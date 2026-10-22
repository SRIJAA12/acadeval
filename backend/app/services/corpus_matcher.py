"""Reference-corpus catalog and rarity-weighted project matching.

Replaces the old hand-tuned match heuristic. A candidate's similarity to a
target project is the average of two scores, both weighted by how RARE the
shared terms are across the reference corpus (idf), so that ubiquitous stack
terms (Python, React, Git) contribute almost nothing and shared problem
words / rare techniques dominate:

* entity score: weighted Jaccard over the extracted entity sets
  (sum idf of shared / (sum idf of the union + a smoothing constant)),
  exact matches only.
* text score: idf-weighted cosine over title / abstract / keywords / domain
  tokens, i.e. "are they about the same problem".
"""
from __future__ import annotations

import csv
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.config import settings
from app.services.corpus_quality import boilerplate_cells, is_template_row

log = logging.getLogger(__name__)

STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "of", "for", "to", "with", "and", "or", "is",
    "are", "was", "were", "by", "at", "from", "as", "into", "using", "based",
    "via", "through", "system", "project", "approach", "framework", "model",
    "evaluation", "analysis", "application", "development", "implementation",
}

# Candidates scoring below this are not offered as a "related project"; the
# report then says there is no close prior work instead of showing a weak %.
# Bump whenever the scoring formula below changes (not for data-only changes —
# those are covered by get_corpus_fingerprint()). Read by app/eval/versioning.py
# to decide whether a cached benchmark result is still valid.
SIMILARITY_METHOD_VERSION = "corpus-matcher-v1.0"

MIN_SIMILARITY = 0.15
# An entity found in more than this share of corpus projects is flagged generic.
GENERIC_DOC_FRACTION = 0.05
ENTITY_WEIGHT = 0.5
MIN_IDF = 0.05
# Added to the weighted-Jaccard denominator. Without it, two projects whose
# entire entity sets are generic (all idf ~ 0) would still score 1.0, because
# the weights cancel. This makes the score depend on the absolute amount of
# rare shared evidence, not just the ratio.
ENTITY_SMOOTHING = 2.0

_PREFERRED_CORPUS = "corpus/AcadEval_Corpus_MASTER.csv"
_LEGACY_CORPUS = [
    "AcadEval_Corpus_MASTER.csv",
    "new_dataset/new_AcadEval_Corpus.csv.xls",
    "corpus/new_AcadEval_Corpus.csv",
    "corpus/AcadEval_Corpus.csv",
    "corpus/AcadEval_Corpus_250_Projects.csv",
]
_INTERNAL_ENTITY_KEYS = {"sub_domain", "domain"}

_CATALOG: Optional[List[Dict[str, Any]]] = None
_INDEX: Dict[str, Any] = {}


def reset_corpus_cache() -> None:
    global _CATALOG, _INDEX
    _CATALOG = None
    _INDEX = {}


def get_corpus_vocabulary() -> Set[str]:
    """All canonical entity keys known to the loaded corpus. Loads the catalog
    if it hasn't been loaded yet. Used by app/eval/telemetry.py to measure what
    share of a submission's entities the corpus can actually compare against.
    """
    if not _CATALOG:
        load_corpus_projects_catalog()
    return set(_INDEX.get("entity_idf", {}).keys())


def get_corpus_fingerprint() -> str:
    """Cheap proxy for "has the corpus data changed" (path + size + mtime, not
    file content — the corpus CSV is ~55MB, too large to hash on every check).
    Used by app/eval/versioning.py to decide whether to re-run the benchmark.
    """
    import hashlib

    parts = []
    for p in _resolve_corpus_paths():
        try:
            st = Path(p).stat()
            parts.append(f"{p}:{st.st_size}:{int(st.st_mtime)}")
        except OSError:
            parts.append(f"{p}:missing")
    return hashlib.sha256("|".join(sorted(parts)).encode("utf-8")).hexdigest()[:16]


def _split_clean_field(val: Any) -> list[str]:
    """Splits comma/semicolon/newline separated text into clean, de-duplicated items."""
    if not val:
        return []
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a", "[]", "{}"):
        return []
    res, seen = [], set()
    for item in re.split(r"[,;\n\t|]+", s):
        cleaned = item.strip().strip("\"'`")
        low = cleaned.lower()
        if cleaned and low not in ("none", "nan", "null", "n/a") and low not in seen:
            seen.add(low)
            res.append(cleaned)
    return res


def _tokenise(text: str) -> Set[str]:
    text = re.sub(r"\[[A-Za-z]*\d+\]", " ", text or "")
    return {t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(t) > 2 and not t.isdigit()} - STOPWORDS


def _corpus_dirs() -> List[Path]:
    dirs = [Path("/datasets"), Path("./datasets")]
    for parent in Path(__file__).resolve().parents:
        dirs.append(parent / "datasets")
    return dirs


def _resolve_corpus_paths() -> List[str]:
    explicit = (settings.CORPUS_CSV_PATH or "").strip()
    if explicit and Path(explicit).exists():
        return [str(Path(explicit).resolve())]
    for d in _corpus_dirs():
        try:
            p = d / _PREFERRED_CORPUS
            if p.exists():
                return [str(p.resolve())]
        except OSError:
            continue
    found, seen = [], set()
    for d in _corpus_dirs():
        for rel in _LEGACY_CORPUS:
            try:
                p = d / rel
                if p.exists() and str(p.resolve()) not in seen:
                    seen.add(str(p.resolve()))
                    found.append(str(p.resolve()))
            except OSError:
                continue
    return found


def _project_from_row(row: dict, idx: int, boiler: dict[str, set[str]]) -> Optional[Dict[str, Any]]:
    title = str(row.get("Title") or "").strip()
    if not title:
        return None

    def cells(col: str) -> list[str]:
        cell = str(row.get(col) or "").strip()
        return [] if cell in boiler.get(col, ()) else _split_clean_field(cell)

    algos, techs = cells("Algorithms"), cells("Technologies")
    frameworks, tools = cells("Frameworks"), cells("Tools")
    hardware, datasets = cells("Hardware"), cells("Dataset_Used")
    languages, keywords = cells("Programming_Languages"), cells("Keywords")
    domain = str(row.get("Domain") or "General CSE").strip()
    sub_domain = str(row.get("Sub_Domain") or "Machine Learning").strip()
    abstract = str(row.get("Abstract") or "").strip()

    entity_set = {
        item.strip().lower() for item in algos + techs + frameworks + tools + hardware + datasets + languages
    }
    tokens = _tokenise(f"{title} {domain} {sub_domain} {' '.join(keywords)} {abstract}")
    return {
        "id": str(row.get("Project_ID") or f"CORPUS_{idx + 1}").strip(),
        "title": title,
        "domain": domain,
        "sub_domain": sub_domain,
        "abstract": abstract,
        "algorithms": algos,
        "technologies": techs,
        "frameworks": frameworks,
        "tools": tools,
        "hardware": hardware,
        "datasets": datasets,
        "languages": languages,
        "keywords": keywords,
        "entity_set": entity_set,
        "tokens": tokens,
        "source": "corpus_dataset",
    }


def _build_index(projects: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(projects)
    ent_df: Counter = Counter()
    tok_df: Counter = Counter()
    for p in projects:
        ent_df.update(p["entity_set"])
        tok_df.update(p["tokens"])

    def idf(df: int) -> float:
        return max(math.log((n + 1) / (df + 1)), MIN_IDF)

    entity_idf = {e: idf(c) for e, c in ent_df.items()}
    token_idf = {t: idf(c) for t, c in tok_df.items()}
    return {
        "n": n,
        "entity_idf": entity_idf,
        "token_idf": token_idf,
        "max_entity_idf": idf(0),
        "max_token_idf": idf(0),
        "generic_entities": {e for e, c in ent_df.items() if n and c / n > GENERIC_DOC_FRACTION},
    }


def _with_norm(project: Dict[str, Any], index: Dict[str, Any]) -> Dict[str, Any]:
    t_idf, default = index["token_idf"], index["max_token_idf"]
    project["tok_norm_sq"] = sum(t_idf.get(t, default) ** 2 for t in project["tokens"])
    return project


def load_corpus_projects_catalog(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Reference corpus (filler removed) plus submitted projects, cached in memory."""
    global _CATALOG, _INDEX
    if _CATALOG:
        return _CATALOG

    corpus: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    skipped = 0
    for csv_path in _resolve_corpus_paths():
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                rows = list(csv.DictReader(f))
        except Exception as e:
            log.warning("Could not read corpus file %s: %s", csv_path, e)
            continue
        boiler = boilerplate_cells(rows)
        for idx, row in enumerate(rows):
            if is_template_row(row):
                skipped += 1
                continue
            project = _project_from_row(row, idx, boiler)
            if project and project["id"] not in seen_ids:
                seen_ids.add(project["id"])
                corpus.append(project)
        log.info("Corpus %s: %d rows read", csv_path, len(rows))

    index = _build_index(corpus)
    for project in corpus:
        _with_norm(project, index)

    catalog = list(corpus)
    if db:
        try:
            from app.models.project import Project

            for p in db.query(Project).all():
                pid = str(p.id)
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                extracted = p.extracted_entities or {}
                if isinstance(extracted, str):
                    try:
                        extracted = json.loads(extracted)
                    except Exception:
                        extracted = {}
                if not isinstance(extracted, dict):
                    extracted = {}

                def items(key: str) -> list:
                    v = extracted.get(key, [])
                    return v if isinstance(v, list) else []

                entity_set = {
                    str(i).strip().lower()
                    for key in ("algorithms", "technologies", "frameworks", "libraries", "hardware", "datasets", "applications")
                    for i in items(key)
                    if i
                }
                sub_domain = extracted.get("sub_domain", "") or "Machine Learning"
                catalog.append(_with_norm({
                    "id": pid,
                    "title": p.title or "Submitted Project",
                    "domain": p.domain or "General CSE",
                    "sub_domain": sub_domain,
                    "abstract": p.abstract or "",
                    "algorithms": items("algorithms"),
                    "technologies": items("technologies"),
                    "frameworks": items("frameworks"),
                    "tools": items("libraries"),
                    "hardware": items("hardware"),
                    "datasets": items("datasets"),
                    "languages": [],
                    "keywords": [],
                    "entity_set": entity_set,
                    "tokens": _tokenise(f"{p.title or ''} {p.domain or ''} {sub_domain} {p.abstract or ''} {' '.join(items('applications'))}"),
                    "source": "database",
                }, index))
        except Exception as e:
            log.warning("Could not load database projects into corpus catalog: %s", e)

    _CATALOG, _INDEX = catalog, index
    log.info("Corpus catalog ready: %d reference projects (%d template rows skipped), %d total.", len(corpus), skipped, len(catalog))
    return _CATALOG


def score_candidate(
    target_entities: Set[str],
    target_tokens: Set[str],
    target_tok_norm_sq: float,
    candidate: Dict[str, Any],
    index: Dict[str, Any],
) -> Dict[str, Any]:
    e_idf, e_default = index["entity_idf"], index["max_entity_idf"]
    t_idf, t_default = index["token_idf"], index["max_token_idf"]

    cand_entities = candidate["entity_set"]
    shared_entities = target_entities & cand_entities
    union = target_entities | cand_entities
    union_w = sum(e_idf.get(e, e_default) for e in union)
    entity_score = sum(e_idf.get(e, e_default) for e in shared_entities) / (union_w + ENTITY_SMOOTHING)

    shared_tokens = target_tokens & candidate["tokens"]
    denom = math.sqrt(target_tok_norm_sq * candidate.get("tok_norm_sq", 0.0))
    text_score = (sum(t_idf.get(t, t_default) ** 2 for t in shared_tokens) / denom) if denom else 0.0

    similarity = ENTITY_WEIGHT * entity_score + (1 - ENTITY_WEIGHT) * text_score
    return {
        "similarity": similarity,
        "entity_score": entity_score,
        "text_score": text_score,
        "shared_entities": shared_entities,
        "shared_tokens": shared_tokens,
    }


def _target_entity_set(target_entities: Any) -> Set[str]:
    if isinstance(target_entities, str):
        try:
            target_entities = json.loads(target_entities)
        except Exception:
            target_entities = {}
    if not isinstance(target_entities, dict):
        return set()
    out: Set[str] = set()
    for key, items in target_entities.items():
        if key.startswith("_") or key in _INTERNAL_ENTITY_KEYS:
            continue
        if isinstance(items, list):
            out.update(str(i).strip().lower() for i in items if i)
    return out


def find_similar_corpus_projects(
    target_id: str,
    target_title: str,
    target_domain: str,
    target_sub_domain: str,
    target_entities: Any,
    db: Optional[Session] = None,
    top_k: int = 15,
    target_abstract: str = "",
    min_similarity: float = MIN_SIMILARITY,
) -> List[Dict[str, Any]]:
    """Top reference projects by rarity-weighted similarity (see module docstring)."""
    catalog = load_corpus_projects_catalog(db)
    if not catalog:
        return []

    entity_set = _target_entity_set(target_entities)
    cleaned_title = re.sub(r"\(\d+\)|\.pdf|\.docx|\.pptx|\.txt", "", target_title or "", flags=re.IGNORECASE).strip()
    target_tokens = _tokenise(
        f"{cleaned_title} {target_domain or ''} {target_sub_domain or ''} {target_abstract or ''} {' '.join(entity_set)}"
    )
    t_idf, t_default = _INDEX["token_idf"], _INDEX["max_token_idf"]
    target_norm_sq = sum(t_idf.get(t, t_default) ** 2 for t in target_tokens)

    scored = []
    for cand in catalog:
        if cand["id"] == target_id:
            continue
        result = score_candidate(entity_set, target_tokens, target_norm_sq, cand, _INDEX)
        if result["similarity"] >= min_similarity:
            scored.append((result["similarity"], cand, result))
    scored.sort(key=lambda x: x[0], reverse=True)

    e_idf, e_default = _INDEX["entity_idf"], _INDEX["max_entity_idf"]
    generic = _INDEX["generic_entities"]
    out = []
    for similarity, cand, result in scored[:top_k]:
        detail = sorted(
            ({"name": e, "idf": round(e_idf.get(e, e_default), 2), "generic": e in generic} for e in result["shared_entities"]),
            key=lambda d: (d["generic"], -d["idf"], d["name"]),
        )
        top_tokens = sorted(result["shared_tokens"], key=lambda t: -_INDEX["token_idf"].get(t, t_default))[:8]
        public = {k: v for k, v in cand.items() if k not in ("entity_set", "tokens", "tok_norm_sq")}
        out.append({
            **public,
            "similarity": round(similarity, 4),
            "distance": round(max(0.04, 1.0 - similarity), 4),
            "entity_score": round(result["entity_score"], 4),
            "text_score": round(result["text_score"], 4),
            "shared_entities": [d["name"] for d in detail],
            "shared_entities_detail": detail,
            "shared_tokens": top_tokens,
            "shared_anchors": [],
        })
    return out
