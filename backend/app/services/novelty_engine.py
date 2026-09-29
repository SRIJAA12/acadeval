"""Versioned novelty scoring against a frozen historical snapshot.

The candidate project is deliberately not inserted before this service runs.

Two scoring engines share the same five formulas (novelty_math.py) and the
same output contract (see compute_novelty_signals):
  - corpus (default, settings.NOVELTY_GRAPH_BACKEND): the in-memory index
    over datasets/AcadEval_Corpus_MASTER.csv (corpus_index.py). Always
    available, no external service required.
  - neo4j: the graph in Neo4j Aura, read inside one transaction so the five
    signals see the same historical graph even while other workers ingest
    completed projects. Optional -- used for "auto" fallback or "neo4j"
    strict mode; Neo4j itself remains the source of truth for the graph
    *visualization* UI regardless of which engine scores a given submission.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from itertools import combinations

from app.config import settings
from app.services.corpus_index import get_corpus_index
from app.services.graph_db import CATEGORY_EDGE_MAP, ENTITY_LABELS, GraphUnavailableError, graph_service
from app.services.novelty_math import (
    combine_signals,
    feature_rarity,
    graph_distance,
    neighborhood_sparsity,
    new_connection_score,
    relationship_rarity,
)

log = logging.getLogger(__name__)

# Bumped from v2.0 -> v2.1: the corpus-index fallback (Task: "make novelty
# scoring always succeed") means a project scored before this change and one
# scored after may have taken different code paths even under identical
# settings, so cached evidence from before this version is invalidated and
# recomputed once. Both engines share one version string on purpose --
# graph_backend (in scoring_metadata) records which engine actually ran,
# rather than forking the version per engine.
SCORING_METHOD_VERSION = "graph-novelty-v2.1"
COMBINER_METHOD = "unweighted-mean-v2"
SIMILAR_PROJECTS_TOP_K = 5
ADEQUATE_CORPUS_SIZE = 30

ENTITY_RELATIONSHIPS = [relationship for _label, relationship in CATEGORY_EDGE_MAP.values()]


def _entity_key(label: str, name: str) -> str:
    return f"{label.strip().casefold()}:{name.strip().casefold()}"


class NoveltyEngineService:
    @staticmethod
    def input_hash(title: str, domain: str, sub_domain: str, extracted_entities: dict) -> str:
        public_entities = {
            key: sorted({str(value).strip().casefold() for value in extracted_entities.get(key, []) if str(value).strip()})
            for key in CATEGORY_EDGE_MAP
        }
        payload = {
            "title": title.strip(),
            "domain": domain.strip(),
            "sub_domain": sub_domain.strip(),
            "entities": public_entities,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def compute_novelty_signals(
        self,
        project_id: str,
        extracted_entities: dict,
        domain: str,
        sub_domain: str = "",
    ) -> dict:
        """Score a candidate against historical evidence. Dispatches to the
        engine selected by settings.NOVELTY_GRAPH_BACKEND (default "corpus"
        -- see app/config.py). Neo4j, when used, is wrapped so its outage
        falls back to the corpus index instead of aborting the caller
        (pipeline.task_score_and_report / report_generator) with an
        unhandled GraphUnavailableError.
        """
        backend = settings.NOVELTY_GRAPH_BACKEND

        if backend in ("auto", "neo4j"):
            try:
                result = self._compute_via_neo4j(project_id, extracted_entities, domain, sub_domain)
                result["scoring_metadata"]["graph_backend"] = "neo4j"
                log.info("novelty_engine: scored %s via neo4j", project_id)
                return result
            except GraphUnavailableError as exc:
                if backend == "neo4j":
                    raise  # strict mode: caller explicitly wants crash-on-failure
                log.warning(
                    "novelty_engine: Neo4j unavailable for %s (%s) -- falling back to in-memory corpus index",
                    project_id, exc,
                )
            except Exception:
                if backend == "neo4j":
                    raise
                log.exception("novelty_engine: unexpected Neo4j error for %s -- falling back", project_id)

        return self._compute_via_corpus(project_id, extracted_entities, domain, sub_domain)

    def _compute_via_neo4j(
        self,
        project_id: str,
        extracted_entities: dict,
        domain: str,
        sub_domain: str = "",
    ) -> dict:
        entities = self._candidate_entities(extracted_entities)
        with graph_service.session() as session:
            evidence = session.execute_read(
                self._score_snapshot_tx,
                project_id,
                entities,
                domain,
                sub_domain,
            )

        signals = evidence["signals"]
        composite_score = combine_signals(signals)
        corpus_size = evidence["corpus_size"]

        if not entities:
            novelty_band = "Insufficient Extracted Evidence"
            evidence_quality = "empty"
        elif corpus_size == 0:
            novelty_band = "Insufficient Historical Evidence"
            evidence_quality = "empty"
        elif corpus_size < ADEQUATE_CORPUS_SIZE:
            novelty_band = self._band(composite_score)
            evidence_quality = "limited"
        else:
            novelty_band = self._band(composite_score)
            evidence_quality = "adequate"

        captured_at = datetime.now(timezone.utc).isoformat()
        metadata = {
            "method_version": SCORING_METHOD_VERSION,
            "combiner": COMBINER_METHOD,
            "corpus_snapshot_id": evidence["snapshot_id"],
            "corpus_project_count": corpus_size,
            "snapshot_captured_at": captured_at,
            "top_k": SIMILAR_PROJECTS_TOP_K,
            "evidence_quality": evidence_quality,
            "candidate_preexisting_in_graph": evidence["candidate_preexisting"],
            "candidate_excluded_from_snapshot": True,
        }

        signal_1, signal_2, signal_3, signal_4, signal_5 = signals
        explanation_bullets = [
            f"Nearest-project graph distance ({signal_1 * 100:.1f}%): based on the closest entity-set match, so a near duplicate cannot be hidden by unrelated projects.",
            f"Feature rarity ({signal_2 * 100:.1f}%): frequency of the extracted features across {corpus_size} frozen historical projects.",
            f"Relationship rarity ({signal_3 * 100:.1f}%): historical co-occurrence frequency for the candidate's feature pairs.",
            f"Graph neighborhood sparsity ({signal_4 * 100:.1f}%): inverse saturation of the candidate's domain/sub-domain neighborhood.",
            f"New-connection discovery ({signal_5 * 100:.1f}%): unseen pairings among features that are individually established in the corpus.",
            f"Evidence snapshot {evidence['snapshot_id'][:12]} used {corpus_size} projects; the candidate was excluded from every query.",
        ]

        return {
            "signal_1_graph_distance": round(signal_1, 4),
            "signal_2_feature_rarity": round(signal_2, 4),
            "signal_3_relationship_rarity": round(signal_3, 4),
            "signal_4_graph_density": round(signal_4, 4),
            "signal_5_new_connection_discovery": round(signal_5, 4),
            "composite_novelty_score": composite_score,
            "novelty_band": novelty_band,
            "explanation_bullets": explanation_bullets,
            "similar_projects": evidence["similar_projects"],
            "distance_method": "nearest-neighbour-jaccard-v2",
            "density_method": "historical-neighborhood-saturation-v2",
            "scoring_metadata": metadata,
        }

    def _compute_via_corpus(
        self,
        project_id: str,
        extracted_entities: dict,
        domain: str,
        sub_domain: str = "",
    ) -> dict:
        """Score against datasets/AcadEval_Corpus_MASTER.csv via CorpusIndex.
        Adapts CorpusIndex.compute_signals()'s own return contract (status /
        composite_score / band / signals dict -- see corpus_index.py, kept
        exactly as its own tests expect) into the shape pipeline.py and
        report_generator.py already rely on from this method, so neither
        needed to change.
        """
        index = get_corpus_index()

        algorithms = list(extracted_entities.get("algorithms", []))
        # The corpus CSV models one "tech stack" bucket; frameworks/libraries
        # fold into it. Hardware/metrics have no analog in the corpus data
        # and are intentionally left out of the comparison rather than
        # counted as guaranteed-zero-overlap noise against every project.
        technologies = (
            list(extracted_entities.get("technologies", []))
            + list(extracted_entities.get("frameworks", []))
            + list(extracted_entities.get("libraries", []))
        )
        datasets = list(extracted_entities.get("datasets", []))
        applications = list(extracted_entities.get("applications", []))
        application = applications[0] if applications else ""

        result = index.compute_signals(
            domain=domain, subdomain=sub_domain,
            algorithms=algorithms, technologies=technologies,
            datasets=datasets, application=application,
        )

        corpus_size = result["corpus_size"]
        signals = result.get("signals", {})

        if result["status"] == "insufficient_extracted_evidence":
            novelty_band = "Insufficient Extracted Evidence"
            evidence_quality = "empty"
        elif result["status"] == "insufficient_historical_evidence":
            novelty_band = "Insufficient Historical Evidence"
            evidence_quality = "empty"
        elif corpus_size < ADEQUATE_CORPUS_SIZE:
            novelty_band = result["band"]
            evidence_quality = "limited"
        else:
            novelty_band = result["band"]
            evidence_quality = "adequate"

        # A candidate with fewer than 2 total entities can leave S3/S5
        # individually undefined (no pair exists to rate) even though the
        # overall status is "ok". Substitute the same neutral 0.5 the Neo4j
        # path already uses for its insufficient-evidence case, and
        # recompute the composite from these exact 5 values so the displayed
        # signals and the displayed composite always agree (CorpusIndex's
        # own composite silently drops None signals from the average instead
        # of neutralizing them -- fine for its own contract, not for this
        # one, which always shows all five).
        raw = [
            signals.get("S1_nearest_project_distance"),
            signals.get("S2_feature_rarity"),
            signals.get("S3_relationship_rarity"),
            signals.get("S4_neighborhood_sparsity"),
            signals.get("S5_new_connection_discovery"),
        ]
        signal_1, signal_2, signal_3, signal_4, signal_5 = [v if v is not None else 0.5 for v in raw]
        composite_score = combine_signals([signal_1, signal_2, signal_3, signal_4, signal_5])

        similar_projects = [
            {"project_id": m["project_id"], "title": m["title"], "similarity_score": m["similarity_score"]}
            for m in result.get("similar_projects", [])
        ]

        captured_at = datetime.now(timezone.utc).isoformat()
        metadata = {
            "method_version": SCORING_METHOD_VERSION,
            "combiner": COMBINER_METHOD,
            "corpus_snapshot_id": result.get("csv_snapshot_id", "unknown"),
            "corpus_project_count": corpus_size,
            "snapshot_captured_at": captured_at,
            "top_k": SIMILAR_PROJECTS_TOP_K,
            "evidence_quality": evidence_quality,
            "candidate_preexisting_in_graph": project_id in index.projects,
            "candidate_excluded_from_snapshot": True,
            "graph_backend": "in-memory-corpus",
        }

        explanation_bullets = [
            f"Nearest-project distance ({signal_1 * 100:.1f}%): closest entity-set match in the historical CSV corpus, so a near duplicate cannot be hidden by unrelated projects.",
            f"Feature rarity ({signal_2 * 100:.1f}%): frequency of the extracted features across {corpus_size} historical corpus projects.",
            f"Relationship rarity ({signal_3 * 100:.1f}%): historical co-occurrence frequency for the candidate's feature pairs.",
            f"Neighborhood sparsity ({signal_4 * 100:.1f}%): inverse saturation of the candidate's domain/sub-domain neighborhood.",
            f"New-connection discovery ({signal_5 * 100:.1f}%): unseen pairings among features that are individually established in the corpus.",
            f"Scored via the in-memory corpus index (Neo4j unavailable or not selected) against {corpus_size} historical projects.",
        ]
        if result.get("flags", {}).get("s5_all_entities_novel_to_corpus"):
            explanation_bullets.append(
                "Every extracted feature is itself unprecedented in the corpus, so the combination is treated as maximally novel by definition."
            )

        # Grow the in-memory index immediately so the next submission scored
        # in this same process sees this one as historical context, without
        # waiting for a CSV reload.
        if result["status"] == "ok":
            try:
                candidate_entity_keys = set()
                for kind, names in (("algo", algorithms), ("tech", technologies), ("data", datasets)):
                    for name in names:
                        if str(name).strip():
                            candidate_entity_keys.add(f"{kind}:{name.strip().lower()}")
                if application:
                    candidate_entity_keys.add(f"app:{application.strip().lower()}")
                index.add_project(project_id, domain, sub_domain, candidate_entity_keys)
            except Exception:
                log.exception("novelty_engine: failed to grow corpus index with %s (non-fatal)", project_id)

        return {
            "signal_1_graph_distance": signal_1,
            "signal_2_feature_rarity": signal_2,
            "signal_3_relationship_rarity": signal_3,
            "signal_4_graph_density": signal_4,
            "signal_5_new_connection_discovery": signal_5,
            "composite_novelty_score": composite_score,
            "novelty_band": novelty_band,
            "explanation_bullets": explanation_bullets,
            "similar_projects": similar_projects,
            "distance_method": "nearest-neighbour-jaccard-v2",
            "density_method": "historical-neighborhood-saturation-v2",
            "scoring_metadata": metadata,
        }

    @staticmethod
    def _band(score: float) -> str:
        if score >= 75.0:
            return "Highly Novel"
        if score >= 50.0:
            return "Moderately Novel"
        return "Low Novelty / Incremental"

    @staticmethod
    def _candidate_entities(extracted_entities: dict) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for category, (label, _relationship) in CATEGORY_EDGE_MAP.items():
            for raw_name in extracted_entities.get(category, []):
                name = str(raw_name).strip().casefold()
                if not name:
                    continue
                key = _entity_key(label, name)
                if key in seen:
                    continue
                seen.add(key)
                result.append({"key": key, "label": label, "name": name})
        return result

    @classmethod
    def _score_snapshot_tx(cls, tx, project_id: str, entities: list[dict], domain: str, sub_domain: str) -> dict:
        snapshot_rows = tx.run(
            """
            MATCH (p:Project)
            WITH p, p.id = $project_id AS is_candidate
            WHERE NOT is_candidate
              AND EXISTS {
                  MATCH (p)-[r]->()
                  WHERE type(r) IN $entity_relationships
              }
            RETURN p.id AS project_id,
                   coalesce(p.content_hash, '') AS content_hash,
                   coalesce(p.source_version, '') AS source_version,
                   coalesce(p.title, '') AS title
            ORDER BY project_id
            """,
            project_id=project_id,
            entity_relationships=ENTITY_RELATIONSHIPS,
        ).data()
        candidate_preexisting = bool(tx.run(
            "MATCH (p:Project {id: $project_id}) RETURN count(p) > 0 AS present",
            project_id=project_id,
        ).single()["present"])

        corpus_ids = [row["project_id"] for row in snapshot_rows]
        snapshot_material = "\n".join(
            f"{row['project_id']}:{row['content_hash']}:{row['source_version']}"
            for row in snapshot_rows
        )
        snapshot_id = hashlib.sha256(snapshot_material.encode("utf-8")).hexdigest()
        corpus_size = len(corpus_ids)

        if not corpus_ids:
            return {
                "snapshot_id": snapshot_id,
                "corpus_size": 0,
                "candidate_preexisting": candidate_preexisting,
                "signals": [0.5] * 5,
                "similar_projects": [],
            }

        if not entities:
            return {
                "snapshot_id": snapshot_id,
                "corpus_size": corpus_size,
                "candidate_preexisting": candidate_preexisting,
                "signals": [0.5] * 5,
                "similar_projects": [],
            }

        historical_rows = tx.run(
            """
            MATCH (p:Project)
            WHERE p.id IN $corpus_ids
            OPTIONAL MATCH (p)-[r]->(e)
            WHERE type(r) IN $entity_relationships
            RETURN p.id AS project_id,
                   coalesce(p.title, p.id) AS title,
                   collect(DISTINCT CASE
                       WHEN e IS NULL THEN null
                       ELSE {labels: labels(e), name: toLower(e.name)}
                   END) AS raw_entities
            """,
            corpus_ids=corpus_ids,
            entity_relationships=ENTITY_RELATIONSHIPS,
        ).data()
        historical_projects = []
        valid_labels = set(ENTITY_LABELS)
        for row in historical_rows:
            names = set()
            for item in row.get("raw_entities", []):
                name = item.get("name") if item else None
                labels = item.get("labels", []) if item else []
                label = next((value for value in labels if value in valid_labels), None)
                if label and name:
                    names.add(_entity_key(label, name))
            historical_projects.append({
                "project_id": row["project_id"],
                "title": row["title"],
                "entity_names": names,
            })

        candidate_keys = {entity["key"] for entity in entities}
        signal_1, similar_projects = graph_distance(
            candidate_keys,
            historical_projects,
            top_k=SIMILAR_PROJECTS_TOP_K,
        )

        feature_rows = tx.run(
            """
            UNWIND $entities AS ent
            OPTIONAL MATCH (p:Project)-[r]->(e)
            WHERE p.id IN $corpus_ids
              AND type(r) IN $entity_relationships
              AND ent.label IN labels(e)
              AND toLower(e.name) = ent.name
            RETURN ent.key AS key, count(DISTINCT p) AS project_count
            """,
            entities=entities,
            corpus_ids=corpus_ids,
            entity_relationships=ENTITY_RELATIONSHIPS,
        ).data() if entities else []
        feature_counts = {row["key"]: int(row["project_count"]) for row in feature_rows}
        signal_2 = feature_rarity(feature_counts.values(), corpus_size)

        pair_payload = []
        pair_key_lookup: dict[str, tuple[str, str]] = {}
        for index, (left, right) in enumerate(combinations(entities, 2)):
            canonical = tuple(sorted((left["key"], right["key"])))
            pair_id = str(index)
            pair_key_lookup[pair_id] = canonical
            pair_payload.append({
                "id": pair_id,
                "a_label": left["label"],
                "a_name": left["name"],
                "b_label": right["label"],
                "b_name": right["name"],
            })

        pair_rows = tx.run(
            """
            UNWIND $pairs AS pair
            CALL {
                WITH pair
                OPTIONAL MATCH (p:Project)-[ra]->(a), (p)-[rb]->(b)
                WHERE p.id IN $corpus_ids
                  AND type(ra) IN $entity_relationships
                  AND type(rb) IN $entity_relationships
                  AND pair.a_label IN labels(a)
                  AND pair.b_label IN labels(b)
                  AND toLower(a.name) = pair.a_name
                  AND toLower(b.name) = pair.b_name
                RETURN count(DISTINCT p) AS project_count
            }
            RETURN pair.id AS id, project_count
            """,
            pairs=pair_payload,
            corpus_ids=corpus_ids,
            entity_relationships=ENTITY_RELATIONSHIPS,
        ).data() if pair_payload else []
        pair_counts = {
            pair_key_lookup[row["id"]]: int(row["project_count"])
            for row in pair_rows
        }
        signal_3 = relationship_rarity(pair_counts.values())

        neighborhood = tx.run(
            """
            MATCH (p:Project)
            WHERE p.id IN $corpus_ids
              AND (
                ($sub_domain <> '' AND toLower(coalesce(p.sub_domain, '')) = toLower($sub_domain))
                OR ($sub_domain = '' AND toLower(coalesce(p.domain, '')) = toLower($domain))
              )
            RETURN count(DISTINCT p) AS sibling_count
            """,
            corpus_ids=corpus_ids,
            domain=domain,
            sub_domain=sub_domain,
        ).single()
        sibling_count = int(neighborhood["sibling_count"]) if neighborhood else 0
        signal_4 = neighborhood_sparsity(sibling_count, corpus_size)

        known_features = {key for key, count in feature_counts.items() if count > 0}
        signal_5 = new_connection_score(
            pair_key_lookup.values(),
            pair_counts,
            known_features,
        )

        return {
            "snapshot_id": snapshot_id,
            "corpus_size": corpus_size,
            "candidate_preexisting": candidate_preexisting,
            "signals": [signal_1, signal_2, signal_3, signal_4, signal_5],
            "similar_projects": similar_projects,
        }


novelty_engine_service = NoveltyEngineService()
