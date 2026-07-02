"""
Quiver Quantitative client — pulls congressional trading disclosures.

We use plain HTTP (no extra SDK) so you can see exactly what is requested.
Docs: https://api.quiverquant.com/docs/
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
import requests

import config

BASE_URL = "https://api.quiverquant.com/beta"


@dataclass
class CongressTrade:
    """One disclosed congressional transaction, normalized."""
    politician: str
    ticker: str
    transaction: str          # "Purchase" or "Sale"
    amount_range: str         # e.g. "$1,001 - $15,000"
    trade_date: date | None   # when the trade actually happened
    report_date: date | None  # when it was disclosed (this is what we react to)
    raw: dict                 # original record, in case you want more fields

    def key(self) -> str:
        """Stable identity for de-duplication across daemon runs."""
        return f"{self.politician}|{self.ticker}|{self.transaction}|{self.report_date}"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    # Quiver returns ISO-ish dates like "2026-06-20".
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize(record: dict) -> CongressTrade:
    """Map Quiver's field names into our dataclass. Field names can vary
    slightly across endpoints, so we check a few common keys."""
    def pick(*keys, default=""):
        for k in keys:
            if k in record and record[k] not in (None, ""):
                return record[k]
        return default

    return CongressTrade(
        politician=pick("Representative", "Senator", "Name", "politician"),
        ticker=pick("Ticker", "ticker").upper(),
        transaction=pick("Transaction", "transaction"),
        amount_range=pick("Range", "Amount", "amount"),
        trade_date=_parse_date(pick("TransactionDate", "Date", "transactionDate", default=None)),
        report_date=_parse_date(pick("ReportDate", "Filed", "reportDate", default=None)),
        raw=record,
    )


def get_recent_trades() -> list[CongressTrade]:
    """Fetch the live feed of recent congressional trades."""
    url = f"{BASE_URL}/live/congresstrading"
    headers = {"Authorization": f"Bearer {config.QUIVER_API_KEY}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Quiver response shape: {type(data)}")

    return [_normalize(rec) for rec in data]


if __name__ == "__main__":
    # Quick manual test:  python quiver_client.py
    config.validate()
    trades = get_recent_trades()
    print(f"Fetched {len(trades)} recent congressional trades. First 5:")
    for t in trades[:5]:
        print(f"  {t.report_date}  {t.politician:25.25}  {t.transaction:9}  "
              f"{t.ticker:6}  {t.amount_range}")
