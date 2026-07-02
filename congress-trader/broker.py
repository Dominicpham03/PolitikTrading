"""
Broker layer — Alpaca execution, wrapped in hard risk controls.

Every order goes through place_buy(), which enforces the limits in config.py
BEFORE anything is submitted. In DRY_RUN mode nothing is ever sent.
"""
from __future__ import annotations

import logging

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

import config
import pricing
import portfolio

log = logging.getLogger("congress-trader")


class Broker:
    def __init__(self) -> None:
        self.client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=config.ALPACA_PAPER,
        )
        # Track how much we've committed during this run (daily-spend cap).
        self.spent_this_run = 0.0

    # --- account / state helpers ---
    def account_summary(self) -> str:
        a = self.client.get_account()
        mode = "PAPER" if config.ALPACA_PAPER else "*** LIVE / REAL MONEY ***"
        return (f"[{mode}] equity=${float(a.equity):,.2f} "
                f"cash=${float(a.cash):,.2f} status={a.status}")

    def market_is_open(self) -> bool:
        return bool(self.client.get_clock().is_open)

    def held_symbols(self) -> set[str]:
        return {p.symbol.upper() for p in self.client.get_all_positions()}

    def open_position_count(self) -> int:
        return len(self.client.get_all_positions())

    # --- the one place orders are created ---
    def place_buy(self, ticker: str, reason: str) -> bool:
        """Run all risk checks, then submit (or simulate) a notional buy.
        Returns True if an order was placed (or would be, in dry run)."""
        notional = config.NOTIONAL_PER_TRADE

        # RISK CHECK 1: daily spend cap.
        if self.spent_this_run + notional > config.MAX_DAILY_SPEND:
            log.warning("  SKIP %s: would exceed MAX_DAILY_SPEND ($%.0f)", ticker, config.MAX_DAILY_SPEND)
            return False

        # RISK CHECK 2: max open positions.
        if self.open_position_count() >= config.MAX_OPEN_POSITIONS:
            log.warning("  SKIP %s: at MAX_OPEN_POSITIONS (%d)", ticker, config.MAX_OPEN_POSITIONS)
            return False

        # RISK CHECK 3: don't stack into something we already hold.
        if config.SKIP_IF_ALREADY_HELD and ticker in self.held_symbols():
            log.info("  SKIP %s: already held", ticker)
            return False

        # RISK CHECK 4: market hours.
        if config.ONLY_TRADE_WHEN_MARKET_OPEN and not self.market_is_open():
            log.info("  SKIP %s: market is closed", ticker)
            return False

        # Reference price for recording the trade. In dry run / paper this is
        # our price source; for a real fill you'd use the broker's fill price.
        price = pricing.get_price(ticker)
        shares = notional / price if price else 0.0

        # All checks passed.
        if config.DRY_RUN:
            log.info("  [DRY RUN] would BUY $%.0f of %s  (%s)", notional, ticker, reason)
            portfolio.record_trade(ticker, "BUY", shares, price,
                                   reason=reason, simulated=True)
            self.spent_this_run += notional
            return True

        order = MarketOrderRequest(
            symbol=ticker,
            notional=notional,            # buy by dollar amount, supports fractions
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        submitted = self.client.submit_order(order)
        self.spent_this_run += notional
        portfolio.record_trade(ticker, "BUY", shares, price,
                               reason=reason, simulated=False)
        log.info("  ORDER placed: BUY $%.0f %s id=%s  (%s)", notional, ticker, submitted.id, reason)
        return True
