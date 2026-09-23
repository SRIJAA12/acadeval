"""
Module 4 — Project Knowledge Graph Router
==========================================
REST API endpoints for inspecting, visualising, exporting, and managing
the Project Knowledge Graph.

Routes:
  GET  /api/graph/summary        — overall graph metrics (density, nodes, edges, top centrality)
  GET  /api/graph/visualization  — D3 force payload ({nodes:[], links:[]}) for UI visualizer
  GET  /api/graph/node/{query}    — 1-hop / 2-hop neighborhood of a specific node
  POST /api/graph/rebuild        — trigger bulk re-ingestion of all projects into the graph
  GET  /api/graph/export         — export graph structure as JSON
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response
from app.dependencies import DB, CurrentUser, CurrentFacultyOrHOD
from app.models.project import Project
from app.services.graph_networkx import (
    get_cached_graph,
    get_graph_metrics,
    export_d3_graph,
    get_node_neighborhood,
    invalidate_graph_cache,
    export_project_d3_graph,
    export_comparison_d3_graph,
)
from app.services.graph_builder import bulk_rebuild_graph, ingest_project_to_relational_graph

log = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Module 4 — Knowledge Graph Construction"])


@router.get("/summary", summary="Get overall Knowledge Graph metrics")
def get_summary(current_user: CurrentUser, db: DB, refresh: bool = Query(False)):
    """
    Returns summary statistics for the Knowledge Graph:
    total nodes, total edges, graph density, node type breakdown,
    relationship type breakdown, and top nodes by degree centrality.
    """
    try:
        G = get_cached_graph(db, force_reload=refresh)
        metrics = get_graph_metrics(G)
        return {
            "status": "ok",
            "metrics": metrics,
        }
    except Exception as e:
        log.error("Failed to compute graph summary: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate graph summary: {e}")


@router.get("/visualization", summary="Get D3.js/Cytoscape format payload for graph visualization")
def get_visualization(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(300, ge=10, le=1000, description="Max nodes to return"),
    node_types: Optional[str] = Query(None, description="Comma-separated node types to include (e.g. Algorithm,Technology)"),
):
    """
    Returns nodes and links formatted for force-directed graph rendering.
    """
    try:
        G = get_cached_graph(db)
        type_filter = [t.strip() for t in node_types.split(",")] if node_types else None
        d3_data = export_d3_graph(G, max_nodes=limit, node_type_filter=type_filter)
        return {
            "status": "ok",
            **d3_data,
        }
    except Exception as e:
        log.error("Failed to export visualization graph: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load graph visualization data: {e}")


@router.get("/node/{query}", summary="Get neighborhood subgraph for a specific node")
def inspect_node(
    query: str,
    current_user: CurrentUser,
    db: DB,
    radius: int = Query(1, ge=1, le=3, description="Hops to include around target node"),
):
    """
    Returns the target node's details and its surrounding 1-hop or 2-hop neighborhood.
    """
    try:
        G = get_cached_graph(db)
        res = get_node_neighborhood(G, query=query, radius=radius)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return {
            "status": "ok",
            **res,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to inspect node %r: %s", query, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving node neighborhood: {e}")


@router.post("/rebuild", summary="Bulk re-ingest all project proposals into Knowledge Graph")
def rebuild_knowledge_graph(current_user: CurrentFacultyOrHOD, db: DB):
    """
    Clears PostgreSQL `graph_nodes` & `graph_edges` and re-ingests all stored projects.
    Requires Faculty or HOD role.
    """
    try:
        res = bulk_rebuild_graph(db)
        invalidate_graph_cache()
        return {
            "status": "rebuilt",
            "result": res,
        }
    except Exception as e:
        log.error("Bulk graph rebuild failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph rebuild failed: {e}")


@router.get("/export", summary="Export full Knowledge Graph as JSON payload")
def export_graph_data(current_user: CurrentUser, db: DB):
    """
    Exports the complete NetworkX graph structure as JSON.
    """
    try:
        G = get_cached_graph(db)
        d3_data = export_d3_graph(G, max_nodes=5000)
        return {
            "status": "ok",
            **d3_data,
        }
    except Exception as e:
        log.error("Graph export failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/project/{project_id}", summary="Get isolated Knowledge Graph for a single project")
def get_project_graph(project_id: str, current_user: CurrentUser, db: DB):
    """
    Returns the project-scoped graph: Project node, Domain/Subdomain,
    extracted entity nodes (Algorithms, Technologies, Frameworks, etc.),
    and their intra-project relationships.
    """
    try:
        data = export_project_d3_graph(db, project_id)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to export project graph for %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load project graph: {e}")


@router.get("/comparison/{project_id}", summary="Get comparison Knowledge Graph between project and related projects")
def get_comparison_graph(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    distance_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Max Jaccard distance threshold for related projects"),
):
    """
    Returns a unified comparison graph highlighting:
    - Target project nodes and links
    - Similar/related project nodes and links
    - Overlapping/shared entities between projects
    - Sets related_project_available=False if no project meets distance threshold
    """
    try:
        data = export_comparison_d3_graph(db, project_id, distance_threshold=distance_threshold)
        return data
    except Exception as e:
        log.error("Failed to export comparison graph for %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load comparison graph: {e}")


@router.post("/rebuild/{project_id}", summary="Reconstruct Knowledge Graph for a single project")
def rebuild_project_graph(project_id: str, current_user: CurrentFacultyOrHOD, db: DB):
    """
    Reconstructs the PostgreSQL and Neo4j graph nodes and edges specifically
    for the selected project.
    """
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    from app.services.entity_normalizer import canonicalize_extracted_entities
    entities = canonicalize_extracted_entities(proj.extracted_entities or {})
    proj.extracted_entities = entities
    db.add(proj)
    db.commit()

    domain = entities.get("domain", proj.domain or "General CSE")
    sub_domain = entities.get("sub_domain", "Machine Learning")

    try:
        res = ingest_project_to_relational_graph(
            db=db,
            project_id=str(proj.id),
            title=proj.title or "",
            domain=domain,
            sub_domain=sub_domain,
            extracted_entities=entities,
        )
        invalidate_graph_cache()
        return {
            "status": "rebuilt",
            "project_id": str(proj.id),
            "result": res,
        }
    except Exception as e:
        log.error("Single project graph rebuild failed for %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph rebuild failed: {e}")

