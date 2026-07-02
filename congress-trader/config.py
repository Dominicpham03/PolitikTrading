"""
Central configuration and RISK CONTROLS.

Everything that decides "how much risk" lives here so it is easy to find and
audit. Read every value before you ever flip ALPACA_PAPER to false.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Credentials (loaded from .env) ---
QUIVER_API_KEY = os.getenv("QUIVER_API_KEY", "")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")

# Paper trading is ON unless you explicitly set ALPACA_PAPER=false in .env.
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() != "false"


# --- Strategy parameters ---
# Only act on disclosures whose REPORT date is within this many days.
# (Remember: the trade itself can be up to 45 days older than that.)
SIGNAL_LOOKBACK_DAYS = 7

# Only follow these transaction types. We follow buys, not sells.
FOLLOW_TRANSACTIONS = {"Purchase"}

# Optional: only follow these politicians (by name, lowercase substring match).
# Leave empty to follow ALL members of Congress.
FOLLOW_POLITICIANS: set[str] = set()
# Example: {"nancy pelosi", "tommy tuberville"}


# --- RISK CONTROLS (the important part) ---
# Dollar amount to buy per signal. Small + fixed = sane.
NOTIONAL_PER_TRADE = 100.0

# Never spend more than this total across one run of the pipeline.
MAX_DAILY_SPEND = 500.0

# Never hold more than this many distinct positions.
MAX_OPEN_POSITIONS = 20

# Never buy a name we already hold (avoid stacking into one ticker).
SKIP_IF_ALREADY_HELD = True

# Only submit orders while the market is open.
ONLY_TRADE_WHEN_MARKET_OPEN = True

# Master safety switch. True = log what WOULD happen, place NO orders at all.
# Start here. Set to False only once the output looks correct to you.
DRY_RUN = True


# --- Daemon settings (used by daemon.py) ---
# How often the daemon runs a full pass. Congress data only updates daily, so
# every few hours is plenty; more often just wastes API calls for no new data.
RUN_INTERVAL_HOURS = 6.0

# Only run a pass when the market is open (skip nights/weekends entirely).
# The daemon still wakes on its interval but does nothing while closed.
DAEMON_ONLY_WHEN_MARKET_OPEN = True

# Where to persist "already acted on" signals and logs. Defaults to next to
# this file; in Docker we set DATA_DIR=/app/data (a mounted volume) so they
# survive container restarts.
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "daemon.log")


def validate_data_dir() -> None:
    """Ensure the data directory exists. No API keys required — used by the
    dummy seeder and the dashboard, which run fully offline."""
    os.makedirs(DATA_DIR, exist_ok=True)


def validate() -> None:
    """Fail fast with a clear message if keys are missing."""
    missing = [
        name
        for name, val in {
            "QUIVER_API_KEY": QUIVER_API_KEY,
            "ALPACA_API_KEY": ALPACA_API_KEY,
            "ALPACA_SECRET_KEY": ALPACA_SECRET_KEY,
        }.items()
        if not val
    ]
    if missing:
        raise SystemExit(
            f"Missing required keys in .env: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill them in."
        )
