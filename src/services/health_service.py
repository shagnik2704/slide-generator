"""Health check service for probing dependencies and infrastructure availability.

Probes:
  1. PostgreSQL database connection & query latency
  2. Redis cache & Celery broker connection & ping latency
  3. Celery background Whisper workers
  4. Local disk storage accessibility & disk space usage
"""

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.api.config import settings
from src.core.metrics import (
    SERVICE_AVAILABILITY,
    SERVICE_CHECK_LATENCY_SECONDS,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def check_postgres() -> Tuple[bool, float, str]:
    """Probe PostgreSQL database connectivity with a lightweight SELECT 1 query."""
    t0 = time.perf_counter()
    try:
        from src.script_chat.persistence import get_pool
        pool = get_pool()
        async with pool.connection(timeout=settings.database_pool_timeout_seconds) as conn:
            await conn.execute("SELECT 1")
        latency = time.perf_counter() - t0
        return True, latency, "PostgreSQL connected and responsive"
    except Exception as exc:
        latency = time.perf_counter() - t0
        return False, latency, f"PostgreSQL probe failed: {exc}"


async def check_redis() -> Tuple[bool, float, str]:
    """Probe Redis broker responsiveness via PING command."""
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    t0 = time.perf_counter()
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            broker_url,
            socket_timeout=1.0,
            socket_connect_timeout=0.5,
        )
        pong = await client.ping()
        await client.aclose()
        latency = time.perf_counter() - t0
        if pong:
            return True, latency, "Redis connected and responsive"
        return False, latency, "Redis returned false to ping"
    except Exception as exc:
        latency = time.perf_counter() - t0
        return False, latency, f"Redis probe failed: {exc}"


async def check_celery_worker() -> Tuple[bool, int, List[str], str]:
    """Probe running Celery workers using inspector ping."""
    try:
        from src.workers.celery_app import celery_app
        responses = await asyncio.to_thread(celery_app.control.ping, timeout=1.0)
        if not responses:
            return False, 0, [], "No Celery workers responded to ping"
        
        active_workers = []
        for resp in responses:
            for worker_name, status in resp.items():
                if status.get("ok") == "pong":
                    active_workers.append(worker_name)
        
        is_healthy = len(active_workers) > 0
        msg = f"{len(active_workers)} Celery worker(s) online" if is_healthy else "No healthy Celery workers found"
        return is_healthy, len(active_workers), active_workers, msg
    except Exception as exc:
        return False, 0, [], f"Celery worker probe failed: {exc}"


def check_storage() -> Tuple[bool, Dict[str, Any], str]:
    """Probe local storage paths for writeability and free disk capacity."""
    output_dir = PROJECT_ROOT / "output"
    uploads_dir = PROJECT_ROOT / "uploads"

    output_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    test_file = output_dir / f".probe_{int(time.time())}"
    try:
        test_file.write_text("probe")
        test_file.unlink()
        writable = True
    except Exception:
        writable = False

    usage = shutil.disk_usage(output_dir)
    total_gb = round(usage.total / (1024**3), 2)
    free_gb = round(usage.free / (1024**3), 2)
    used_gb = round(usage.used / (1024**3), 2)
    percent_used = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0.0

    details = {
        "writable": writable,
        "total_gb": total_gb,
        "free_gb": free_gb,
        "used_gb": used_gb,
        "percent_used": percent_used,
    }

    if not writable:
        return False, details, "Storage directory is not writable"
    if percent_used >= 95.0:
        return False, details, f"Storage space critically low ({percent_used}% used)"

    return True, details, f"Storage healthy ({free_gb} GB free)"


async def check_all_services(update_metrics: bool = True) -> Dict[str, Any]:
    """Run all dependency probes and optionally update Prometheus availability gauges."""
    # Probe Postgres, Redis, and Storage concurrently
    pg_res, redis_res, storage_res = await asyncio.gather(
        check_postgres(),
        check_redis(),
        asyncio.to_thread(check_storage),
        return_exceptions=True,
    )

    pg_ok, pg_lat, pg_msg = pg_res if isinstance(pg_res, tuple) else (False, 0.0, str(pg_res))
    redis_ok, redis_lat, redis_msg = redis_res if isinstance(redis_res, tuple) else (False, 0.0, str(redis_res))
    storage_ok, storage_info, storage_msg = (
        storage_res if isinstance(storage_res, tuple) else (False, {}, str(storage_res))
    )

    # Celery workers communicate over Redis broker; if Redis is down, workers are unreachable
    if redis_ok:
        try:
            celery_res = await check_celery_worker()
            celery_ok, celery_count, celery_names, celery_msg = celery_res
        except Exception as exc:
            celery_ok, celery_count, celery_names, celery_msg = False, 0, [], str(exc)
    else:
        celery_ok, celery_count, celery_names, celery_msg = (
            False,
            0,
            [],
            "Redis broker unreachable; Celery workers offline",
        )


    if update_metrics:
        try:
            SERVICE_AVAILABILITY.labels(service="postgres").set(1.0 if pg_ok else 0.0)
            SERVICE_AVAILABILITY.labels(service="redis").set(1.0 if redis_ok else 0.0)
            SERVICE_AVAILABILITY.labels(service="celery_worker").set(1.0 if celery_ok else 0.0)
            SERVICE_AVAILABILITY.labels(service="storage").set(1.0 if storage_ok else 0.0)

            SERVICE_CHECK_LATENCY_SECONDS.labels(service="postgres").set(pg_lat)
            SERVICE_CHECK_LATENCY_SECONDS.labels(service="redis").set(redis_lat)
        except Exception:
            pass

    # Overall service status calculation
    if not pg_ok or not storage_ok:
        overall_status = "unhealthy"
    elif not redis_ok or not celery_ok:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "environment": settings.environment,
        "timestamp": time.time(),
        "dependencies": {
            "postgres": {
                "status": "healthy" if pg_ok else "unhealthy",
                "latency_seconds": round(pg_lat, 4),
                "message": pg_msg,
            },
            "redis": {
                "status": "healthy" if redis_ok else "unhealthy",
                "latency_seconds": round(redis_lat, 4),
                "message": redis_msg,
            },
            "celery_worker": {
                "status": "healthy" if celery_ok else "unhealthy",
                "active_workers": celery_count,
                "workers": celery_names,
                "message": celery_msg,
            },
            "storage": {
                "status": "healthy" if storage_ok else "unhealthy",
                "details": storage_info,
                "message": storage_msg,
            },
        },
    }
