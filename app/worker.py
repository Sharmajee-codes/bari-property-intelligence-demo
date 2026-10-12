"""Optional local report worker. Ingestion remains explicit and synthetic-only."""

import logging
import os
import signal
import threading
from pathlib import Path

from app.db import SessionLocal
from app.logging import event
from app.services.quality import save_report


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    interval = max(10, int(os.getenv("WORKER_INTERVAL_SECONDS", "3600")))
    while not stop.is_set():
        try:
            with SessionLocal.begin() as session:
                save_report(session, Path("reports"))
        except Exception as exc:
            event("report_worker_failure", reason=str(exc))
        stop.wait(interval)


if __name__ == "__main__":
    main()
