from __future__ import annotations

from oculis_api.core.config import settings
from oculis_api.services.analysis_runner import run_analysis_job


def get_analysis_queue():
    from redis import Redis
    from rq import Queue

    connection = Redis.from_url(settings.redis_url)
    return Queue(
        "oculis-analysis",
        connection=connection,
        default_timeout=settings.analysis_timeout_seconds + 30,
    )


def enqueue_analysis(analysis_id: str) -> str:
    job = get_analysis_queue().enqueue(run_analysis_job, analysis_id)
    return job.id
