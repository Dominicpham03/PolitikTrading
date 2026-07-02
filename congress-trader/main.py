"""
Congress-follow trading pipeline:  Quiver signal -> decision -> Alpaca execution.

Run a single pass:   python main.py
Run continuously:    python daemon.py

Safe by default:
  - Uses your Alpaca PAPER account (config.ALPACA_PAPER).
  - DRY_RUN is True, so it only LOGS what it would do until you turn it off.
"""
from __future__ import annotations

import logging

import config
import quiver_client
import state
import strategy
from broker import Broker

log = logging.getLogger("congress-trader")


def run_once(broker: Broker | None = None) -> None:
    """One full pass of the pipeline. Reuses a Broker if given (daemon does)."""
    config.validate()
    broker = broker or Broker()

    log.info("--- pass start | DRY_RUN=%s PAPER=%s notional=$%.0f cap=$%.0f ---",
             config.DRY_RUN, config.ALPACA_PAPER,
             config.NOTIONAL_PER_TRADE, config.MAX_DAILY_SPEND)
    log.info(broker.account_summary())
    broker.spent_this_run = 0.0  # reset the per-pass daily-spend counter

    # 1. SIGNAL
    trades = quiver_client.get_recent_trades()
    log.info("Pulled %d recent congressional trades from Quiver.", len(trades))

    # 2. DECISION
    signals = strategy.filter_signals(trades)
    log.info("%d passed the strategy filter (buys, recent, unique).", len(signals))

    # 3. EXECUTION — skip anything we've already acted on in a prior pass.
    placed = 0
    for s in signals:
        if state.already_acted(s.key()):
            log.debug("  skip %s: already acted on this disclosure", s.ticker)
            continue

        reason = f"{s.politician} disclosed a {s.transaction} (disclosed {s.report_date})"
        if broker.place_buy(s.ticker, reason):
            placed += 1
            # Only remember it as "done" once a REAL order is placed, so dry
            # runs keep surfacing signals for you to inspect.
            if not config.DRY_RUN:
                state.mark_acted(s.key())

    log.info("pass done: %d order(s) %s; $%.0f committed.",
             placed, "simulated" if config.DRY_RUN else "placed",
             broker.spent_this_run)


def _setup_console_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    _setup_console_logging()
    run_once()
