"""
AcadEval+ — Celery Application
================================
Single source of truth for the Celery instance.  Both the FastAPI process
(which enqueues tasks) and the Celery worker process (which executes them)
import from this module, so there is no risk of configuration drift.

Beat schedule (requires running:  celery -A app.worker beat):
  - Weekly  trend refresh        — every Sunday at 00:00 UTC
  - Nightly correlation run      — every night   at 02:00 UTC (legacy; superseded
                                    by eval.run_faculty_agreement below, kept for now)
  - eval.check_versions          — every 10 min (also fires once at worker startup,
                                    see worker_ready below, as a "was the machine off
                                    overnight" catch-up) — auto-runs the benchmark
                                    when the scoring method's fingerprint changes
  - eval.run_benchmark           — nightly  02:10 UTC
  - eval.run_graph_integrity     — nightly  02:20 UTC
  - eval.run_faculty_agreement   — nightly  02:30 UTC
  - eval.rollup_online           — hourly, on the hour
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
        "app.tasks.evaluation",  # continuous evaluation: benchmark, graph integrity, faculty agreement
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

# Redis' broker-side visibility_timeout defaults to 3600s: with task_acks_late,
# any task still running past that gets silently redelivered to a second worker
# process while the first keeps running -- two copies of the same work at once.
# eval.run_benchmark carries its own 30-min time_limit (see tasks/evaluation.py);
# this just needs to comfortably exceed every task's time_limit.
celery_app.conf.broker_transport_options = {"visibility_timeout": 2400}

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
    "eval-check-versions": {
        "task": "eval.check_versions",
        "schedule": 600.0,  # every 10 minutes
        "options": {"queue": "eval"},
    },
    "eval-nightly-benchmark": {
        "task": "eval.run_benchmark",
        "schedule": crontab(hour=2, minute=10),
        "kwargs": {"trigger": "schedule"},
        "options": {"queue": "eval"},
    },
    "eval-nightly-graph-integrity": {
        "task": "eval.run_graph_integrity",
        "schedule": crontab(hour=2, minute=20),
        "kwargs": {"trigger": "schedule"},
        "options": {"queue": "eval"},
    },
    "eval-nightly-faculty-agreement": {
        "task": "eval.run_faculty_agreement",
        "schedule": crontab(hour=2, minute=30),
        "kwargs": {"trigger": "schedule"},
        "options": {"queue": "eval"},
    },
    "eval-hourly-rollup": {
        "task": "eval.rollup_online",
        "schedule": crontab(minute=0),
        "options": {"queue": "eval"},
    },
}

# ── Queue routing ─────────────────────────────────────────────────────────────
# Pipeline tasks go to "pipeline", periodic to "periodic", continuous
# evaluation to its own "eval" queue so a long benchmark run never blocks a
# real submission. All three are served by the same worker in dev.
celery_app.conf.task_routes = {
    "pipeline.*":   {"queue": "pipeline"},
    "scheduled.*":  {"queue": "periodic"},
    "eval.*":       {"queue": "eval"},
}

celery_app.conf.task_default_queue = "pipeline"


# ── Startup catch-up ──────────────────────────────────────────────────────────
# The dev machine is often off overnight, so beat's 10-minute check_versions
# schedule alone could miss a long gap. Fire it once when a worker comes up.
from celery.signals import worker_ready  # noqa: E402


@worker_ready.connect
def _trigger_startup_version_check(**_kwargs):
    try:
        celery_app.send_task("eval.check_versions", queue="eval")
    except Exception:
        pass  # best-effort — the 10-minute beat schedule will catch it anyway
