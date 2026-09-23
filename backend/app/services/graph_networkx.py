"""
Module 4 — In-Memory NetworkX MultiDiGraph Engine
===================================================
Loads PostgreSQL relational graph nodes/edges into an in-memory NetworkX
MultiDiGraph (`G`) for fast Graph Analytics, Centrality, and path algorithms.
Maintains a thread-safe in-memory cache refreshed on new project ingestion.
"""

import logging
import networkx as nx
from typing import Optional
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
        # Fallback: check if project exists in DB and ingest on the fly if extracted_entities present
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return {"error": f"Project {project_id} not found", "nodes": [], "links": []}
        if proj.extracted_entities:
            from app.services.graph_builder import ingest_project_to_relational_graph
            entities = proj.extracted_entities or {}
            domain = entities.get("domain", proj.domain or "General CSE")
            sub_domain = entities.get("sub_domain", "Machine Learning")
            ingest_project_to_relational_graph(
                db, pid_str, proj.title or "", domain, sub_domain, entities
            )
            proj_row = db.execute(
                text("SELECT id, node_type, name FROM graph_nodes WHERE node_type = 'Project' AND source_key = :pid"),
                {"pid": pid_str}
            ).fetchone()

    if not proj_row:
        return {
            "status": "ok",
            "project_id": pid_str,
            "title": "Unprocessed Project",
            "nodes": [],
            "links": [],
            "nodes_count": 0,
            "links_count": 0,
        }

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


def export_comparison_d3_graph(
    db: Session,
    project_id: str,
    similar_project_ids: Optional[list[str]] = None,
    distance_threshold: float = 0.5,
) -> dict:
    """
    Exports a comparison D3 graph containing:
    - Target project nodes & relationships (group='target')
    - Similar project nodes & relationships (group='comparison')
    - Shared entity nodes (group='shared', is_shared=True)
    - Returns related_project_available=False if no similar projects meet threshold.
    """
    from app.models.evaluation import EvaluationReport

    pid_str = str(project_id)
    target_graph = export_project_d3_graph(db, pid_str)

    # Fetch similar projects if not explicitly provided
    sim_projects = []
    if similar_project_ids is not None:
        sim_projects = [{"project_id": spid, "similarity_score": 1.0} for spid in similar_project_ids]
    else:
        eval_rep = db.query(EvaluationReport).filter(EvaluationReport.project_id == project_id).first()
        if eval_rep and eval_rep.novelty_report:
            sim_projects = eval_rep.novelty_report.get("most_similar_projects", [])

    # Filter similar projects: must have valid ID, not equal to target, and pass threshold
    valid_sims = []
    for sp in sim_projects:
        sp_id = str(sp.get("project_id", "")).strip()
        if not sp_id or sp_id == pid_str:
            continue
        sim_score = float(sp.get("similarity_score", 0.0))
        # A project is related if jaccard distance (1 - sim_score) <= distance_threshold
        # or if sim_score >= (1.0 - distance_threshold)
        if sim_score >= (1.0 - distance_threshold) or (1.0 - sim_score) <= distance_threshold:
            valid_sims.append(sp)

    if not valid_sims:
        return {
            "status": "ok",
            "project_id": pid_str,
            "target_title": target_graph.get("title", "Target Project"),
            "related_project_available": False,
            "message": "Related project is not available (distance threshold not met).",
            "similar_projects": [],
            "nodes": target_graph.get("nodes", []),
            "links": target_graph.get("links", []),
            "nodes_count": len(target_graph.get("nodes", [])),
            "links_count": len(target_graph.get("links", [])),
        }

    # Merge target graph with top similar project graph (take top 1 or 2)
    top_sim = valid_sims[0]
    top_sim_id = str(top_sim.get("project_id", ""))
    sim_graph = export_project_d3_graph(db, top_sim_id)

    target_nodes_by_id = {n["id"]: n for n in target_graph.get("nodes", [])}
    sim_nodes_by_id = {n["id"]: n for n in sim_graph.get("nodes", [])}

    # Identify shared nodes (by ID or normalized entity name for non-Project types)
    target_names_map = {
        (n["type"], n["name"].strip().lower()): n["id"]
        for n in target_graph.get("nodes", [])
        if n.get("type") != "Project"
    }

    shared_node_ids = set()
    for nid, snode in sim_nodes_by_id.items():
        if nid in target_nodes_by_id and snode.get("type") != "Project":
            shared_node_ids.add(nid)
        else:
            key = (snode.get("type"), snode.get("name", "").strip().lower())
            if key in target_names_map:
                shared_node_ids.add(target_names_map[key])
                shared_node_ids.add(nid)

    merged_nodes = []
    seen_node_ids = set()

    for n in target_graph.get("nodes", []):
        nid = n["id"]
        seen_node_ids.add(nid)
        is_shared = nid in shared_node_ids
        merged_nodes.append({
            **n,
            "group": "shared" if is_shared else "target",
            "is_shared": is_shared,
            "project": "target",
        })

    for n in sim_graph.get("nodes", []):
        nid = n["id"]
        if nid not in seen_node_ids:
            seen_node_ids.add(nid)
            is_shared = nid in shared_node_ids
            merged_nodes.append({
                **n,
                "group": "shared" if is_shared else "comparison",
                "is_shared": is_shared,
                "project": "comparison",
            })

    # Merge links
    seen_links = set()
    merged_links = []

    for l in target_graph.get("links", []):
        key = (l["source"], l["target"], l["relationship"])
        if key not in seen_links:
            seen_links.add(key)
            merged_links.append({**l, "group": "target"})

    for l in sim_graph.get("links", []):
        key = (l["source"], l["target"], l["relationship"])
        if key not in seen_links:
            seen_links.add(key)
            merged_links.append({**l, "group": "comparison"})

    return {
        "status": "ok",
        "project_id": pid_str,
        "target_title": target_graph.get("title", "Target Project"),
        "comparison_title": sim_graph.get("title", top_sim.get("title", "Comparison Project")),
        "related_project_available": True,
        "similarity_score": top_sim.get("similarity_score", 0.0),
        "message": f"Comparing with {sim_graph.get('title', 'related project')}.",
        "similar_projects": valid_sims,
        "nodes": merged_nodes,
        "links": merged_links,
        "nodes_count": len(merged_nodes),
        "links_count": len(merged_links),
    }

