"""
Module 4 — Relational Graph Builder & Ingestion Service
=========================================================
Handles upserting nodes and edges into PostgreSQL `graph_nodes` and `graph_edges`
in a single DB transaction. Also synchronizes Neo4j Aura in parallel.
"""

import json
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.project import Project
from app.services.graph_db import GRAPH_INGESTION_VERSION, graph_service

log = logging.getLogger(__name__)

# Category to relationship mapping
CATEGORY_RELATION_MAP = {
    "algorithms": ("Algorithm", "USES_ALGORITHM"),
    "technologies": ("Technology", "USES_TECHNOLOGY"),
    "frameworks": ("Framework", "USES_FRAMEWORK"),
    "libraries": ("Library", "USES_LIBRARY"),
    "datasets": ("Dataset", "USES_DATASET"),
    "applications": ("Application", "TARGETS_APPLICATION"),
    "hardware": ("Hardware", "RUNS_ON"),
    "metrics": ("Metric", "EVALUATED_BY"),
}


def upsert_node(db: Session, node_type: str, name: str, source_key: str | None = None) -> int:
    """
    Atomic node upsert using PostgreSQL ON CONFLICT (node_type, source_key).
    Returns the node's integer ID.
    """
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Node name cannot be empty")

    normalized_key = (source_key or clean_name).strip().casefold()
    stmt = text("""
        INSERT INTO graph_nodes (node_type, name, source_key)
        VALUES (:node_type, :name, :source_key)
        ON CONFLICT (node_type, source_key)
        DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """)
    result = db.execute(stmt, {
        "node_type": node_type,
        "name": clean_name,
        "source_key": normalized_key,
    })
    node_id = result.scalar()
    return node_id


def insert_edge(
    db: Session,
    from_node: int,
    to_node: int,
    relationship: str,
    confidence: float = 1.0,
    project_id: str | None = None,
) -> None:
    """
    Idempotently inserts a directed edge between from_node and to_node.
    """
    stmt = text("""
        INSERT INTO graph_edges (from_node, to_node, relationship, confidence, project_ids)
        VALUES (:from_node, :to_node, :relationship, :confidence, CAST(:project_ids AS jsonb))
        ON CONFLICT (from_node, to_node, relationship)
        DO UPDATE SET
            confidence = EXCLUDED.confidence,
            project_ids = CASE
                WHEN graph_edges.project_ids @> EXCLUDED.project_ids THEN graph_edges.project_ids
                ELSE graph_edges.project_ids || EXCLUDED.project_ids
            END
    """)
    db.execute(stmt, {
        "from_node": from_node,
        "to_node": to_node,
        "relationship": relationship,
        "confidence": confidence,
        "project_ids": json.dumps([project_id] if project_id else []),
    })


def ingest_project_to_relational_graph(
    db: Session,
    project_id: str,
    title: str,
    domain: str,
    sub_domain: str,
    extracted_entities: dict
) -> dict:
    """
    Ingests a project and all its extracted entities into `graph_nodes` & `graph_edges`.
    Executed inside a single DB transaction.
    """
    nodes_created = 0
    edges_created = 0

    # 1. Project node uses the immutable project UUID as its storage key while
    # keeping the editable title purely as display text.
    proj_name = title or str(project_id)
    proj_node_id = upsert_node(db, "Project", proj_name, source_key=str(project_id))
    nodes_created += 1

    # Remove stale project-to-entity edges before an idempotent re-ingestion.
    db.execute(text("DELETE FROM graph_edges WHERE from_node = :project_node"), {
        "project_node": proj_node_id,
    })
    db.execute(text("""
        UPDATE graph_edges
        SET project_ids = project_ids - :project_id
        WHERE relationship = 'CO_OCCURS' AND project_ids ? :project_id
    """), {"project_id": str(project_id)})
    db.execute(text("""
        DELETE FROM graph_edges
        WHERE relationship = 'CO_OCCURS' AND jsonb_array_length(project_ids) = 0
    """))

    # 2. Domain & Subdomain nodes
    if domain:
        dom_id = upsert_node(db, "Domain", domain)
        insert_edge(db, proj_node_id, dom_id, "HAS_DOMAIN")
        nodes_created += 1
        edges_created += 1

        if sub_domain:
            subdom_id = upsert_node(db, "Subdomain", sub_domain)
            insert_edge(db, proj_node_id, subdom_id, "HAS_SUBDOMAIN")
            insert_edge(db, subdom_id, dom_id, "SUBDOMAIN_OF")
            nodes_created += 1
            edges_created += 2

    # 3. Entity nodes & project-to-entity edges
    entity_nodes: list[tuple[str, int]] = []  # (category_label, node_id)

    for cat_key, (node_label, rel_type) in CATEGORY_RELATION_MAP.items():
        entity_list = extracted_entities.get(cat_key, [])
        for ent_name in entity_list:
            if not ent_name or not str(ent_name).strip():
                continue
            ent_id = upsert_node(db, node_label, str(ent_name).strip())
            insert_edge(db, proj_node_id, ent_id, rel_type)
            entity_nodes.append((node_label, ent_id))
            nodes_created += 1
            edges_created += 1

    # 4. CO_OCCURS edges between entity pairs on the same project
    n_entities = len(entity_nodes)
    for i in range(n_entities):
        for j in range(i + 1, n_entities):
            node1_id = entity_nodes[i][1]
            node2_id = entity_nodes[j][1]
            if node1_id != node2_id:
                insert_edge(
                    db,
                    node1_id,
                    node2_id,
                    "CO_OCCURS",
                    confidence=1.0,
                    project_id=str(project_id),
                )
                edges_created += 1

    # 5. Neo4j sync must succeed before the relational transaction commits.
    neo4j_status = "synced"
    try:
        neo4j_result = graph_service.build_project_graph(
            project_id=str(project_id),
            title=title,
            domain=domain or "Unknown",
            sub_domain=sub_domain or "Unknown",
            extracted_entities=extracted_entities,
            source_type="submission",
            source_version=GRAPH_INGESTION_VERSION,
        )
    except Exception as e:
        log.error("Neo4j sync failed for project %s: %s", project_id, e)
        raise

    db.commit()

    # Invalidate NetworkX cache only after both graph stores are ready.
    try:
        from app.services.graph_networkx import invalidate_graph_cache
        invalidate_graph_cache()
    except Exception as e:
        log.warning("Could not invalidate NetworkX cache: %s", e)

    log.info("Relational Graph Ingestion complete for project %s: %d nodes, %d edges.", project_id, nodes_created, edges_created)

    return {
        "project_id": project_id,
        "relational_nodes_ingested": nodes_created,
        "relational_edges_ingested": edges_created,
        "neo4j_sync": neo4j_status,
        "neo4j_content_hash": neo4j_result["content_hash"],
    }


def bulk_rebuild_graph(db: Session) -> dict:
    """
    Clears existing `graph_edges` and `graph_nodes` tables and re-ingests all
    projects in PostgreSQL that have non-null `extracted_entities`.
    """
    # Truncate graph tables
    db.execute(text("TRUNCATE TABLE graph_edges, graph_nodes RESTART IDENTITY CASCADE;"))
    db.commit()

    from app.models.evaluation import EvaluationReport

    projects = (
        db.query(Project)
        .join(EvaluationReport, EvaluationReport.project_id == Project.id)
        .filter(
            Project.extracted_entities.isnot(None),
            EvaluationReport.novelty_report.isnot(None),
        )
        .all()
    )

    total_projects = 0
    total_nodes = 0
    total_edges = 0

    for proj in projects:
        title = proj.title or ""
        entities = proj.extracted_entities or {}
        domain = entities.get("domain", proj.domain or "General CSE")
        sub_domain = entities.get("sub_domain", "Machine Learning")

        res = ingest_project_to_relational_graph(
            db=db,
            project_id=str(proj.id),
            title=title,
            domain=domain,
            sub_domain=sub_domain,
            extracted_entities=entities,
        )
        total_projects += 1
        total_nodes += res["relational_nodes_ingested"]
        total_edges += res["relational_edges_ingested"]

    # Re-build NetworkX in-memory cache
    try:
        from app.services.graph_networkx import load_graph
        G = load_graph(db)
        nx_nodes = G.number_of_nodes()
        nx_edges = G.number_of_edges()
    except Exception as e:
        nx_nodes, nx_edges = 0, 0
        log.warning("Failed to populate NetworkX graph after bulk rebuild: %s", e)

    return {
        "projects_processed": total_projects,
        "relational_nodes": total_nodes,
        "relational_edges": total_edges,
        "networkx_nodes": nx_nodes,
        "networkx_edges": nx_edges,
    }
