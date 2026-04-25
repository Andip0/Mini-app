"""
tasks.py — Celery application and task definitions.

Architecture
────────────
  run_job()          ← regular task that acts as an orchestrator
      │
      └─ chord(
             [compute_single(n) for n in numbers]   ← parallel header tasks
             |
             aggregate_results()                     ← callback runs after ALL header tasks finish
         ).apply_async()

A Celery *chord* is the idiomatic primitive for fan-out/fan-in:
  • The *header* is a group of tasks that execute in parallel across
    all available workers.
  • The *callback* (body) runs exactly once, receiving a list of every
    header result in order, after every header task has succeeded.
"""

import math
import time
import os

from celery import Celery, chord
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Celery application — broker and result backend both point to Redis.
# The URLs are injected via environment variables in docker-compose.yml.
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "demo_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Keep results in Redis for 1 hour so the frontend can poll lazily.
    result_expires=3600,
    # Acknowledge the task only after it finishes — safer retry behaviour.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ---------------------------------------------------------------------------
# Sub-task: runs in parallel, one per input number
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=2)
def compute_single(self, number: float, operation: str) -> dict:
    """
    Apply *operation* to a single number.

    Simulates I/O latency (0.5 s) so parallel execution is clearly visible
    in the demo — if tasks were instant the benefit would be invisible.
    """
    try:
        logger.info("compute_single(%s, op=%s) started", number, operation)
        time.sleep(0.5)                   # simulate work / I/O

        if operation == "square":
            output = number ** 2
        elif operation == "cube":
            output = number ** 3
        elif operation == "factorial":
            output = float(math.factorial(int(number)))
        else:
            raise ValueError(f"Unknown operation: {operation}")

        logger.info("compute_single(%s) → %s", number, output)
        return {"input": number, "output": output, "operation": operation}

    except Exception as exc:
        # Retry up to max_retries times before propagating the exception.
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Chord callback: runs once, receives list of all sub-task results
# ---------------------------------------------------------------------------

@celery_app.task
def aggregate_results(results: list) -> dict:
    """
    Receive the ordered list of per-number results and compute summary stats.
    This task runs in the worker *after* every compute_single task finishes.
    """
    logger.info("aggregate_results called with %d results", len(results))

    outputs = [r["output"] for r in results]
    summary = {
        "count": len(outputs),
        "total": sum(outputs),
        "min": min(outputs),
        "max": max(outputs),
        "average": sum(outputs) / len(outputs) if outputs else 0,
    }
    return {"results": results, "summary": summary}


# ---------------------------------------------------------------------------
# Orchestrator task: entry-point called by the FastAPI endpoint
# ---------------------------------------------------------------------------

@celery_app.task
def run_job(numbers: list, operation: str = "square") -> dict:
    """
    Fan out one compute_single task per number, then collect with aggregate_results.

    We call chord(...).apply_async() here so the *chord id* (returned by
    apply_async) is what the API stores as the job_id.  Polling that id
    gives the final aggregated result once all sub-tasks finish.

    Note: run_job itself returns immediately after scheduling the chord;
    the real work happens asynchronously across the worker pool.
    """
    logger.info("run_job: scheduling %d tasks op=%s", len(numbers), operation)

    header = [compute_single.s(n, operation) for n in numbers]
    callback = aggregate_results.s()

    chord(header)(callback)
