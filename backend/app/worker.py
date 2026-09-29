"""
AcadEval+ — Celery Application
================================
Single source of truth for the Celery instance.  Both the FastAPI process
(which enqueues tasks) and the Celery worker process (which executes them)
import from this module, so there is no risk of configuration drift.

Beat schedule (requires running:  celery -A app.worker beat):
  - Weekly  trend refresh       — every Sunday at 00:00 UTC
  - Nightly correlation run     — every night   at 02:00 UTC
  - Pending Neo4j sync retry    — every 15 minutes
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "acadeval",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.pipeline",    # Module 11 — submission pipeline tasks
        "app.tasks.scheduled",   # Module 11 — periodic beat tasks
    ],
)

# ── Serialisation ─────────────────────────────────────────────────────────────
celery_app.conf.task_serializer    = "json"
celery_app.conf.result_serializer  = "json"
celery_app.conf.accept_content     = ["json"]

# ── Timezone ──────────────────────────────────────────────────────────────────
celery_app.conf.timezone           = "UTC"
celery_app.conf.enable_utc         = True

# ── Result expiry (keep task results 24 h so status polling always works) ─────
celery_app.conf.result_expires     = 86_400  # seconds

# ── Worker reliability ────────────────────────────────────────────────────────
import sys
if sys.platform == "win32":
    celery_app.conf.worker_pool = "solo"

celery_app.conf.task_acks_late              = True   # only ack after success
celery_app.conf.worker_prefetch_multiplier  = 1      # one task at a time per worker
celery_app.conf.task_reject_on_worker_lost  = True

# ── Beat schedule ─────────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "refresh-trend-base-weekly": {
        "task": "scheduled.refresh_trend_base",
        "schedule": crontab(hour=0, minute=0, day_of_week="sunday"),
        "options": {"queue": "periodic"},
    },
    "nightly-score-correlation": {
        "task": "scheduled.nightly_correlation",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "periodic"},
    },
    "retry-pending-neo4j-sync": {
        "task": "scheduled.retry_pending_neo4j_sync",
        "schedule": 900.0,  # every 15 minutes
        "options": {"queue": "periodic"},
    },
}

# ── Queue routing ─────────────────────────────────────────────────────────────
# Pipeline tasks go to the "pipeline" queue; periodic to "periodic".
# Both queues are served by the same worker in dev; split them in prod.
celery_app.conf.task_routes = {
    "pipeline.*":   {"queue": "pipeline"},
    "scheduled.*":  {"queue": "periodic"},
}

celery_app.conf.task_default_queue = "pipeline"
