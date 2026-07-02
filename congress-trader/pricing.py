"""
Current-price provider.

Offline/dummy mode (no Alpaca keys needed): simulates prices with a small
random walk, persisted to prices.json. When you add real Alpaca keys you can
extend get_price()/update_prices() to pull live quotes instead — the rest of
the app doesn't care where the numbers come from.
"""
from __future__ import annotations

import json
import os
import random
import time

import config

PRICES_FILE = os.path.join(config.DATA_DIR, "prices.json")

# Seed prices for common tickers so dummy data looks realistic.
DEFAULT_BASE = {
    "AAPL": 195.0, "MSFT": 420.0, "NVDA": 120.0, "TSLA": 250.0, "AMZN": 185.0,
    "GOOGL": 175.0, "META": 500.0, "JPM": 200.0, "XOM": 110.0, "DIS": 100.0,
}


def _load() -> dict:
    if os.path.exists(PRICES_FILE):
        try:
            with open(PRICES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(d: dict) -> None:
    tmp = PRICES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, PRICES_FILE)


def _seed_price(ticker: str) -> float:
    return DEFAULT_BASE.get(ticker, round(random.uniform(20, 300), 2))


def get_price(ticker: str) -> float:
    """Latest price for one ticker (initializes it if unseen)."""
    t = ticker.upper()
    d = _load()
    if t not in d:
        d[t] = {"price": _seed_price(t), "updated": time.time()}
        _save(d)
    return d[t]["price"]


def update_prices(tickers: list[str]) -> dict[str, float]:
    """Random-walk existing prices (+/-3%) and init any new ones.
    Returns {ticker: price}. (Swap this body for live Alpaca quotes later.)"""
    d = _load()
    for raw in tickers:
        t = raw.upper()
        if t in d:
            drift = random.uniform(-0.03, 0.03)
            new_price = max(0.5, round(d[t]["price"] * (1 + drift), 2))
        else:
            new_price = _seed_price(t)
        d[t] = {"price": new_price, "updated": time.time()}
    _save(d)
    return {t.upper(): d[t.upper()]["price"] for t in tickers}


def all_prices() -> dict[str, float]:
    return {k: v["price"] for k, v in _load().items()}
