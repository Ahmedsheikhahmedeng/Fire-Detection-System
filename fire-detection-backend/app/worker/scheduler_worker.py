import asyncio
import logging
import signal

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time_utils import utc_now
from app.services.ml_service import load_ml_model
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.scheduler_state import write_scheduler_state

logger = logging.getLogger("fire_detection.scheduler_worker")


def _write_worker_state(values: dict) -> None:
    db = SessionLocal()
    try:
        write_scheduler_state(db, values)
    finally:
        db.close()


async def _heartbeat_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await asyncio.to_thread(
            _write_worker_state,
            {
                "worker_status": "running",
                "worker_last_seen_at": utc_now().isoformat(),
            },
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            continue


async def run_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    stop_event = asyncio.Event()

    if not settings.ENABLE_SCHEDULER:
        await asyncio.to_thread(
            _write_worker_state,
            {
                "worker_status": "disabled",
                "worker_last_seen_at": utc_now().isoformat(),
            },
        )
        logger.warning(
            "Scheduler worker ENABLE_SCHEDULER=false ile baslatildi; is yapmadan bekleyecek."
        )
        heartbeat_task = None
    else:
        load_ml_model()
        await asyncio.to_thread(
            _write_worker_state,
            {
                "worker_status": "running",
                "worker_started_at": utc_now().isoformat(),
                "worker_last_seen_at": utc_now().isoformat(),
            },
        )
        start_scheduler()
        heartbeat_task = asyncio.create_task(_heartbeat_loop(stop_event))
        logger.info("Scheduler worker baslatildi.")

    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
        stop_scheduler()
        await asyncio.to_thread(
            _write_worker_state,
            {
                "worker_status": "stopped",
                "worker_last_seen_at": utc_now().isoformat(),
            },
        )
        logger.info("Scheduler worker durduruldu.")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
