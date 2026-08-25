import asyncio
import json
import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Redis key prefixes (used for state/progress tracking alongside arq)
JOB_QUEUE_KEY = "llm_eval:jobs:queue"
JOB_STATE_KEY = "llm_eval:jobs:state:{job_id}"
JOB_PROGRESS_KEY = "llm_eval:jobs:progress:{job_id}"

# TTL for temporary state (24 hours)
STATE_TTL = 86400


def get_redis_client() -> redis.Redis:
    """Create a Redis client from settings with connection timeout."""
    settings = get_settings()
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def dispatch_job(job_id: str) -> None:
    """Dispatch a job to the arq worker pool (production async path).

    The arq worker consumes ``process_evaluation_job`` from its own queue;
    this is what the API uses to schedule background evaluation work.
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    async def _dispatch() -> None:
        pool = await create_pool(redis_settings)
        try:
            await pool.enqueue_job("process_evaluation_job", job_id)
        finally:
            # redis-py >= 5.0.1 renamed close() -> aclose(); support both.
            close = getattr(pool, "aclose", None) or pool.close
            await close()

    # Use a dedicated event loop — safe in sync FastAPI endpoints (threadpool)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_dispatch())
    finally:
        loop.close()

    set_job_state(job_id, "queued")
    logger.info("Job %s dispatched to arq pool", job_id)


def enqueue_job(job_id: str) -> None:
    """Push a job ID onto the Redis list queue (FIFO) and mark it queued."""
    r = get_redis_client()
    r.rpush(JOB_QUEUE_KEY, job_id)
    set_job_state(job_id, "queued")
    logger.info("Job %s enqueued", job_id)


def dequeue_job() -> str | None:
    """Pop a job ID from the Redis list queue (blocking with timeout)."""
    r = get_redis_client()
    result = r.blpop(JOB_QUEUE_KEY, timeout=5)
    if result:
        return result[1]
    return None


def set_job_state(job_id: str, state: str, **extra: Any) -> None:
    """Set job state in Redis with optional extra fields."""
    r = get_redis_client()
    key = JOB_STATE_KEY.format(job_id=job_id)
    data = {"state": state, **extra}
    r.set(key, json.dumps(data), ex=STATE_TTL)


def get_job_state(job_id: str) -> dict | None:
    """Get job state from Redis."""
    r = get_redis_client()
    key = JOB_STATE_KEY.format(job_id=job_id)
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None


def set_job_progress(job_id: str, total: int, completed: int, failed: int) -> None:
    """Update job progress in Redis."""
    r = get_redis_client()
    key = JOB_PROGRESS_KEY.format(job_id=job_id)
    data = {"total": total, "completed": completed, "failed": failed}
    r.set(key, json.dumps(data), ex=STATE_TTL)


def get_job_progress(job_id: str) -> dict | None:
    """Get job progress from Redis."""
    r = get_redis_client()
    key = JOB_PROGRESS_KEY.format(job_id=job_id)
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None


def cancel_job(job_id: str) -> bool:
    """Mark a job for cancellation in Redis.

    Returns True if the job was in a cancellable state.
    """
    r = get_redis_client()
    key = JOB_STATE_KEY.format(job_id=job_id)
    raw = r.get(key)
    if not raw:
        return False

    state_data = json.loads(raw)
    if state_data["state"] in ("completed", "failed", "cancelled"):
        return False

    set_job_state(job_id, "cancelled")
    return True
