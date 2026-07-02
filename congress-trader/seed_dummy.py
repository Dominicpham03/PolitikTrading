"""
Generate realistic DUMMY data so the dashboard is populated without any API keys.

Run:  python seed_dummy.py

Creates a spread of buys from various politicians over the last ~30 days, walks
prices forward so some positions are up and some down, and writes equity-history
snapshots so the graph has a shape. Safe: touches only the data files.
"""
from __future__ import annotations

import os
import random
import time

import config
import pricing
import portfolio

POLITICIANS = [
    "Nancy Pelosi", "Tommy Tuberville", "Dan Crenshaw",
    "Ro Khanna", "Michael McCaul", "Josh Gottheimer",
]
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM"]

DAY = 86_400


def _reset() -> None:
    for f in (portfolio.TRADES_FILE, portfolio.EQUITY_FILE,
              pricing.PRICES_FILE, portfolio.TXN_LOG):
        if os.path.exists(f):
            os.remove(f)


def run() -> None:
    config.validate_data_dir()
    _reset()
    now = time.time()

    chosen = random.sample(TICKERS, 6)

    # Initial buys spread across the last ~30 days.
    for i, tk in enumerate(chosen):
        ts = now - (30 - i * 4) * DAY
        buy_price = round(pricing.get_price(tk) * random.uniform(0.88, 1.0), 2)
        notional = random.choice([100.0, 150.0, 200.0])
        shares = notional / buy_price
        politician = random.choice(POLITICIANS)
        portfolio.record_trade(
            tk, "BUY", shares, buy_price,
            reason=f"{politician} disclosed a Purchase",
            simulated=True, ts=ts,
        )

    # Walk prices forward in steps, snapshotting equity each step -> graph shape.
    steps = 14
    for s in range(steps):
        ts = now - (steps - s) * 2 * DAY
        pricing.update_prices(chosen)
        portfolio.snapshot_equity(ts=ts)

    pricing.update_prices(chosen)
    summ = portfolio.snapshot_equity(ts=now)

    print("Seeded dummy data into:", config.DATA_DIR)
    print(f"  positions : {len(summ['rows'])}")
    print(f"  invested  : ${summ['total_cost']:,.2f}")
    print(f"  value     : ${summ['total_value']:,.2f}")
    print(f"  net P&L   : ${summ['net_pnl']:,.2f} ({summ['net_pct']:+.2f}%)")
    print("\nNow run:  python dashboard.py   ->   http://localhost:5000")


if __name__ == "__main__":
    run()
