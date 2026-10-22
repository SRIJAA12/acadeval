"""Builds the continuous-evaluation benchmark: synthetic retrieval/duplicate
cases generated from the reference corpus (fixed seed, no LLM), plus the ~237
real hand-labelled pairs salvaged from datasets/AcadEval_SimBench.csv rows
SB00001-SB00987 (the other ~28k SimBench rows are template-generated and
their labels are thresholds of their own stored score columns — see the
corpus-quality investigation — so they are never used).

Synthetic cases are the only thing weights/thresholds are ever tuned on
(dev split); the holdout split and the real pairs are for reporting only.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

BENCHMARK_BUILDER_VERSION = "benchmark-v1.0"
SEED = 42
N_SEED_PROJECTS = 300
HOLDOUT_FRACTION = 0.3

_TITLE_SUFFIX_RE = re.compile(r"\s*\((?:Variant\s*\d+|Ref:?[^)]*)\)\s*", re.IGNORECASE)


def _project_hash_split(project_id: str) -> str:
    """Deterministic dev/holdout assignment — stable across rebuilds as long
    as the project id doesn't change, independent of row order."""
    h = int(hashlib.sha256(project_id.encode("utf-8")).hexdigest(), 16)
    return "holdout" if (h % 1000) / 1000.0 < HOLDOUT_FRACTION else "dev"


def _entities_payload(algorithms, technologies, frameworks, tools, datasets) -> dict:
    return {
        "algorithms": list(algorithms or []),
        "technologies": list(technologies or []),
        "frameworks": list(frameworks or []),
        "libraries": list(tools or []),
        "datasets": list(datasets or []),
    }


def _drop_fraction(items: list[str], fraction: float, rng: random.Random) -> list[str]:
    if not items or fraction <= 0:
        return list(items)
    keep_n = max(0, round(len(items) * (1 - fraction)))
    return rng.sample(items, keep_n) if keep_n < len(items) else list(items)


def _shuffle_words(text: str, rng: random.Random) -> str:
    words = text.split()
    rng.shuffle(words)
    return " ".join(words)


def _make_near_duplicate(seed: dict, case_id: str, rng: random.Random) -> dict:
    """Same project, reworded title, up to 20% of entities dropped."""
    algos = _drop_fraction(seed["algorithms"], 0.2, rng)
    techs = _drop_fraction(seed["technologies"], 0.2, rng)
    return {
        "case_id": case_id, "kind": "near_duplicate", "seed_id": seed["id"],
        "query": {
            "title": _shuffle_words(seed["title"], rng),
            "domain": seed["domain"], "sub_domain": seed["sub_domain"],
            "entities": _entities_payload(algos, techs, seed["frameworks"], seed["tools"], seed["datasets"]),
            "abstract": seed.get("abstract", ""),
        },
        "relevant_ids": [seed["id"]], "is_duplicate": True,
    }


def _make_alias_variant(seed: dict, case_id: str, rng: random.Random) -> dict:
    """Same entities, case/spacing changed — an approximation of a real alias
    table until Phase 1's entity_aliases.csv exists; MR2 (metamorphic: alias
    swap) should ideally use real synonyms once that file lands."""
    def mutate(name: str) -> str:
        choice = rng.random()
        if choice < 0.33:
            return name.upper()
        if choice < 0.66:
            return name.replace(" ", "")
        return f" {name} "

    return {
        "case_id": case_id, "kind": "alias_variant", "seed_id": seed["id"],
        "query": {
            "title": seed["title"],
            "domain": seed["domain"], "sub_domain": seed["sub_domain"],
            "entities": _entities_payload(
                [mutate(a) for a in seed["algorithms"]], [mutate(t) for t in seed["technologies"]],
                seed["frameworks"], seed["tools"], seed["datasets"],
            ),
            "abstract": seed.get("abstract", ""),
        },
        "relevant_ids": [seed["id"]], "is_duplicate": True,
    }


def _make_hard_negative(seed: dict, other: dict, case_id: str) -> dict:
    """Same sub-domain as the seed, but a different project's entities —
    tests that the matcher doesn't treat "same topic area" as "duplicate"."""
    return {
        "case_id": case_id, "kind": "hard_negative", "seed_id": seed["id"], "foil_id": other["id"],
        "query": {
            "title": other["title"], "domain": other["domain"], "sub_domain": seed["sub_domain"],
            "entities": _entities_payload(other["algorithms"], other["technologies"], other["frameworks"], other["tools"], other["datasets"]),
            "abstract": other.get("abstract", ""),
        },
        "relevant_ids": [other["id"]], "is_duplicate": False,
    }


def _make_random_negative(seed: dict, other: dict, case_id: str) -> dict:
    return {
        "case_id": case_id, "kind": "random_negative", "seed_id": seed["id"], "foil_id": other["id"],
        "query": {
            "title": other["title"], "domain": other["domain"], "sub_domain": other["sub_domain"],
            "entities": _entities_payload(other["algorithms"], other["technologies"], other["frameworks"], other["tools"], other["datasets"]),
            "abstract": other.get("abstract", ""),
        },
        "relevant_ids": [other["id"]], "is_duplicate": False,
    }


def _make_partial_splice(seed: dict, other: dict, case_id: str, rng: random.Random) -> dict:
    """Half of seed's entities + half of other's — should score as related to
    both but a duplicate of neither."""
    a_algos = _drop_fraction(seed["algorithms"], 0.5, rng)
    a_techs = _drop_fraction(seed["technologies"], 0.5, rng)
    b_algos = _drop_fraction(other["algorithms"], 0.5, rng)
    b_techs = _drop_fraction(other["technologies"], 0.5, rng)
    return {
        "case_id": case_id, "kind": "partial_splice", "seed_id": seed["id"], "foil_id": other["id"],
        "query": {
            "title": f"{seed['title']} / {other['title']}", "domain": seed["domain"], "sub_domain": seed["sub_domain"],
            "entities": _entities_payload(a_algos + b_algos, a_techs + b_techs, seed["frameworks"], seed["tools"], seed["datasets"]),
            "abstract": f"{seed.get('abstract','')} {other.get('abstract','')}".strip(),
        },
        "relevant_ids": [seed["id"], other["id"]], "is_duplicate": False,
    }


def build_synthetic_cases(n_seeds: int = N_SEED_PROJECTS, seed: int = SEED) -> list[dict]:
    from app.services.corpus_matcher import load_corpus_projects_catalog

    catalog = [p for p in load_corpus_projects_catalog() if p.get("source") == "corpus_dataset"]
    if not catalog:
        log.warning("benchmark_builder: corpus catalog is empty — no synthetic cases built")
        return []

    rng = random.Random(seed)
    by_subdomain: dict[str, list[dict]] = {}
    for p in catalog:
        by_subdomain.setdefault(p["sub_domain"], []).append(p)

    # Stratified-by-domain sample: round-robin over sub-domains so no single
    # large sub-domain dominates the seed set.
    pools = list(by_subdomain.values())
    rng.shuffle(pools)
    seeds: list[dict] = []
    i = 0
    while len(seeds) < min(n_seeds, len(catalog)) and pools:
        pool = pools[i % len(pools)]
        if pool:
            seeds.append(pool.pop(rng.randrange(len(pool))))
        pools = [p for p in pools if p]
        i += 1

    cases: list[dict] = []
    for seed_project in seeds:
        split = _project_hash_split(seed_project["id"])
        others_same_subdomain = [p for p in catalog if p["sub_domain"] == seed_project["sub_domain"] and p["id"] != seed_project["id"]]
        others_any = [p for p in catalog if p["id"] != seed_project["id"]]
        if not others_any:
            continue

        base = f"{seed_project['id']}"
        c1 = _make_near_duplicate(seed_project, f"{base}-dup", rng)
        c2 = _make_alias_variant(seed_project, f"{base}-alias", rng)
        hard_foil = rng.choice(others_same_subdomain) if others_same_subdomain else rng.choice(others_any)
        c3 = _make_hard_negative(seed_project, hard_foil, f"{base}-hardneg")
        c4 = _make_random_negative(seed_project, rng.choice(others_any), f"{base}-randneg")
        splice_foil = rng.choice(others_any)
        c5 = _make_partial_splice(seed_project, splice_foil, f"{base}-splice", rng)

        for case in (c1, c2, c3, c4, c5):
            case["split"] = split
            cases.append(case)

    log.info("benchmark_builder: built %d synthetic cases from %d seeds", len(cases), len(seeds))
    return cases


LABEL_TO_ORDINAL = {"Different": 0.0, "Partially Similar": 1 / 3, "Partial Match": 2 / 3, "Similar": 1.0}
LABEL_TO_BINARY_STRICT = {"Different": 0, "Similar": 1}  # Partial* excluded from the strict binary subset


def load_real_pairs(simbench_path: str | None = None) -> dict[str, list[dict]]:
    """Returns {"pairs": [...], "conflicting_excluded": [...]} from the
    salvaged SB00001-SB00987 range. See module docstring for why only this
    subset of SimBench is usable."""
    import csv

    path = simbench_path or _default_simbench_path()
    if not path or not Path(path).exists():
        log.warning("benchmark_builder: SimBench file not found at %s — no real pairs loaded", path)
        return {"pairs": [], "conflicting_excluded": []}

    def strip_title(t: str) -> str:
        return _TITLE_SUFFIX_RE.sub(" ", str(t or "")).strip()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= 1000:
                break
            pair_id = str(row.get("Pair_ID", "")).strip()
            if not ("SB00001" <= pair_id <= "SB00987"):
                continue
            row["A_clean"] = strip_title(row.get("Project_A_Title"))
            row["B_clean"] = strip_title(row.get("Project_B_Title"))
            row["pair_key"] = tuple(sorted([row["A_clean"], row["B_clean"]]))
            rows.append(row)

    labels_per_key: dict[tuple, set] = {}
    for row in rows:
        labels_per_key.setdefault(row["pair_key"], set()).add(str(row.get("Faculty_Label", "")).strip())
    conflicting_keys = {key for key, labels in labels_per_key.items() if len(labels) > 1}

    seen_keys: set = set()
    pairs, conflicting = [], []
    for row in rows:
        key = row["pair_key"]
        if key in seen_keys:
            continue
        seen_keys.add(key)

        label = str(row.get("Faculty_Label", "")).strip()
        entry = {
            "pair_id": row.get("Pair_ID"),
            "title_a": row["A_clean"], "title_b": row["B_clean"],
            "abstract_a": str(row.get("Project_A_Abstract", "") or ""),
            "abstract_b": str(row.get("Project_B_Abstract", "") or ""),
            "entities_a": {"technologies": [s.strip() for s in str(row.get("Project_A_Features", "") or "").split(";") if s.strip()]},
            "entities_b": {"technologies": [s.strip() for s in str(row.get("Project_B_Features", "") or "").split(";") if s.strip()]},
            "label": label,
            "ordinal": LABEL_TO_ORDINAL.get(label),
            "binary_strict": LABEL_TO_BINARY_STRICT.get(label),  # None for Partial* — excluded from the strict AUC
        }
        if key in conflicting_keys:
            conflicting.append(entry)
        else:
            pairs.append(entry)

    log.info("benchmark_builder: loaded %d real pairs (%d excluded for conflicting labels)", len(pairs), len(conflicting))
    return {"pairs": pairs, "conflicting_excluded": conflicting}


def _default_simbench_path() -> str | None:
    from app.services.dataset_paths import resolve_dataset_file

    found = resolve_dataset_file("AcadEval_SimBench.csv")
    return str(found) if found else None


def benchmark_fingerprint(synthetic_cases: list[dict], real_pairs: list[dict]) -> str:
    blob = json.dumps(
        {"n_synthetic": len(synthetic_cases), "n_real": len(real_pairs), "builder": BENCHMARK_BUILDER_VERSION, "seed": SEED},
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def build_benchmark() -> dict:
    synthetic = build_synthetic_cases()
    real = load_real_pairs()
    return {
        "version": benchmark_fingerprint(synthetic, real["pairs"]),
        "builder_version": BENCHMARK_BUILDER_VERSION,
        "synthetic_cases": synthetic,
        "real_pairs": real["pairs"],
        "real_pairs_excluded_conflicting": real["conflicting_excluded"],
    }
