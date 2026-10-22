"""In-memory reproduction of NoveltyEngineService's current scoring logic
(graph-novelty-v2.0), built from ONE full Neo4j export instead of the 4+
Cypher queries per candidate that the live engine runs. This is what makes
scoring a few hundred benchmark cases take seconds instead of minutes —
it is NEVER used for real submissions; those always go through the live
`novelty_engine_service` so production behaviour is unchanged.

Reuses the exact pure functions from novelty_math.py and the exact
entity-key/band logic from novelty_engine.py. Parity with the live engine is
checked by tests/test_legacy_scorer_parity.py (requires Neo4j, skipped
otherwise) and by app/eval/benchmark_runner.py's own parity check on a
handful of real projects before trusting a benchmark run.
"""
from __future__ import annotations

import logging
from collections import Counter
from itertools import combinations

from app.services.novelty_engine import NoveltyEngineService, SCORING_METHOD_VERSION, _entity_key
from app.services.novelty_math import (
    clamp, combine_signals, feature_rarity, graph_distance, neighborhood_sparsity,
    new_connection_score, relationship_rarity,
)

log = logging.getLogger(__name__)


class LegacySnapshot:
    """A frozen, in-memory copy of every Project's entity set + domain, plus
    an inverted entity index so feature/pair rarity don't need an O(corpus)
    scan per candidate entity."""

    def __init__(self, projects: list[dict]):
        self.projects = projects  # [{"project_id","title","domain","sub_domain","entity_names": set[str]}]
        self.corpus_size = len(projects)
        self.entity_index: dict[str, set[int]] = {}
        self.domain_counts: Counter = Counter()
        self.sub_domain_counts: Counter = Counter()
        self._project_sizes: list[int] = [len(p["entity_names"]) for p in projects]
        for idx, p in enumerate(projects):
            for key in p["entity_names"]:
                self.entity_index.setdefault(key, set()).add(idx)
            if p["domain"]:
                self.domain_counts[p["domain"].strip().lower()] += 1
            if p["sub_domain"]:
                self.sub_domain_counts[p["sub_domain"].strip().lower()] += 1

    @classmethod
    def export(cls) -> "LegacySnapshot":
        from app.services.graph_db import graph_service, ENTITY_LABELS
        from app.services.novelty_engine import ENTITY_RELATIONSHIPS

        valid_labels = set(ENTITY_LABELS)
        with graph_service.session() as session:
            rows = session.run(
                """
                MATCH (p:Project)
                OPTIONAL MATCH (p)-[r]->(e)
                WHERE type(r) IN $entity_relationships
                RETURN p.id AS project_id, coalesce(p.title, p.id) AS title,
                       coalesce(p.domain, '') AS domain, coalesce(p.sub_domain, '') AS sub_domain,
                       collect(DISTINCT CASE WHEN e IS NULL THEN null ELSE {labels: labels(e), name: toLower(e.name)} END) AS raw_entities
                """,
                entity_relationships=ENTITY_RELATIONSHIPS,
            ).data()

        projects = []
        for row in rows:
            names = set()
            for item in row.get("raw_entities", []):
                if not item:
                    continue
                label = next((lbl for lbl in item.get("labels", []) if lbl in valid_labels), None)
                name = item.get("name")
                if label and name:
                    names.add(_entity_key(label, name))
            if not names:
                continue  # mirrors the live query's EXISTS {...} filter: only projects with entities count
            projects.append({
                "project_id": row["project_id"], "title": row["title"],
                "domain": row["domain"], "sub_domain": row["sub_domain"], "entity_names": names,
            })
        log.info("LegacySnapshot exported %d projects with entities (of %d total)", len(projects), len(rows))
        return cls(projects)

    def _graph_distance_fast(self, candidate_keys: set[str], historical,
                              exclude_idx: int | None, top_k: int) -> tuple[float, list[dict]]:
        """Same contract as novelty_math.graph_distance (nearest-neighbour Jaccard,
        top_k nearest), but uses entity_index to only visit projects that share at
        least one entity with the candidate instead of scanning the whole corpus.
        Falls back to the exact brute-force function on true zero-overlap (rare),
        so results are always identical to the live engine's, just usually much
        faster — this is what makes scoring ~1700 benchmark cases take seconds
        instead of over an hour."""
        if not candidate_keys:
            return 0.5, []

        intersection_counts: Counter = Counter()
        for key in candidate_keys:
            for idx in self.entity_index.get(key, ()):
                if idx != exclude_idx:
                    intersection_counts[idx] += 1

        if not intersection_counts:
            return graph_distance(candidate_keys, historical, top_k=top_k)

        n_candidate = len(candidate_keys)
        scored = []
        for idx, inter in intersection_counts.items():
            union = n_candidate + self._project_sizes[idx] - inter
            sim = round(inter / union, 4) if union > 0 else 0.0
            scored.append((idx, sim))
        scored.sort(key=lambda t: (-t[1], t[0]))

        top = scored[:top_k]
        nearest_similarity = top[0][1] if top else 0.0
        ranked = [
            {
                "project_id": str(self.projects[idx]["project_id"]),
                "title": str(self.projects[idx]["title"] or self.projects[idx]["project_id"] or "Untitled project"),
                "similarity_score": sim,
            }
            for idx, sim in top
        ]
        return clamp(1.0 - nearest_similarity), ranked

    def score(self, extracted_entities: dict, domain: str, sub_domain: str,
              exclude_project_id: str | None = None, top_k: int = 5) -> dict:
        """Reproduces NoveltyEngineService.compute_novelty_signals's composite
        and signals from this in-memory snapshot."""
        entities = NoveltyEngineService._candidate_entities(extracted_entities)
        exclude_idx = None
        if exclude_project_id:
            exclude_idx = next((i for i, p in enumerate(self.projects) if p["project_id"] == exclude_project_id), None)
        corpus_size = self.corpus_size - (1 if exclude_idx is not None else 0)

        similar_projects: list[dict] = []
        if corpus_size <= 0 or not entities:
            signals = [0.5] * 5
        else:
            candidate_keys = {e["key"] for e in entities}
            historical = (p for i, p in enumerate(self.projects) if i != exclude_idx)
            signal_1, similar_projects = self._graph_distance_fast(candidate_keys, historical, exclude_idx, top_k)

            def _count(key: str) -> int:
                idxs = self.entity_index.get(key, set())
                return len(idxs - {exclude_idx}) if exclude_idx is not None else len(idxs)

            feature_counts = {e["key"]: _count(e["key"]) for e in entities}
            signal_2 = feature_rarity(feature_counts.values(), corpus_size)

            pair_keys = [tuple(sorted((a["key"], b["key"]))) for a, b in combinations(entities, 2)]

            def _pair_count(pair: tuple[str, str]) -> int:
                idxs = self.entity_index.get(pair[0], set()) & self.entity_index.get(pair[1], set())
                return len(idxs - {exclude_idx}) if exclude_idx is not None else len(idxs)

            pair_counts = {pair: _pair_count(pair) for pair in pair_keys}
            signal_3 = relationship_rarity(pair_counts.values())

            dom_l, sub_l = (domain or "").strip().lower(), (sub_domain or "").strip().lower()
            if sub_l:
                sibling_count = self.sub_domain_counts.get(sub_l, 0)
            else:
                sibling_count = self.domain_counts.get(dom_l, 0)
            if exclude_idx is not None:
                excl = self.projects[exclude_idx]
                matches_sibling = (sub_l and excl["sub_domain"].strip().lower() == sub_l) or \
                                   (not sub_l and excl["domain"].strip().lower() == dom_l)
                if matches_sibling:
                    sibling_count = max(0, sibling_count - 1)
            signal_4 = neighborhood_sparsity(sibling_count, corpus_size)

            known_features = {k for k, c in feature_counts.items() if c > 0}
            signal_5 = new_connection_score(pair_keys, pair_counts, known_features)

            signals = [signal_1, signal_2, signal_3, signal_4, signal_5]

        composite = combine_signals(signals)
        if not entities:
            band = "Insufficient Extracted Evidence"
        elif corpus_size <= 0:
            band = "Insufficient Historical Evidence"
        else:
            band = NoveltyEngineService._band(composite)

        s1, s2, s3, s4, s5 = signals
        return {
            "signal_1_graph_distance": round(s1, 4), "signal_2_feature_rarity": round(s2, 4),
            "signal_3_relationship_rarity": round(s3, 4), "signal_4_graph_density": round(s4, 4),
            "signal_5_new_connection_discovery": round(s5, 4),
            "composite_novelty_score": composite, "novelty_band": band,
            "method_version": SCORING_METHOD_VERSION, "corpus_size": corpus_size,
            "similar_projects": similar_projects,
        }
