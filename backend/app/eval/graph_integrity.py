"""Neo4j structural checks: orphan entities, relationship validity, the same
entity name appearing under more than one label (e.g. "pytorch" as both
Technology and Framework — found during investigation, not yet fixed; this
metric exists to measure it, and should trend to 0 once Phase 1's
canonicalizer is wired into the backfill), and corpus-vs-index drift (the
Neo4j graph and the in-memory corpus catalog, see corpus_matcher.py, must
agree on how many reference projects exist).

Each check is independent and returned separately — see the project's
quality-architecture plan for why these are never combined into one score.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def run_graph_integrity_checks() -> dict:
    """Returns {metric_name: {"value": float|None, "n": int, "details": dict}}.
    Raises GraphUnavailableError if Neo4j can't be reached — callers (the eval
    task) should let that fail the EvalRun rather than silently skip it, since
    "Neo4j unreachable" is itself the finding.
    """
    from app.services.graph_db import graph_service, ENTITY_LABELS, CATEGORY_EDGE_MAP

    known_rel_types = {rel for _label, rel in CATEGORY_EDGE_MAP.values()} | {
        "HAS_DOMAIN", "HAS_SUBDOMAIN", "SUBDOMAIN_OF", "CO_OCCURS",
    }

    with graph_service.session() as session:
        orphan_row = session.run(
            """
            MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels)
            OPTIONAL MATCH (p:Project)-[r]->(n)
            WITH n, count(r) AS incoming
            RETURN count(n) AS total, sum(CASE WHEN incoming = 0 THEN 1 ELSE 0 END) AS orphans
            """,
            labels=ENTITY_LABELS,
        ).single()
        total_entities = orphan_row["total"] or 0
        orphan_entities = orphan_row["orphans"] or 0

        rel_row = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(r) AS c
            """
        ).data()
        total_rels = sum(r["c"] for r in rel_row)
        invalid_rels = sum(r["c"] for r in rel_row if r["rel_type"] not in known_rel_types)

        multi_label_row = session.run(
            """
            MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels)
            WITH toLower(n.name) AS key, collect(DISTINCT [l IN labels(n) WHERE l IN $labels][0]) AS lbls
            RETURN count(key) AS total_keys, sum(CASE WHEN size(lbls) > 1 THEN 1 ELSE 0 END) AS multi_label_keys
            """,
            labels=ENTITY_LABELS,
        ).single()
        total_keys = multi_label_row["total_keys"] or 0
        multi_label_keys = multi_label_row["multi_label_keys"] or 0

        corpus_project_count = session.run(
            "MATCH (p:Project {source_type: 'corpus'}) RETURN count(p) AS c"
        ).single()["c"]

    try:
        from app.services.corpus_matcher import load_corpus_projects_catalog
        index_size = sum(1 for p in load_corpus_projects_catalog() if p.get("source") == "corpus_dataset")
    except Exception:
        log.exception("graph_integrity: could not load corpus catalog for drift check")
        index_size = None

    drift = abs(corpus_project_count - index_size) if index_size is not None else None

    return {
        "graph_orphan_entity_rate": {
            "value": round(orphan_entities / total_entities, 4) if total_entities else None,
            "n": total_entities,
            "details": {"orphan_count": orphan_entities},
        },
        "graph_relationship_validity": {
            "value": round(1 - invalid_rels / total_rels, 4) if total_rels else None,
            "n": total_rels,
            "details": {"invalid_count": invalid_rels, "by_type": {r["rel_type"]: r["c"] for r in rel_row}},
        },
        "graph_multi_label_entity_rate": {
            "value": round(multi_label_keys / total_keys, 4) if total_keys else None,
            "n": total_keys,
            "details": {"multi_label_count": multi_label_keys},
        },
        "graph_corpus_index_drift": {
            "value": float(drift) if drift is not None else None,
            "n": 1,
            "details": {"neo4j_corpus_projects": corpus_project_count, "index_corpus_projects": index_size},
        },
    }
