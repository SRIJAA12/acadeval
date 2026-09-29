"""
backend/app/services/corpus_index.py

Deterministic, dependency-free (no Neo4j) implementation of the five novelty
signals, built from datasets/AcadEval_Corpus_MASTER.csv. This is the
DEFAULT scoring engine (see settings.NOVELTY_GRAPH_BACKEND) — Neo4j is a
visualization-only layer and does not participate in scoring.

S1-S4 delegate to the exact functions in novelty_math.py that the Neo4j
engine also uses, so the two engines can only ever differ because of DATA
availability, never because of independently-drifted formula code. S5 adds
one deliberate special case on top of novelty_math.new_connection_score
(see signal_5_new_connection_discovery) that the Neo4j path does not have —
see the novelty-engine fix report for why.

Real CSV schema note: datasets/AcadEval_Corpus_MASTER.csv has NO clean
"application area" column. _derive_application() extracts a best-effort
proxy from Expected_Output's templated topic phrase, falling back to the
first Keywords entry. This is a heuristic, not ground truth — it materially
affects S1/S3/S5 combination-novelty quality since "application" is one of
the four entity categories those signals compare against, so it deserves
a second look if novelty scores from the corpus engine seem off for a
particular domain.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import os
import re
import threading
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.services.novelty_math import (
    combine_signals,
    feature_rarity,
    graph_distance,
    neighborhood_sparsity,
    new_connection_score,
    relationship_rarity,
)

CSV_PATH_DEFAULT = os.environ.get(
    "ACADEVAL_CORPUS_CSV",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets", "AcadEval_Corpus_MASTER.csv"),
)

# Real production CSV (datasets/AcadEval_Corpus_MASTER.csv) uses Project_ID.
REAL_SCHEMA_ID_COL = "Project_ID"
# Generic/test schema (backend/tests/test_corpus_index.py's fixture) uses
# lowercase columns including a clean "application" field directly — kept as
# its own branch so the hand-verified fixture numbers stay exact.
GENERIC_SCHEMA_ID_COL = "project_id"

# Expected_Output is templated but not uniformly so ("A working prototype for
# X with...", "A deployable X platform...", "A functional and deployable X
# framework...", or fully freeform for some domains). These patterns cover
# the templated majority; freeform rows fall back to Keywords[0].
EXPECTED_OUTPUT_APPLICATION_PATTERNS = [
    re.compile(r"^A working (?:prototype for )?(.+?) (?:system|platform)\b", re.IGNORECASE),
    re.compile(r"^A deployable (.+?) (?:platform|system)\b", re.IGNORECASE),
    re.compile(r"^A functional and deployable (.+?) (?:framework|system|platform)\b", re.IGNORECASE),
]

SIMILAR_PROJECTS_TOP_K = 5


def _is_nan(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _split_comma_list(value) -> list[str]:
    if value is None or _is_nan(value):
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _derive_application(row) -> str:
    expected_output = str(row.get("Expected_Output", "") or "").strip()
    for pattern in EXPECTED_OUTPUT_APPLICATION_PATTERNS:
        m = pattern.match(expected_output)
        if m:
            return m.group(1).strip().lower()
    keywords = _split_comma_list(row.get("Keywords"))
    return keywords[0].lower() if keywords else ""


def _namespaced(kind: str, name: str) -> str:
    # namespacing prevents e.g. an algorithm and a dataset that happen to
    # share a name from colliding in the entity-count / pair-count dicts
    return f"{kind}:{name.strip().lower()}"


def _build_entities_from_real_row(row) -> frozenset:
    entities = set()
    for name in _split_comma_list(row.get("Algorithms")):
        entities.add(_namespaced("algo", name))
    for name in _split_comma_list(row.get("Technologies")):
        entities.add(_namespaced("tech", name))
    dataset_used = str(row.get("Dataset_Used", "") or "").strip()
    if dataset_used and dataset_used.lower() != "nan":
        # Dataset_Used is free text ("Wikipedia and BookCorpus", "Model
        # parameters, metrics and artifacts") with no consistent delimiter --
        # splitting on "," / "and" would manufacture noisy, non-repeating
        # tokens. Treat the whole normalized phrase as one entity so exact
        # repeats across templated rows still count as real co-occurrence.
        entities.add(_namespaced("data", dataset_used.lower()))
    application = _derive_application(row)
    if application:
        entities.add(_namespaced("app", application))
    return frozenset(entities)


def _build_entities_from_generic_row(row) -> frozenset:
    entities = set()
    for kind, col in (("algo", "algorithms"), ("tech", "technologies"), ("data", "datasets")):
        for name in _split_comma_list(row.get(col)):
            entities.add(_namespaced(kind, name))
    application = str(row.get("application", "") or "").strip()
    if application and application.lower() != "nan":
        entities.add(_namespaced("app", application))
    return frozenset(entities)


@dataclass
class ProjectRecord:
    project_id: str
    title: str
    domain: str
    subdomain: str
    entities: frozenset


class CorpusIndex:
    """Thread-safe singleton. Access via get_corpus_index(), not the constructor."""

    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or CSV_PATH_DEFAULT
        self.projects: dict[str, ProjectRecord] = {}
        self.entity_doc_count: dict[str, int] = {}
        self.pair_doc_count: dict[frozenset, int] = {}
        self.domain_count: dict[str, int] = {}
        self.subdomain_count: dict[str, int] = {}
        self.n_projects: int = 0
        self.csv_snapshot_id: str = "no-csv-loaded"
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if not os.path.exists(self.csv_path):
            self.n_projects = 0  # valid (degraded) state -- compute_signals() handles N=0
            return

        with open(self.csv_path, "rb") as f:
            self.csv_snapshot_id = "corpus-csv:" + hashlib.sha256(f.read()).hexdigest()[:16]

        df = pd.read_csv(self.csv_path)
        is_real_schema = REAL_SCHEMA_ID_COL in df.columns

        for _, row in df.iterrows():
            if is_real_schema:
                pid = str(row[REAL_SCHEMA_ID_COL])
                title = str(row.get("Title", "") or "")
                domain = str(row.get("Domain", "") or "")
                subdomain = str(row.get("Sub_Domain", "") or "")
                entities = _build_entities_from_real_row(row)
            else:
                pid = str(row[GENERIC_SCHEMA_ID_COL])
                title = str(row.get("title", "") or pid)
                domain = str(row.get("domain", "") or "")
                subdomain = str(row.get("sub_domain", "") or "")
                entities = _build_entities_from_generic_row(row)
            self._index_one(pid, title, domain, subdomain, entities)

        self.n_projects = len(self.projects)

    def _index_one(self, pid: str, title: str, domain: str, subdomain: str, entities: frozenset):
        self.projects[pid] = ProjectRecord(pid, title, domain, subdomain, entities)
        for e in entities:
            self.entity_doc_count[e] = self.entity_doc_count.get(e, 0) + 1
        for u, v in itertools.combinations(sorted(entities), 2):
            key = frozenset((u, v))
            self.pair_doc_count[key] = self.pair_doc_count.get(key, 0) + 1
        if domain:
            self.domain_count[domain] = self.domain_count.get(domain, 0) + 1
        if subdomain:
            self.subdomain_count[subdomain] = self.subdomain_count.get(subdomain, 0) + 1

    def reload(self):
        with self._lock:
            self.__init__(self.csv_path)

    def add_project(self, project_id: str, domain: str, subdomain: str, entities, title: str = ""):
        """Call this right after a project is scored & accepted, so the very
        next submission in the same process sees it as historical context
        without waiting for a full CSV reload."""
        with self._lock:
            if project_id in self.projects:
                return
            self._index_one(project_id, title or project_id, domain, subdomain, frozenset(entities))
            self.n_projects += 1

    # -- five signals -------------------------------------------------------

    def signal_1_nearest_distance(self, candidate: frozenset) -> tuple[Optional[float], Optional[str], list[dict]]:
        if self.n_projects == 0 or not candidate:
            return None, None, []
        historical = [
            {"project_id": pid, "title": rec.title, "entity_names": rec.entities}
            for pid, rec in self.projects.items()
        ]
        distance, ranked = graph_distance(candidate, historical, top_k=SIMILAR_PROJECTS_TOP_K)
        nearest_pid = ranked[0]["project_id"] if ranked else None
        return round(distance, 4), nearest_pid, ranked

    def _feature_counts(self, candidate: frozenset) -> dict[str, int]:
        return {f: self.entity_doc_count.get(f, 0) for f in candidate}

    def signal_2_feature_rarity(self, candidate: frozenset) -> Optional[float]:
        if not candidate:
            return None
        counts = self._feature_counts(candidate)
        return round(feature_rarity(counts.values(), self.n_projects), 4)

    def _pair_counts(self, candidate: frozenset) -> dict[tuple, int]:
        return {
            (u, v): self.pair_doc_count.get(frozenset((u, v)), 0)
            for u, v in itertools.combinations(sorted(candidate), 2)
        }

    def signal_3_relationship_rarity(self, candidate: frozenset) -> Optional[float]:
        pairs = self._pair_counts(candidate)
        if not pairs:
            return None
        return round(relationship_rarity(pairs.values()), 4)

    def signal_4_neighborhood_sparsity(self, domain: str, subdomain: str) -> Optional[float]:
        if self.n_projects == 0:
            return None
        sibling_count = self.subdomain_count.get(subdomain, 0) if subdomain else self.domain_count.get(domain, 0)
        return round(neighborhood_sparsity(sibling_count, self.n_projects), 4)

    def signal_5_new_connection_discovery(self, candidate: frozenset) -> tuple[Optional[float], bool]:
        pairs = list(itertools.combinations(sorted(candidate), 2))
        if not pairs:
            return None, False
        feature_counts = self._feature_counts(candidate)
        known_features = {f for f, c in feature_counts.items() if c > 0}
        known_pairs = [(u, v) for u, v in pairs if u in known_features and v in known_features]
        if not known_pairs:
            # Every extracted entity is itself unseen in the corpus -- you
            # can't say a *combination* is "new" when the individual pieces
            # have never been observed at all. Treated as maximal novelty by
            # definition, and flagged so the report can explain why rather
            # than silently returning a number that looks like an ordinary
            # score. (novelty_math.new_connection_score alone would collapse
            # this into the same neutral 0.5 it uses for "no pairs at all",
            # which loses this distinction.)
            return 1.0, True
        pair_counts = self._pair_counts(candidate)
        return round(new_connection_score(pairs, pair_counts, known_features), 4), False

    # -- orchestration --------------------------------------------------------
    def compute_signals(self, domain: str, subdomain: str, algorithms, technologies,
                          datasets, application) -> dict:
        entities = set()
        for kind, names in (("algo", algorithms), ("tech", technologies), ("data", datasets)):
            for name in names or []:
                if str(name).strip():
                    entities.add(_namespaced(kind, name))
        if application and str(application).strip():
            entities.add(_namespaced("app", application))
        entities = frozenset(entities)

        if self.n_projects == 0:
            return {"status": "insufficient_historical_evidence", "composite_score": None,
                    "band": "Not Scored", "signals": {}, "nearest_project_id": None,
                    "similar_projects": [], "graph_backend": "in-memory-corpus",
                    "corpus_size": 0, "csv_snapshot_id": self.csv_snapshot_id}
        if not entities:
            return {"status": "insufficient_extracted_evidence", "composite_score": None,
                    "band": "Not Scored", "signals": {}, "nearest_project_id": None,
                    "similar_projects": [], "graph_backend": "in-memory-corpus",
                    "corpus_size": self.n_projects, "csv_snapshot_id": self.csv_snapshot_id}

        s1, nearest_pid, similar_projects = self.signal_1_nearest_distance(entities)
        s2 = self.signal_2_feature_rarity(entities)
        s3 = self.signal_3_relationship_rarity(entities)
        s4 = self.signal_4_neighborhood_sparsity(domain, subdomain)
        s5, s5_all_novel = self.signal_5_new_connection_discovery(entities)

        values = [v for v in (s1, s2, s3, s4, s5) if v is not None]
        composite = combine_signals(values) if values else None
        band = ("Highly Novel" if composite is not None and composite >= 75.0 else
                 "Moderately Novel" if composite is not None and composite >= 50.0 else
                 "Low Novelty / Incremental" if composite is not None else "Not Scored")

        return {
            "status": "ok", "composite_score": composite, "band": band,
            "signals": {
                "S1_nearest_project_distance": s1, "S2_feature_rarity": s2,
                "S3_relationship_rarity": s3, "S4_neighborhood_sparsity": s4,
                "S5_new_connection_discovery": s5,
            },
            "nearest_project_id": nearest_pid,
            "similar_projects": similar_projects,
            "flags": {"s5_all_entities_novel_to_corpus": s5_all_novel},
            "corpus_size": self.n_projects,
            "graph_backend": "in-memory-corpus",
            "csv_snapshot_id": self.csv_snapshot_id,
        }


_singleton: Optional[CorpusIndex] = None
_singleton_lock = threading.Lock()


def get_corpus_index() -> CorpusIndex:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = CorpusIndex()
    return _singleton
