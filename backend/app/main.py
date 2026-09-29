from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.services.graph_db import graph_service
from app.routers import (
    auth, projects, reports, reviews,
    appeals, rubrics, viva,
    leaderboard, dashboard, users,
    acadeval_plus, entities, graph, integrations
)
from app.database import engine, Base

app = FastAPI(
    title="AcadEval API",
    description="AI-based Academic Project Evaluation Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Static uploads ────────────────────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api"

app.include_router(auth.router,          prefix=API_PREFIX)
app.include_router(projects.router,      prefix=API_PREFIX)
app.include_router(reports.router,       prefix=API_PREFIX)
app.include_router(reviews.router,       prefix=API_PREFIX)
app.include_router(appeals.router,       prefix=API_PREFIX)
app.include_router(rubrics.router,       prefix=API_PREFIX)
app.include_router(viva.router,          prefix=API_PREFIX)
app.include_router(leaderboard.router,   prefix=API_PREFIX)
app.include_router(dashboard.router,     prefix=API_PREFIX)
app.include_router(users.router,         prefix=API_PREFIX)
app.include_router(acadeval_plus.router, prefix=API_PREFIX)
app.include_router(entities.router,      prefix=API_PREFIX)  # Module 3 — entity KB & pending review
app.include_router(graph.router,         prefix=API_PREFIX)  # Module 4 — Knowledge Graph engine
app.include_router(integrations.router,  prefix=API_PREFIX)  # Module 13 — SS / GitHub / Moodle


@app.on_event("startup")
def on_startup():
    import logging
    log = logging.getLogger(__name__)
    # Database availability is mandatory. Failing startup is safer than
    # silently switching stores or serving a partially functional API.
    Base.metadata.create_all(bind=engine)
    try:
        graph_service.ensure_constraints()
    except Exception as e:
        log.warning("Neo4j constraints check skipped: %s", e)

    # Eager warm-up: load the in-memory corpus index (the default novelty
    # scoring engine, settings.NOVELTY_GRAPH_BACKEND) now, not on the first
    # submission. A broken CSV path/format then fails loudly at boot with a
    # clear traceback instead of surfacing as a mysterious 500 on someone's
    # first real submission.
    from app.services.corpus_index import get_corpus_index
    index = get_corpus_index()
    log.info(
        "Corpus index warmed: %d projects loaded from %s",
        index.n_projects, index.csv_path,
    )
    if index.n_projects == 0:
        log.warning(
            "Corpus index loaded 0 projects (csv_path=%s) -- the corpus "
            "scoring engine will return 'insufficient_historical_evidence' "
            "for every submission until this is fixed.",
            index.csv_path,
        )


@app.on_event("shutdown")
def on_shutdown():
    graph_service.close()


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
