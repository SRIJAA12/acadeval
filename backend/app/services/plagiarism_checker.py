"""Real plagiarism evidence, per the AcadEval+ methodology document:

* Text channel — TF-IDF + cosine passage matching against the full text of
  every OTHER submitted project (Project.parsed_text). Uses sklearn's
  TfidfVectorizer, whose default smooth-idf formula —
  IDF(w) = ln((N+1)/(DF(w)+1)) + 1 — is the exact formula the document
  specifies. NOT run against the reference corpus CSV: its Abstract column is
  auto-generated from a handful of sentence templates (confirmed by sampling),
  so passage-level matching against it would produce systematic false
  positives (unrelated projects "matching" only because they share a template
  sentence). That CSV continues to be used only for the existing entity/topic
  novelty matching (app/services/corpus_matcher.py), unchanged.

* Code channel — k-gram + winnowing fingerprinting (Schleimer, Wilkerson &
  Aiken, 2003) of a project's own linked GitHub repo (see
  app/services/github_code_fetcher.py), compared via Jaccard similarity
  against every other project's cached fingerprint set. Fingerprints are
  plain hashlib.md5-hashed k-grams — deliberately NOT called "Rabin
  fingerprinting"; the document explicitly flags that exact mislabeling.
  Comparison is repo-level (union of all of a repo's file fingerprints), not
  per-file/per-line — an honest scope limit for this first pass, documented
  in the match's source/candidate labels rather than overclaiming precision.

Similarity is not the same as plagiarism: this module reports "potential
overlap found" with source evidence; a human reviewer sets review_status.
Deliberately independent of the novelty engine's topic-similarity corpus
matching — the two must never be conflated (see assessment_engine.py).
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

MIN_TEXT_SCORE = 0.5
MIN_TEXT_PASSAGE_WORDS = 40

MIN_CODE_SCORE = 0.3
MIN_SHARED_FINGERPRINTS = 10
KGRAM_SIZE = 25     # tokens per k-gram
WINNOW_WINDOW = 4   # hashes per winnowing window

PLAGIARISM_METHOD_VERSION = "plagiarism-checker-v1.0"


# ── Text channel ──────────────────────────────────────────────────────────────

def split_passages(text: str, min_words: int = MIN_TEXT_PASSAGE_WORDS) -> list[tuple[str, str]]:
    """Splits text into (passage, location_label) pairs — paragraphs where
    the document has them, a sliding-word-window fallback otherwise."""
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        # Only treat this as "real paragraphs" when there's more than one —
        # a single no-break blob falls through to the sliding window below
        # instead of being kept as one giant, imprecise passage.
        passages = [
            (p, f"paragraph {i + 1}")
            for i, p in enumerate(paragraphs)
            if len(p.split()) >= min_words
        ]
        if passages:
            return passages

    words = text.split()
    if len(words) < min_words:
        return [(text.strip(), "full text")] if words else []

    window, step = 60, 50
    passages = []
    for i in range(0, max(1, len(words) - window + 1), step):
        chunk = " ".join(words[i:i + window])
        if len(chunk.split()) >= min_words:
            passages.append((chunk, f"words {i}-{i + window}"))
    return passages


def _check_text_similarity(project, db) -> list[dict[str, Any]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    from app.models.project import Project

    candidate_passages = split_passages(project.parsed_text or "")
    if not candidate_passages:
        return []

    other_projects = (
        db.query(Project)
        .filter(Project.id != project.id, Project.parsed_text.isnot(None))
        .all()
    )
    corpus_passages: list[tuple[str, str, Any, str]] = []
    for p in other_projects:
        for passage_text, loc in split_passages(p.parsed_text or ""):
            corpus_passages.append((passage_text, loc, p.id, p.title))

    if not corpus_passages:
        return []

    all_texts = [p[0] for p in candidate_passages] + [c[0] for c in corpus_passages]
    try:
        tfidf = TfidfVectorizer(smooth_idf=True).fit_transform(all_texts)
    except ValueError:
        return []  # e.g. empty vocabulary (all-stopword/non-alphanumeric text)

    n_candidate = len(candidate_passages)
    sims = cosine_similarity(tfidf[:n_candidate], tfidf[n_candidate:])

    best_per_source: dict[str, dict[str, Any]] = {}
    for ci, (cand_text, cand_loc) in enumerate(candidate_passages):
        row = sims[ci]
        best_idx = int(np.argmax(row))
        score = float(row[best_idx])
        if score < MIN_TEXT_SCORE:
            continue
        src_text, src_loc, src_pid, src_title = corpus_passages[best_idx]
        existing = best_per_source.get(src_pid)
        if existing is None or score > existing["score"]:
            best_per_source[src_pid] = {
                "match_type": "text",
                "source_project_id": src_pid,
                "source_label": src_title,
                "candidate_passage": cand_text,
                "candidate_location": cand_loc,
                "source_passage": src_text,
                "source_location": src_loc,
                "score": score,
            }
    return list(best_per_source.values())


# ── Code channel ──────────────────────────────────────────────────────────────

_COMMENT_PATTERNS = [
    re.compile(r"#.*"),
    re.compile(r"//.*"),
    re.compile(r"/\*.*?\*/", re.DOTALL),
    re.compile(r'"""(?:.*?)"""', re.DOTALL),
    re.compile(r"'''(?:.*?)'''", re.DOTALL),
]


def _strip_comments(code: str) -> str:
    for pattern in _COMMENT_PATTERNS:
        code = pattern.sub(" ", code)
    return code


def _tokenize_code(code: str) -> list[str]:
    """Best-effort: strips common comment styles, then tokenizes identifiers
    and punctuation. Does not normalize renamed identifiers — a documented v1
    limitation, consistent with the methodology document's own caution that
    tokenization/normalization choices are implementation-specific."""
    code = _strip_comments(code)
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[{}()\[\];,.:=+\-*/]", code)


def _winnow(tokens: list[str]) -> set[int]:
    """Winnowing (Schleimer, Wilkerson & Aiken, 2003): hash every k-gram with
    plain MD5 (not Rabin fingerprinting), then keep only the minimum hash in
    each sliding window of hashes, deduped by position."""
    if not tokens:
        return set()
    if len(tokens) < KGRAM_SIZE:
        kgrams = [" ".join(tokens)]
    else:
        kgrams = [" ".join(tokens[i:i + KGRAM_SIZE]) for i in range(len(tokens) - KGRAM_SIZE + 1)]

    hashes = [int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF for g in kgrams]
    if len(hashes) <= WINNOW_WINDOW:
        return set(hashes)

    fingerprints: set[int] = set()
    prev_min_pos = -1
    for i in range(len(hashes) - WINNOW_WINDOW + 1):
        window = hashes[i:i + WINNOW_WINDOW]
        min_val = min(window)
        min_pos = i + window.index(min_val)
        if min_pos != prev_min_pos:
            fingerprints.add(min_val)
            prev_min_pos = min_pos
    return fingerprints


def _fingerprint_files(files: list[dict]) -> set[int]:
    fingerprints: set[int] = set()
    for f in files:
        fingerprints |= _winnow(_tokenize_code(f.get("content", "")))
    return fingerprints


def _check_code_similarity(project, db) -> tuple[list[dict[str, Any]], dict | None]:
    from app.models.plagiarism import CodeFingerprint
    from app.models.project import Project
    from app.services.github_code_fetcher import fetch_repo_source_files

    if not project.github_url:
        return [], None

    fetched = fetch_repo_source_files(project.github_url)
    cache_row = {
        "repo_owner": fetched["repo_owner"], "repo_name": fetched["repo_name"],
        "branch": fetched["branch"], "file_count": len(fetched["files"]),
        "fingerprints": [], "fetch_error": fetched["fetch_error"],
    }
    if not fetched["files"]:
        return [], cache_row

    candidate_fp = _fingerprint_files(fetched["files"])
    cache_row["fingerprints"] = list(candidate_fp)
    if not candidate_fp:
        return [], cache_row

    other_fps = (
        db.query(CodeFingerprint)
        .filter(CodeFingerprint.project_id != project.id)
        .all()
    )
    matches: list[dict[str, Any]] = []
    for other in other_fps:
        other_set = set(other.fingerprints or [])
        if not other_set:
            continue
        shared = candidate_fp & other_set
        if len(shared) < MIN_SHARED_FINGERPRINTS:
            continue
        union = candidate_fp | other_set
        jaccard = (len(shared) / len(union)) if union else 0.0
        if jaccard < MIN_CODE_SCORE:
            continue
        source_project = db.query(Project).filter(Project.id == other.project_id).first()
        if not source_project:
            continue
        matches.append({
            "match_type": "code",
            "source_project_id": other.project_id,
            "source_label": f"{source_project.title} ({other.repo_owner}/{other.repo_name})",
            "candidate_passage": f"{cache_row['file_count']} source files fingerprinted from {fetched['repo_owner']}/{fetched['repo_name']}",
            "candidate_location": project.github_url,
            "source_passage": f"{other.file_count} source files fingerprinted from {other.repo_owner}/{other.repo_name}",
            "source_location": f"https://github.com/{other.repo_owner}/{other.repo_name}",
            "score": jaccard,
        })
    matches.sort(key=lambda m: -m["score"])
    return matches, cache_row


# ── Orchestration ─────────────────────────────────────────────────────────────

def run_plagiarism_check(project, db) -> dict[str, Any]:
    """Runs both channels, persists evidence, returns a summary for
    assessment_engine.evaluate(). Preserves any PlagiarismMatch a human has
    already reviewed — only `unreviewed` rows for this project are replaced."""
    from app.models.plagiarism import PlagiarismMatch, CodeFingerprint, MatchType, ReviewStatus

    text_matches = _check_text_similarity(project, db)
    code_matches, code_cache = _check_code_similarity(project, db)

    if code_cache is not None:
        existing_fp = db.query(CodeFingerprint).filter(CodeFingerprint.project_id == project.id).first()
        if existing_fp:
            existing_fp.repo_owner = code_cache["repo_owner"]
            existing_fp.repo_name = code_cache["repo_name"]
            existing_fp.branch = code_cache["branch"]
            existing_fp.file_count = code_cache["file_count"]
            existing_fp.fingerprints = code_cache["fingerprints"]
            existing_fp.fetch_error = code_cache["fetch_error"]
            existing_fp.fetched_at = datetime.now(timezone.utc)
        else:
            db.add(CodeFingerprint(
                project_id=project.id,
                repo_owner=code_cache["repo_owner"], repo_name=code_cache["repo_name"],
                branch=code_cache["branch"], file_count=code_cache["file_count"],
                fingerprints=code_cache["fingerprints"], fetch_error=code_cache["fetch_error"],
            ))

    db.query(PlagiarismMatch).filter(
        PlagiarismMatch.project_id == project.id,
        PlagiarismMatch.review_status == ReviewStatus.unreviewed,
    ).delete(synchronize_session=False)

    for m in text_matches + code_matches:
        db.add(PlagiarismMatch(
            project_id=project.id,
            match_type=MatchType(m["match_type"]),
            source_project_id=m["source_project_id"],
            source_label=m["source_label"],
            candidate_passage=m["candidate_passage"][:8000],
            candidate_location=m.get("candidate_location"),
            source_passage=m["source_passage"][:8000],
            source_location=m.get("source_location"),
            score=m["score"],
        ))
    db.commit()

    return {
        "method_version": PLAGIARISM_METHOD_VERSION,
        "text_max": max((m["score"] for m in text_matches), default=0.0),
        "code_max": max((m["score"] for m in code_matches), default=0.0),
        "text_match_count": len(text_matches),
        "code_match_count": len(code_matches),
    }
