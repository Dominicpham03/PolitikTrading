"""
Portfolio ledger + P&L math.  JSON-backed, no database needed.

Three files live in DATA_DIR:
  trades.json          every buy/sell the daemon has done
  equity_history.json  periodic snapshots of total value (drives the graph)
  transactions.log     human-readable, one line per trade (what you asked for)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import time
from threading import Lock

import config
import pricing

TRADES_FILE = os.path.join(config.DATA_DIR, "trades.json")
EQUITY_FILE = os.path.join(config.DATA_DIR, "equity_history.json")
TXN_LOG = os.path.join(config.DATA_DIR, "transactions.log")

_lock = Lock()


def _load(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def _save(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def record_trade(ticker: str, side: str, shares: float, price: float,
                 reason: str = "", simulated: bool = True,
                 ts: float | None = None) -> dict:
    """Append a trade to the ledger and the human-readable transaction log."""
    ts = ts or time.time()
    trade = {
        "id": int(ts * 1000),
        "timestamp": ts,
        "ticker": ticker.upper(),
        "side": side.upper(),
        "shares": round(shares, 6),
        "price": round(price, 2),
        "notional": round(shares * price, 2),
        "reason": reason,
        "simulated": simulated,
    }
    with _lock:
        trades = _load(TRADES_FILE, [])
        trades.append(trade)
        _save(TRADES_FILE, trades)

    stamp = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    tag = "SIM " if simulated else "LIVE"
    line = (f"{stamp} {tag} {side.upper():4} {shares:9.4f} {ticker.upper():6} "
            f"@ ${price:8.2f} = ${shares * price:9.2f}  {reason}\n")
    with open(TXN_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    return trade


def positions() -> dict[str, dict]:
    """Aggregate trades into current holdings: {ticker: {shares, cost}}."""
    pos: dict[str, dict] = {}
    for t in _load(TRADES_FILE, []):
        p = pos.setdefault(t["ticker"], {"shares": 0.0, "cost": 0.0})
        if t["side"] == "BUY":
            p["shares"] += t["shares"]
            p["cost"] += t["notional"]
        else:  # SELL reduces shares and cost proportionally
            if p["shares"] > 0:
                avg = p["cost"] / p["shares"]
                p["shares"] -= t["shares"]
                p["cost"] -= avg * t["shares"]
    return {k: v for k, v in pos.items() if v["shares"] > 1e-6}


def summary() -> dict:
    """Per-stock and total P&L using the latest prices."""
    prices = pricing.all_prices()
    rows = []
    total_cost = total_val = 0.0
    for tk, p in sorted(positions().items()):
        price = prices.get(tk) or pricing.get_price(tk)
        shares, cost = p["shares"], p["cost"]
        value = shares * price
        pnl = value - cost
        pct = (pnl / cost * 100) if cost else 0.0
        rows.append({
            "ticker": tk,
            "shares": round(shares, 4),
            "avg_cost": round(cost / shares, 2) if shares else 0.0,
            "price": round(price, 2),
            "cost": round(cost, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pct": round(pct, 2),
        })
        total_cost += cost
        total_val += value

    net = total_val - total_cost
    return {
        "rows": rows,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_val, 2),
        "net_pnl": round(net, 2),
        "net_pct": round((net / total_cost * 100) if total_cost else 0.0, 2),
    }


def snapshot_equity(ts: float | None = None) -> dict:
    """Append a point to the equity-history graph and return the summary."""
    ts = ts or time.time()
    s = summary()
    with _lock:
        hist = _load(EQUITY_FILE, [])
        hist.append({
            "timestamp": ts,
            "cost": s["total_cost"],
            "value": s["total_value"],
            "pnl": s["net_pnl"],
        })
        _save(EQUITY_FILE, hist)
    return s


def equity_history() -> list:
    return _load(EQUITY_FILE, [])


def trades() -> list:
    return _load(TRADES_FILE, [])
