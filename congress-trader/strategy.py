"""
Strategy / decision layer.

Turns raw congressional disclosures into a list of "signals" we might act on.
This is intentionally simple and rule-based so its behavior is obvious. Tune
the rules in config.py, not here.
"""
from __future__ import annotations

from datetime import date, timedelta

import config
from quiver_client import CongressTrade


def _days_ago(d: date | None) -> int | None:
    if d is None:
        return None
    return (date.today() - d).days


def filter_signals(trades: list[CongressTrade]) -> list[CongressTrade]:
    """Apply the rules from config to decide which trades become buy signals."""
    signals: list[CongressTrade] = []

    for t in trades:
        # 1. Must be a transaction type we follow (buys only, by default).
        if t.transaction not in config.FOLLOW_TRANSACTIONS:
            continue

        # 2. Must have a usable ticker.
        if not t.ticker or not t.ticker.isalpha():
            continue

        # 3. Must be recently disclosed (we react to the REPORT date).
        age = _days_ago(t.report_date)
        if age is None or age > config.SIGNAL_LOOKBACK_DAYS:
            continue

        # 4. Optional: only follow specific politicians.
        if config.FOLLOW_POLITICIANS:
            name = t.politician.lower()
            if not any(p in name for p in config.FOLLOW_POLITICIANS):
                continue

        signals.append(t)

    # De-duplicate by ticker — if 3 politicians bought NVDA, that's one buy.
    seen: set[str] = set()
    unique: list[CongressTrade] = []
    for s in signals:
        if s.ticker not in seen:
            seen.add(s.ticker)
            unique.append(s)

    return unique
