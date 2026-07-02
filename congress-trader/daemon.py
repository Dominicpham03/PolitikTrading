"""
Long-running daemon: runs the pipeline forever on an interval.

  python daemon.py

Features:
  - Wakes every config.RUN_INTERVAL_HOURS and runs one pass.
  - Skips passes while the market is closed (config.DAEMON_ONLY_WHEN_MARKET_OPEN).
  - Logs to console AND config.LOG_FILE (rotating, 5 files x 1MB).
  - Survives errors in a single pass (logs and keeps going).
  - Shuts down cleanly on Ctrl+C / SIGTERM (so a service can stop it).
"""
from __future__ import annotations

import logging
import logging.handlers
import signal
import threading
import time

import config
import portfolio
import pricing
from broker import Broker
from main import run_once

log = logging.getLogger("congress-trader")

# Set when we want the loop to exit. Event.wait() lets us sleep but wake
# immediately on a shutdown signal instead of blocking for hours.
_stop = threading.Event()


def _setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    root = logging.getLogger("congress-trader")
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    fileh = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fileh.setFormatter(fmt)
    root.addHandler(fileh)


def _handle_signal(signum, _frame) -> None:
    log.info("Received signal %s — shutting down after current pass.", signum)
    _stop.set()


def main() -> None:
    _setup_logging()
    config.validate()

    # Catch Ctrl+C (SIGINT) and service-stop (SIGTERM where supported).
    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (AttributeError, ValueError):
        pass  # SIGTERM not available on some Windows setups

    interval_s = config.RUN_INTERVAL_HOURS * 3600
    log.info("Daemon started. interval=%.1fh  paper=%s  dry_run=%s",
             config.RUN_INTERVAL_HOURS, config.ALPACA_PAPER, config.DRY_RUN)

    # Reuse one Broker (one Alpaca connection) across all passes.
    broker = Broker()

    while not _stop.is_set():
        try:
            if config.DAEMON_ONLY_WHEN_MARKET_OPEN and not broker.market_is_open():
                log.info("Market closed — skipping trade pass.")
            else:
                run_once(broker=broker)

            # Refresh prices for what we hold and snapshot equity so the
            # dashboard graph keeps growing even between trades.
            held = list(portfolio.positions().keys())
            if held:
                pricing.update_prices(held)
            snap = portfolio.snapshot_equity()
            log.info("equity snapshot: value=$%.2f net=$%.2f (%.2f%%)",
                     snap["total_value"], snap["net_pnl"], snap["net_pct"])
        except Exception:  # never let one bad pass kill the daemon
            log.exception("Pass failed with an error; will retry next interval.")

        # Sleep until the next interval, but wake early if asked to stop.
        if _stop.wait(timeout=interval_s):
            break

    log.info("Daemon stopped cleanly.")


if __name__ == "__main__":
    main()
