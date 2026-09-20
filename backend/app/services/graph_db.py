"""
Module 3 — Project Knowledge Graph Service (AcadEval_ProjectGraphBank)
========================================================================
Ingests a project's classification + extracted entities into Neo4j as the
Project Knowledge Graph, following the node/edge schema from Section 5.4 of
the AcadEval+ specification: Project/Domain/Subdomain/Algorithm/Technology/
Dataset/Application/Metric nodes (plus Framework/Library/Hardware, an
extension of the doc's first-draft ontology to match what Module 2 actually
extracts), connected via HAS_DOMAIN/HAS_SUBDOMAIN/SUBDOMAIN_OF/USES_*/
TARGETS_APPLICATION/EVALUATED_BY edges, with a derived CO_OCCURS edge between
every pair of entities used together on the same project.

There is deliberately no in-memory/NetworkX fallback here: the novelty engine
(Module 4) reads directly from Neo4j, so a project that can't be written to
Neo4j must fail loudly (GraphUnavailableError) rather than silently drifting
onto a second, ephemeral source of truth.
"""

import logging
from contextlib import contextmanager

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import settings

log = logging.getLogger(__name__)

# category key (as produced by extractor_service.extract_entities) -> (Node label, relationship type)
CATEGORY_EDGE_MAP = {
    "algorithms":    ("Algorithm",   "USES_ALGORITHM"),
    "technologies":  ("Technology",  "USES_TECHNOLOGY"),
    "frameworks":    ("Framework",   "USES_FRAMEWORK"),
    "libraries":     ("Library",     "USES_LIBRARY"),
    "datasets":      ("Dataset",     "USES_DATASET"),
    "applications":  ("Application", "TARGETS_APPLICATION"),
    "hardware":      ("Hardware",    "RUNS_ON"),
    "metrics":       ("Metric",      "EVALUATED_BY"),   # Module 3 step 7 \u2014 was missing
}

ENTITY_LABELS = [label for label, _ in CATEGORY_EDGE_MAP.values()]

CONSTRAINED_LABELS = ["Domain", "Subdomain"] + ENTITY_LABELS


class GraphUnavailableError(RuntimeError):
    """Raised when Neo4j cannot be reached. The novelty pipeline has no other
    source of truth, so callers should surface this as a clear 503, not a
    fabricated score."""


class ProjectGraphService:
    def __init__(self):
        self.driver = None
        self._connect_attempted = False

    def connect(self):
        if self._connect_attempted:
            return
        self._connect_attempted = True
        try:
            user = settings.effective_neo4j_user
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(user, settings.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            db_label = settings.NEO4J_DATABASE or "default"
            log.info(
                "Connected to Neo4j Aura at %s  (database=%s)",
                settings.NEO4J_URI, db_label,
            )
        except Exception as e:
            log.warning("Neo4j unavailable at %s (%s).", settings.NEO4J_URI, e)
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
        self.driver = None
        self._connect_attempted = False

    @contextmanager
    def session(self):
        """Context manager yielding a live Neo4j session. Raises GraphUnavailableError
        if Neo4j can't be reached (never falls back to in-memory data)."""
        self.connect()
        if not self.driver:
            raise GraphUnavailableError(
                "Neo4j is not reachable. Start it with `docker compose up -d neo4j` "
                "and confirm NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD in .env."
            )
        # Use NEO4J_DATABASE if provided (required for Neo4j Aura)
        db_name = settings.NEO4J_DATABASE or None
        session = self.driver.session(database=db_name) if db_name else self.driver.session()
        try:
            yield session
        except (ServiceUnavailable, Neo4jError) as e:
            raise GraphUnavailableError(f"Neo4j query failed: {e}") from e
        finally:
            session.close()

    def ensure_constraints(self):
        """Idempotent uniqueness constraints, run once at app startup so MERGE
        calls stay fast/dedupe-safe as the graph grows (Section 7.3, step 1)."""
        try:
            with self.session() as session:
                session.run(
                    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS "
                    "FOR (p:Project) REQUIRE p.id IS UNIQUE"
                )
                for label in CONSTRAINED_LABELS:
                    session.run(
                        f"CREATE CONSTRAINT {label.lower()}_name_unique IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.name IS UNIQUE"
                    )
            log.info("Neo4j schema constraints ensured.")
        except GraphUnavailableError as e:
            log.warning("Skipping constraint setup — %s", e)

    @staticmethod
    def entity_label_name_pairs(extracted_entities: dict) -> list[tuple[str, str]]:
        """Flattens Module 2's categorized entity dict into (label, name) tuples."""
        pairs = []
        for cat_key, (label, _rel) in CATEGORY_EDGE_MAP.items():
            for name in extracted_entities.get(cat_key, []):
                pairs.append((label, name))
        return pairs

    def build_project_graph(self, project_id: str, title: str, domain: str, sub_domain: str,
                             extracted_entities: dict) -> dict:
        """
        Ingests a project's metadata and extracted entities into Neo4j inside a
        single write transaction, so a partially-extracted project never leaves
        a half-written graph (Section 7.3, step 2).
        """
        entity_pairs = self.entity_label_name_pairs(extracted_entities)

        with self.session() as session:
            session.execute_write(self._ingest_tx, project_id, title, domain, sub_domain, extracted_entities)
            if len(entity_pairs) > 1:
                session.execute_write(self._co_occurrence_tx, project_id, entity_pairs)

        nodes_written = 3 + len(entity_pairs)  # Project + Domain + Subdomain + entities
        edges_written = 2 + len(entity_pairs) + (len(entity_pairs) * (len(entity_pairs) - 1)) // 2

        log.info("Built graph for Project %s (%d nodes, %d edges).", project_id, nodes_written, edges_written)
        return {
            "project_id": project_id,
            "nodes_written": nodes_written,
            "edges_written": edges_written,
        }

    @staticmethod
    def _ingest_tx(tx, project_id: str, title: str, domain: str, sub_domain: str, extracted_entities: dict):
        params = {
            "project_id": project_id,
            "title": title,
            "domain": domain,
            "sub_domain": sub_domain,
        }
        for cat_key in CATEGORY_EDGE_MAP:
            params[cat_key] = extracted_entities.get(cat_key, [])

        query_parts = ["""
            MERGE (p:Project {id: $project_id})
            SET p.title = $title, p.domain = $domain, p.sub_domain = $sub_domain, p.updated_at = datetime()
            MERGE (d:Domain {name: $domain})
            MERGE (sd:Subdomain {name: $sub_domain})
            MERGE (sd)-[:SUBDOMAIN_OF]->(d)
            MERGE (p)-[:HAS_DOMAIN]->(d)
            MERGE (p)-[:HAS_SUBDOMAIN]->(sd)
        """]
        for cat_key, (label, rel_type) in CATEGORY_EDGE_MAP.items():
            query_parts.append(f"""
            WITH p
            CALL {{
                WITH p
                UNWIND ${cat_key} AS ent_name
                MERGE (n:{label} {{name: ent_name}})
                MERGE (p)-[:{rel_type}]->(n)
                RETURN count(*) AS {cat_key}_count
            }}
            """)
        query_parts.append("RETURN p.id AS project_id")
        tx.run("\n".join(query_parts), **params)

    @staticmethod
    def _co_occurrence_tx(tx, project_id: str, entity_pairs: list[tuple[str, str]]):
        pair_params = [
            {"a_label": entity_pairs[i][0], "a_name": entity_pairs[i][1],
             "b_label": entity_pairs[j][0], "b_name": entity_pairs[j][1]}
            for i in range(len(entity_pairs))
            for j in range(i + 1, len(entity_pairs))
        ]
        tx.run(
            """
            UNWIND $pairs AS pair
            MATCH (a) WHERE pair.a_label IN labels(a) AND a.name = pair.a_name
            MATCH (b) WHERE pair.b_label IN labels(b) AND b.name = pair.b_name
            MERGE (a)-[r:CO_OCCURS]-(b)
            ON CREATE SET r.weight = 1, r.project_ids = [$project_id]
            ON MATCH SET
                r.weight = CASE
                    WHEN $project_id IN coalesce(r.project_ids, []) THEN r.weight
                    ELSE coalesce(r.weight, 0) + 1
                END,
                r.project_ids = CASE
                    WHEN $project_id IN coalesce(r.project_ids, []) THEN r.project_ids
                    ELSE coalesce(r.project_ids, []) + $project_id
                END
            """,
            pairs=pair_params,
            project_id=project_id,
        )


    def ping(self) -> dict:
        """Returns connectivity status — safe to call from a /health endpoint."""
        try:
            with self.session() as s:
                result = s.run("RETURN 1 AS ok")
                result.single()
            return {"connected": True, "uri": settings.NEO4J_URI,
                    "database": settings.NEO4J_DATABASE or "default"}
        except GraphUnavailableError as e:
            return {"connected": False, "uri": settings.NEO4J_URI, "error": str(e)}
        except Exception as e:
            return {"connected": False, "uri": settings.NEO4J_URI, "error": str(e)}

    def get_graph_stats(self) -> dict:
        """Returns node/edge counts per label — used by the /graph/stats API."""
        try:
            with self.session() as s:
                labels_res = s.run(
                    "CALL apoc.meta.stats() YIELD labels, relTypesCount "
                    "RETURN labels, relTypesCount"
                )
                row = labels_res.single()
                if row:
                    return {"labels": dict(row["labels"]),
                            "relationships": dict(row["relTypesCount"]),
                            "source": "apoc"}
        except Exception:
            pass  # APOC not available on all Aura tiers — fall back
        try:
            with self.session() as s:
                counts = {}
                for label in ["Project", "Domain", "Subdomain",
                              "Algorithm", "Technology", "Framework",
                              "Library", "Dataset", "Application",
                              "Hardware", "Metric"]:
                    r = s.run(f"MATCH (n:{label}) RETURN count(n) AS c")
                    counts[label] = r.single()["c"]
                rel_r = s.run("MATCH ()-[r]->() RETURN count(r) AS c")
                return {"labels": counts,
                        "total_relationships": rel_r.single()["c"],
                        "source": "manual_count"}
        except GraphUnavailableError as e:
            return {"error": str(e)}


# Singleton instance
graph_service = ProjectGraphService()
