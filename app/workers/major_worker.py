from __future__ import annotations

import logging
import signal
import time

from app.core.config import settings
from app.core.logging_config import setup_logging

logger = logging.getLogger("majorerp.worker")


def configure_worker_logging() -> None:
    setup_logging(service="worker", level=settings.LOG_LEVEL)


def main() -> None:
    configure_worker_logging()
    running = True

    def _stop(*_args) -> None:
        nonlocal running
        running = False
        logger.info("Worker de MajorERP detenido por senal.")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Worker de MajorERP iniciado y en espera.")
    while running:
        time.sleep(5)

    logger.info("Worker de MajorERP finalizando correctamente.")


if __name__ == "__main__":
    main()
