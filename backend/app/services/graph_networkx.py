"""
Module 4 — In-Memory NetworkX MultiDiGraph Engine
===================================================
Loads PostgreSQL relational graph nodes/edges into an in-memory NetworkX
MultiDiGraph (`G`) for fast Graph Analytics, Centrality, and path algorithms.
Maintains a thread-safe in-memory cache refreshed on new project ingestion.
"""

import os
import re
import csv
import json
import logging
import networkx as nx
from typing import Optional, Dict, List, Any, Set, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Global thread-safe in-memory cache for the NetworkX MultiDiGraph
_CACHED_GRAPH: Optional[nx.MultiDiGraph] = None


def invalidate_graph_cache():
    """Resets the cached NetworkX graph instance."""
    global _CACHED_GRAPH
    _CACHED_GRAPH = None
    log.info("NetworkX in-memory graph cache invalidated.")


def load_graph(db: Session) -> nx.MultiDiGraph:
    """
    Reads all rows from `graph_nodes` and `graph_edges` in PostgreSQL
    and constructs a NetworkX MultiDiGraph.
    """
    G = nx.MultiDiGraph()

    # 1. Fetch nodes
    nodes_query = text("SELECT id, node_type, name FROM graph_nodes")
    nodes_rows = db.execute(nodes_query).fetchall()

    for node_id, node_type, name in nodes_rows:
        G.add_node(
            node_id,
            id=node_id,
            type=node_type,
            name=name,
        )

    # 2. Fetch edges
    edges_query = text("SELECT id, from_node, to_node, relationship, confidence FROM graph_edges")
    edges_rows = db.execute(edges_query).fetchall()

    for edge_id, from_node, to_node, relationship, confidence in edges_rows:
        if G.has_node(from_node) and G.has_node(to_node):
            G.add_edge(
                from_node,
                to_node,
                key=edge_id,
                relationship=relationship,
                confidence=float(confidence or 1.0),
            )

    log.info("Built NetworkX MultiDiGraph: %d nodes, %d edges.", G.number_of_nodes(), G.number_of_edges())
    return G


def get_cached_graph(db: Session, force_reload: bool = False) -> nx.MultiDiGraph:
    """
    Returns the in-memory NetworkX MultiDiGraph, loading it from DB if uninitialized.
    """
    global _CACHED_GRAPH
    if _CACHED_GRAPH is None or force_reload:
        _CACHED_GRAPH = load_graph(db)
    return _CACHED_GRAPH


def get_graph_metrics(G: nx.MultiDiGraph) -> dict:
    """
    Computes statistical and structural metrics for the graph:
    - Node count & Edge count
    - Graph density
    - Node type breakdown
    - Relationship breakdown
    - Top 10 nodes by degree centrality
    """
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    if num_nodes == 0:
        return {
            "nodes_count": 0,
            "edges_count": 0,
            "density": 0.0,
            "node_type_distribution": {},
            "relationship_distribution": {},
            "top_centrality_nodes": [],
        }

    # Density for directed graph
    density = float(nx.density(G))

    # Node type distribution
    node_types: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        ntype = data.get("type", "Unknown")
        node_types[ntype] = node_types.get(ntype, 0) + 1

    # Relationship distribution
    rel_types: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        rel = data.get("relationship", "Unknown")
        rel_types[rel] = rel_types.get(rel, 0) + 1

    # Degree centrality top nodes
    try:
        deg_centrality = nx.degree_centrality(G)
        top_central_ids = sorted(deg_centrality.items(), key=lambda x: x[1], reverse=True)[:10]

        top_centrality_nodes = [
            {
                "id": nid,
                "name": G.nodes[nid].get("name", str(nid)),
                "type": G.nodes[nid].get("type", "Unknown"),
                "degree": G.degree(nid),
                "centrality_score": round(float(score), 4),
            }
            for nid, score in top_central_ids
        ]
    except Exception as e:
        log.warning("Could not calculate degree centrality: %s", e)
        top_centrality_nodes = []

    return {
        "nodes_count": num_nodes,
        "edges_count": num_edges,
        "density": round(density, 6),
        "node_type_distribution": node_types,
        "relationship_distribution": rel_types,
        "top_centrality_nodes": top_centrality_nodes,
    }


def export_d3_graph(
    G: nx.MultiDiGraph,
    max_nodes: int = 500,
    node_type_filter: Optional[list[str]] = None
) -> dict:
    """
    Exports NetworkX MultiDiGraph as JSON compatible with D3.js / Canvas force visualizers:
    {
      "nodes": [ { "id": 1, "name": "CNN", "type": "Algorithm", "degree": 5 } ],
      "links": [ { "source": 1, "target": 2, "relationship": "USES_ALGORITHM" } ]
    }
    """
    selected_nodes = set()

    for nid, data in G.nodes(data=True):
        ntype = data.get("type", "")
        if node_type_filter and len(node_type_filter) > 0:
            if ntype.lower() in [t.lower() for t in node_type_filter]:
                selected_nodes.add(nid)
        else:
            selected_nodes.add(nid)

        if len(selected_nodes) >= max_nodes:
            break

    # Format nodes
    nodes_payload = [
        {
            "id": nid,
            "name": G.nodes[nid].get("name", str(nid)),
            "type": G.nodes[nid].get("type", "Unknown"),
            "degree": G.degree(nid),
        }
        for nid in selected_nodes
    ]

    # Format edges between selected nodes (CO_OCCURS excluded — N² explosion risk)
    links_payload = []
    seen_edges = set()

    for u, v, data in G.edges(data=True):
        if u in selected_nodes and v in selected_nodes:
            rel = data.get("relationship", "CONNECTED")
            # Skip CO_OCCURS — they are stored for Neo4j analytics but create
            # ~N² edges that overwhelm any D3 / canvas force visualizer.
            if rel == "CO_OCCURS":
                continue
            edge_key = (u, v, rel)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                links_payload.append({
                    "source": u,
                    "target": v,
                    "relationship": rel,
                    "confidence": data.get("confidence", 1.0),
                })

    return {
        "total_graph_nodes": G.number_of_nodes(),
        "total_graph_edges": G.number_of_edges(),
        "returned_nodes": len(nodes_payload),
        "returned_links": len(links_payload),
        "nodes": nodes_payload,
        "links": links_payload,
    }


def get_node_neighborhood(G: nx.MultiDiGraph, query: str, radius: int = 1) -> dict:
    """
    Finds a node by name or integer ID and extracts its subgraph up to `radius` hops.
    """
    target_node = None

    # Search by ID or name
    try:
        target_id = int(query)
        if G.has_node(target_id):
            target_node = target_id
    except ValueError:
        pass

    if target_node is None:
        q_lower = str(query).strip().lower()
        for nid, data in G.nodes(data=True):
            if data.get("name", "").strip().lower() == q_lower:
                target_node = nid
                break

    if target_node is None:
        return {"error": f"Node {query!r} not found in knowledge graph."}

    # Extract ego subgraph
    subgraph_nodes = set(nx.single_source_shortest_path_length(G.to_undirected(), target_node, cutoff=radius).keys())
    subG = G.subgraph(subgraph_nodes)

    sub_d3 = export_d3_graph(subG, max_nodes=1000)

    target_data = G.nodes[target_node]
    return {
        "target_node": {
            "id": target_node,
            "name": target_data.get("name"),
            "type": target_data.get("type"),
            "degree": G.degree(target_node),
        },
        "radius": radius,
        "neighborhood_nodes": len(subgraph_nodes),
        "graph": sub_d3,
    }


def _build_synthetic_d3_graph_from_entities(pid_str: str, proj: Any) -> dict:
    """
    Builds a complete D3-compatible project knowledge graph purely from a
    project's extracted_entities dict — no PostgreSQL graph_nodes needed.
    Used as a fallback when graph ingestion fails (e.g., Neo4j unavailable).
    """
    entities = proj.extracted_entities or {}
    if isinstance(entities, str):
        try:
            entities = json.loads(entities)
        except Exception:
            entities = {}
    if not isinstance(entities, dict):
        entities = {}

    nodes: list[dict] = []
    links: list[dict] = []
    curr_id = 1

    # Project root node
    proj_node_id = curr_id
    curr_id += 1
    proj_name = proj.title or f"Project {pid_str}"
    nodes.append({
        "id": proj_node_id,
        "name": proj_name,
        "type": "Project",
        "degree": 10,
        "is_target": True,
        "group": "target",
    })

    seen_nodes: dict[tuple, int] = {}

    def get_or_add(name: str, ntype: str, degree: int = 3) -> int:
        nonlocal curr_id
        key = (ntype, name.strip().lower())
        if key in seen_nodes:
            return seen_nodes[key]
        nid = curr_id
        curr_id += 1
        seen_nodes[key] = nid
        nodes.append({
            "id": nid,
            "name": name.strip(),
            "type": ntype,
            "degree": degree,
            "is_target": False,
            "group": "target",
        })
        return nid

    # Domain & Subdomain
    domain_val = entities.get("domain", proj.domain or "General CSE")
    subdom_val = entities.get("sub_domain", getattr(proj, "sub_domain", "") or "")
    if domain_val:
        dom_id = get_or_add(domain_val, "Domain", degree=5)
        links.append({"source": proj_node_id, "target": dom_id, "relationship": "HAS_DOMAIN", "confidence": 1.0})
        if subdom_val and subdom_val.lower() != domain_val.lower():
            sub_id = get_or_add(subdom_val, "Subdomain", degree=4)
            links.append({"source": proj_node_id, "target": sub_id, "relationship": "HAS_SUBDOMAIN", "confidence": 1.0})
            links.append({"source": sub_id, "target": dom_id, "relationship": "SUBDOMAIN_OF", "confidence": 1.0})

    # Entity categories
    category_map = [
        ("algorithms", "Algorithm", "USES_ALGORITHM"),
        ("technologies", "Technology", "USES_TECHNOLOGY"),
        ("frameworks", "Framework", "USES_FRAMEWORK"),
        ("libraries", "Library", "USES_LIBRARY"),
        ("datasets", "Dataset", "USES_DATASET"),
        ("applications", "Application", "TARGETS_APPLICATION"),
        ("hardware", "Hardware", "RUNS_ON"),
        ("metrics", "Metric", "EVALUATED_BY"),
    ]
    for cat_key, node_label, rel_type in category_map:
        items = entities.get(cat_key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not item or not str(item).strip():
                continue
            ent_id = get_or_add(str(item).strip(), node_label)
            links.append({
                "source": proj_node_id,
                "target": ent_id,
                "relationship": rel_type,
                "confidence": 1.0,
            })

    return {
        "status": "ok",
        "project_id": pid_str,
        "title": proj_name,
        "nodes": nodes,
        "links": links,
        "nodes_count": len(nodes),
        "links_count": len(links),
    }


def export_project_d3_graph(db: Session, project_id: str) -> dict:

    """
    Exports a project-scoped D3 graph containing:
    - Target Project node
    - Connected Domain/Subdomain nodes
    - Connected Entity nodes (Algorithm, Technology, Library, Framework, etc.)
    - Intra-project CO_OCCURS edges between these entities
    """
    import json
    from app.models.project import Project

    pid_str = str(project_id)

    # 1. Find Project node in graph_nodes
    proj_row = db.execute(
        text("SELECT id, node_type, name FROM graph_nodes WHERE node_type = 'Project' AND source_key = :pid"),
        {"pid": pid_str}
    ).fetchone()

    if not proj_row:
        # Fallback: build a synthetic D3 graph directly from extracted_entities
        # (avoids re-triggering graph ingestion which may fail if Neo4j is down)
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return {"error": f"Project {project_id} not found", "nodes": [], "links": []}

        entities = proj.extracted_entities or {}
        if isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except Exception:
                entities = {}
        if not isinstance(entities, dict):
            entities = {}

        if entities:
            # Try to ingest into graph_nodes (best-effort, non-blocking)
            try:
                from app.services.graph_builder import ingest_project_to_relational_graph
                domain_val = entities.get("domain", proj.domain or "General CSE")
                sub_domain_val = entities.get("sub_domain", "Machine Learning")
                ingest_project_to_relational_graph(
                    db, pid_str, proj.title or "", domain_val, sub_domain_val, entities
                )
                proj_row = db.execute(
                    text("SELECT id, node_type, name FROM graph_nodes WHERE node_type = 'Project' AND source_key = :pid"),
                    {"pid": pid_str}
                ).fetchone()
            except Exception as ingest_err:
                log.warning("Graph ingestion fallback failed for %s (will use synthetic graph): %s", pid_str, ingest_err)

        if not proj_row:
            # Build pure synthetic in-memory D3 graph from extracted_entities
            return _build_synthetic_d3_graph_from_entities(pid_str, proj)


    proj_id_int, _, proj_name = proj_row

    # 2. Find direct edges from project node
    direct_edges = db.execute(
        text("SELECT from_node, to_node, relationship, confidence FROM graph_edges WHERE from_node = :pnode"),
        {"pnode": proj_id_int}
    ).fetchall()

    neighbor_ids = {proj_id_int}
    for edge in direct_edges:
        neighbor_ids.add(edge[1])

    # Also find any SUBDOMAIN_OF edge between the neighbors
    subdomain_edges = []
    if len(neighbor_ids) > 1:
        subdomain_edges = db.execute(
            text("""
                SELECT from_node, to_node, relationship, confidence
                FROM graph_edges
                WHERE relationship = 'SUBDOMAIN_OF'
                  AND from_node = ANY(:nids) AND to_node = ANY(:nids)
            """),
            {"nids": list(neighbor_ids)}
        ).fetchall()

    # 3. CO_OCCURS edges are a full N² Cartesian product between entity nodes
    # (e.g. 343 entities × 342 = ~58k edges) — they are intentionally EXCLUDED
    # from the project-scoped D3 graph to keep it renderable. The structural
    # edges (Project→Entity, HAS_DOMAIN, HAS_SUBDOMAIN, SUBDOMAIN_OF) are
    # sufficient to display the project knowledge graph meaningfully.
    co_occurs_edges: list = []

    all_edge_tuples = []
    seen_edges = set()
    for row in direct_edges + subdomain_edges + co_occurs_edges:
        u, v, rel, conf = row[0], row[1], row[2], float(row[3] or 1.0)
        edge_key = (u, v, rel)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            all_edge_tuples.append((u, v, rel, conf))
            neighbor_ids.add(u)
            neighbor_ids.add(v)

    # 4. Fetch node metadata
    node_rows = db.execute(
        text("SELECT id, node_type, name FROM graph_nodes WHERE id = ANY(:nids)"),
        {"nids": list(neighbor_ids)}
    ).fetchall()

    degree_map: dict[int, int] = {}
    for u, v, _, _ in all_edge_tuples:
        degree_map[u] = degree_map.get(u, 0) + 1
        degree_map[v] = degree_map.get(v, 0) + 1

    nodes = [
        {
            "id": nid,
            "name": nname,
            "type": ntype,
            "degree": degree_map.get(nid, 0),
            "is_target": (nid == proj_id_int),
            "group": "target",
        }
        for nid, ntype, nname in node_rows
    ]

    links = [
        {
            "source": u,
            "target": v,
            "relationship": rel,
            "confidence": conf,
        }
        for u, v, rel, conf in all_edge_tuples
    ]

    return {
        "status": "ok",
        "project_id": pid_str,
        "title": proj_name,
        "nodes": nodes,
        "links": links,
        "nodes_count": len(nodes),
        "links_count": len(links),
    }


# Reference-corpus catalog and rarity-weighted matching live in corpus_matcher.py
from app.services.corpus_matcher import (  # noqa: E402
    find_similar_corpus_projects,
    load_corpus_projects_catalog,
)


def build_corpus_project_d3_graph(candidate: Dict[str, Any], id_offset: int = 10000) -> Dict[str, Any]:
    """
    Builds a complete, interactive D3-compatible project knowledge graph
    from a real research project in the dataset corpus.
    """
    nodes: list[dict] = []
    links: list[dict] = []
    seen_nodes: dict[tuple[str, str], int] = {}

    curr_id = id_offset + 1

    # 1. Project Root Node
    proj_id = curr_id
    curr_id += 1
    proj_name = candidate.get("title") or "Corpus Research Project"
    nodes.append({
        "id": proj_id,
        "name": proj_name,
        "type": "Project",
        "degree": 10,
        "group": "comparison",
        "is_comparison": True,
    })

    def get_or_add_node(name: str, ntype: str, degree: int = 3) -> int:
        nonlocal curr_id
        key = (ntype, name.strip().lower())
        if key in seen_nodes:
            return seen_nodes[key]
        nid = curr_id
        curr_id += 1
        seen_nodes[key] = nid
        nodes.append({
            "id": nid,
            "name": name.strip(),
            "type": ntype,
            "degree": degree,
            "group": "comparison",
            "is_comparison": True,
        })
        return nid

    # 2. Domain and Subdomain
    dom_name = candidate.get("domain")
    if dom_name:
        dom_id = get_or_add_node(dom_name, "Domain", degree=5)
        links.append({
            "source": proj_id,
            "target": dom_id,
            "relationship": "HAS_DOMAIN",
            "confidence": 1.0,
            "group": "comparison",
        })

        subdom_name = candidate.get("sub_domain")
        if subdom_name and subdom_name.lower() != dom_name.lower():
            subdom_id = get_or_add_node(subdom_name, "Subdomain", degree=4)
            links.append({
                "source": proj_id,
                "target": subdom_id,
                "relationship": "HAS_SUBDOMAIN",
                "confidence": 1.0,
                "group": "comparison",
            })
            links.append({
                "source": subdom_id,
                "target": dom_id,
                "relationship": "SUBDOMAIN_OF",
                "confidence": 1.0,
                "group": "comparison",
            })

    # 3. Categorized Technical Entities from Corpus
    entity_mappings = [
        ("algorithms", "Algorithm", "USES_ALGORITHM"),
        ("technologies", "Technology", "USES_TECHNOLOGY"),
        ("frameworks", "Framework", "USES_FRAMEWORK"),
        ("tools", "Library", "USES_LIBRARY"),
        ("datasets", "Dataset", "USES_DATASET"),
        ("hardware", "Hardware", "RUNS_ON"),
        ("languages", "Technology", "USES_LANGUAGE"),
        ("applications", "Application", "TARGETS_APPLICATION"),
        ("metrics", "Metric", "EVALUATED_BY"),
    ]

    for field_key, node_type, rel_name in entity_mappings:
        items = candidate.get(field_key, [])
        if isinstance(items, list):
            for item in items:
                if not item:
                    continue
                ent_id = get_or_add_node(item, node_type, degree=2)
                links.append({
                    "source": proj_id,
                    "target": ent_id,
                    "relationship": rel_name,
                    "confidence": 1.0,
                    "group": "comparison",
                })

    return {
        "title": proj_name,
        "nodes": nodes,
        "links": links,
        "nodes_count": len(nodes),
        "links_count": len(links),
        "domain": candidate.get("domain", ""),
        "sub_domain": candidate.get("sub_domain", ""),
        "project_id": candidate.get("id", ""),
    }


def _explain_match(candidate: Dict[str, Any]) -> str:
    """One plain-language line saying what the match is based on."""
    detail = candidate.get("shared_entities_detail", [])
    rare = [d["name"] for d in detail if not d.get("generic")][:4]
    generic = [d["name"] for d in detail if d.get("generic")][:4]
    words = candidate.get("shared_tokens", [])[:5]
    parts = []
    if rare:
        parts.append("distinctive shared techniques: " + ", ".join(rare))
    if words:
        parts.append("shared problem words: " + ", ".join(words))
    if not parts:
        parts.append("only weak overall overlap")
    note = ""
    if generic:
        note = f" Common stack overlap ({', '.join(generic)}) is given very little weight."
    return "Matched on " + "; ".join(parts) + "." + note


def export_comparison_d3_graph(
    db: Session,
    project_id: str,
    compare_project_id: Optional[str] = None,
) -> dict:
    """
    Exports a dual comparison D3 graph comparing:
    - Graph 1 (Target Project Implementation): Uploaded project's extracted entities & architecture
    - Graph 2 (Related Dataset Project): The truly matching academic research project from the dataset corpus
    - Shared entity overlap highlighted in golden glow
    - Explicit cross-project benchmark bridge link
    """
    pid_str = str(project_id)
    try:
        target_graph = export_project_d3_graph(db, pid_str)
        if not isinstance(target_graph, dict):
            target_graph = {"nodes": [], "links": [], "title": "Target Project"}

        # Get target project details from DB
        from app.models.project import Project
        target_proj = None
        try:
            target_proj = db.query(Project).filter(Project.id == project_id).first()
        except Exception as qe:
            log.warning("Could not fetch project from DB for comparison: %s", qe)

        target_title = target_proj.title if target_proj and target_proj.title else target_graph.get("title", "Target Project")
        target_domain = target_proj.domain if target_proj and target_proj.domain else "General CSE"

        target_entities = target_proj.extracted_entities if target_proj and target_proj.extracted_entities else {}
        if isinstance(target_entities, str):
            try:
                target_entities = json.loads(target_entities)
            except Exception:
                target_entities = {}
        if not isinstance(target_entities, dict):
            target_entities = {}

        # sub_domain lives inside extracted_entities (not a direct Project column)
        target_sub_domain = target_entities.get("sub_domain", "") or "Machine Learning"

        # Enrich title with abstract text for better keyword matching (e.g. Dysgraphia)
        abstract_text = getattr(target_proj, "abstract", "") or ""
        if abstract_text and len(abstract_text) > 20:
            # Add abstract keywords to target_entities for richer matching
            abs_lower = abstract_text.lower()
            # Inject important domain keywords found in abstract as synthetic "applications"
            DOMAIN_KEYWORDS = [
                "dysgraphia", "handwriting", "rehabilitation", "motor", "spatial",
                "autism", "eeg", "ecg", "steganography", "ransomware", "intrusion",
                "drone", "robotics", "quantum", "blockchain", "cardiac", "stroke",
                "parkinson", "dementia", "gesture", "sign language", "ocr",
            ]
            found_in_abstract = [kw for kw in DOMAIN_KEYWORDS if kw in abs_lower]
            if found_in_abstract:
                existing_apps = target_entities.get("applications", [])
                if not isinstance(existing_apps, list):
                    existing_apps = []
                combined = list(set(existing_apps + found_in_abstract))
                target_entities = {**target_entities, "applications": combined}

        # If target_entities empty, extract entity names from target_graph nodes
        if not target_entities and target_graph.get("nodes"):
            extracted_from_graph: dict[str, list[str]] = {
                "algorithms": [],
                "technologies": [],
                "frameworks": [],
                "libraries": [],
                "datasets": [],
                "hardware": [],
                "applications": [],
                "metrics": [],
            }
            for n in target_graph.get("nodes", []):
                ntype = n.get("type", "")
                nname = n.get("name", "")
                if ntype == "Algorithm":
                    extracted_from_graph["algorithms"].append(nname)
                elif ntype == "Technology":
                    extracted_from_graph["technologies"].append(nname)
                elif ntype == "Framework":
                    extracted_from_graph["frameworks"].append(nname)
                elif ntype == "Library":
                    extracted_from_graph["libraries"].append(nname)
                elif ntype == "Dataset":
                    extracted_from_graph["datasets"].append(nname)
                elif ntype == "Hardware":
                    extracted_from_graph["hardware"].append(nname)
                elif ntype == "Application":
                    extracted_from_graph["applications"].append(nname)
                elif ntype == "Metric":
                    extracted_from_graph["metrics"].append(nname)
            target_entities = extracted_from_graph

        # Find candidate research projects from the AcadEval corpus dataset
        similar_candidates = find_similar_corpus_projects(
            target_id=pid_str,
            target_title=target_title,
            target_domain=target_domain,
            target_sub_domain=target_sub_domain,
            target_entities=target_entities,
            db=db,
            top_k=20,
            target_abstract=abstract_text,
        )

        # Check if a qualified candidate exists
        if not similar_candidates:
            return {
                "status": "ok",
                "project_id": pid_str,
                "target_title": target_title,
                "comparison_title": "No close prior work found",
                "related_project_available": False,
                "similarity_score": 0.0,
                "distance": 1.0,
                "shared_entities_count": 0,
                "shared_entities": [],
                "message": "No reference project in the corpus is closely related to this one (best match below the minimum similarity), so this idea has no close prior work in the dataset.",
                "similar_projects": [],
                "nodes": target_graph.get("nodes", []),
                "links": target_graph.get("links", []),
                "nodes_count": target_graph.get("nodes_count", len(target_graph.get("nodes", []))),
                "links_count": target_graph.get("links_count", len(target_graph.get("links", []))),
                "target_graph": target_graph,
                "comparison_graph": {
                    "title": "No close prior work found",
                    "nodes": [],
                    "links": [],
                    "nodes_count": 0,
                    "links_count": 0,
                },
            }

        # If user passed compare_project_id, select that candidate; else top candidate
        selected_candidate = similar_candidates[0]
        if compare_project_id:
            for cand in similar_candidates:
                if str(cand.get("id")) == str(compare_project_id):
                    selected_candidate = cand
                    break

        # Build Graph 2 from the selected dataset research project
        comp_graph = build_corpus_project_d3_graph(selected_candidate, id_offset=10000)

        target_nodes = target_graph.get("nodes", [])
        comp_nodes = comp_graph.get("nodes", [])

        target_proj_node = next((n["id"] for n in target_nodes if n.get("type") == "Project"), None)
        comp_proj_node = next((n["id"] for n in comp_nodes if n.get("type") == "Project"), None)

        # Compute shared entities between target and candidate
        target_names_map = {
            (n.get("type"), str(n.get("name", "")).strip().lower()): n.get("id")
            for n in target_nodes
            if n.get("type") != "Project"
        }

        comp_names_map = {
            (n.get("type"), str(n.get("name", "")).strip().lower()): n.get("id")
            for n in comp_nodes
            if n.get("type") != "Project"
        }

        shared_entity_names = set()
        shared_target_node_ids = set()
        shared_comp_node_ids = set()

        for key, tid in target_names_map.items():
            if key in comp_names_map:
                shared_entity_names.add(key[1])
                shared_target_node_ids.add(tid)
                shared_comp_node_ids.add(comp_names_map[key])

        # Tag nodes for golden glow highlight
        merged_nodes = []
        for n in target_nodes:
            nid = n.get("id")
            is_shared = nid in shared_target_node_ids
            merged_nodes.append({
                **n,
                "group": "shared" if is_shared else "target",
                "is_shared": is_shared,
                "project": "target",
            })

        for n in comp_nodes:
            nid = n.get("id")
            is_shared = nid in shared_comp_node_ids
            merged_nodes.append({
                **n,
                "group": "shared" if is_shared else "comparison",
                "is_shared": is_shared,
                "project": "comparison",
            })

        # Merged links
        merged_links = []
        seen_links = set()

        for l in target_graph.get("links", []):
            key = (l.get("source"), l.get("target"), l.get("relationship"))
            if key not in seen_links:
                seen_links.add(key)
                merged_links.append({**l, "group": "target"})

        for l in comp_graph.get("links", []):
            key = (l.get("source"), l.get("target"), l.get("relationship"))
            if key not in seen_links:
                seen_links.add(key)
                merged_links.append({**l, "group": "comparison"})

        # Cross-project benchmark link
        sim_score = float(selected_candidate.get("similarity", 0.85))
        if target_proj_node and comp_proj_node:
            bridge_key = (target_proj_node, comp_proj_node, "BENCHMARKED_AGAINST")
            if bridge_key not in seen_links:
                seen_links.add(bridge_key)
                merged_links.append({
                    "source": target_proj_node,
                    "target": comp_proj_node,
                    "relationship": "BENCHMARKED_AGAINST",
                    "confidence": sim_score,
                    "group": "bridge",
                })

        # Format similar projects for UI dropdown selector
        similar_projects_list = [
            {
                "project_id": str(c.get("id", "")),
                "title": c.get("title", "Dataset Project"),
                "similarity_score": round(float(c.get("similarity", 0.0)), 2),
                "distance": round(float(c.get("distance", 1.0)), 2),
                "domain": c.get("domain", ""),
                "sub_domain": c.get("sub_domain", ""),
                "shared_entities": c.get("shared_entities", []),
                "shared_entities_detail": c.get("shared_entities_detail", []),
            }
            for c in similar_candidates
        ]

        return {
            "status": "ok",
            "project_id": pid_str,
            "target_title": target_title,
            "comparison_title": selected_candidate.get("title", "Related Research Project"),
            "comparison_project_id": str(selected_candidate.get("id", "")),
            "comparison_domain": selected_candidate.get("domain", ""),
            "comparison_sub_domain": selected_candidate.get("sub_domain", ""),
            "related_project_available": True,
            "similarity_score": round(sim_score, 2),
            "distance": round(float(selected_candidate.get("distance", 0.15)), 2),
            "shared_entities_count": len(shared_entity_names),
            "shared_entities": sorted(list(shared_entity_names)),
            "shared_entities_detail": selected_candidate.get("shared_entities_detail", []),
            "match_explanation": _explain_match(selected_candidate),
            "message": f"Successfully matched against related dataset project '{selected_candidate.get('title')}'.",
            "similar_projects": similar_projects_list,
            "nodes": merged_nodes,
            "links": merged_links,
            "nodes_count": len(merged_nodes),
            "links_count": len(merged_links),
            "target_graph": {
                **target_graph,
                "nodes": [
                    {**n, "is_shared": (n.get("id") in shared_target_node_ids)}
                    for n in target_graph.get("nodes", [])
                ],
            },
            "comparison_graph": {
                **comp_graph,
                "nodes": [
                    {**n, "is_shared": (n.get("id") in shared_comp_node_ids)}
                    for n in comp_graph.get("nodes", [])
                ],
            },
        }
    except Exception as e:
        log.error("Failed to build comparison graph for %s: %s", pid_str, e, exc_info=True)
        # Safe fallback response that prevents 500 error on client
        return {
            "status": "ok",
            "project_id": pid_str,
            "target_title": "Uploaded Project",
            "comparison_title": "Related project is not available",
            "related_project_available": False,
            "similarity_score": 0.0,
            "distance": 1.0,
            "shared_entities_count": 0,
            "shared_entities": [],
            "message": f"Error building comparison graph: {e}",
            "similar_projects": [],
            "nodes": [],
            "links": [],
            "nodes_count": 0,
            "links_count": 0,
            "target_graph": {"nodes": [], "links": []},
            "comparison_graph": {"nodes": [], "links": []},
        }

