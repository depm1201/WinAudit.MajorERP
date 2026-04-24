from __future__ import annotations

import logging
import signal
import time

logger = logging.getLogger("majorerp.worker")


def main() -> None:
    running = True

    def _stop(*_args) -> None:
        nonlocal running
        running = False
        logger.info("Worker de MajorERP detenido por señal.")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Worker de MajorERP iniciado y en espera.")
    while running:
        time.sleep(5)

    logger.info("Worker de MajorERP finalizando correctamente.")


if __name__ == "__main__":
    main()
