# Congress-Follow Trader

A starter Python pipeline that follows U.S. congressional stock disclosures and
auto-executes trades on an **Alpaca paper account**:

```
Quiver (signal)  ->  strategy rules (decision)  ->  Alpaca (execution)
```

It is **safe by default**: paper account + dry-run mode (prints what it would do,
places no orders) until you deliberately turn that off.

## Files
| File | Role |
|------|------|
| `config.py` | All settings + **risk controls**. Read this first. |
| `quiver_client.py` | Pulls recent congressional trades from Quiver. |
| `strategy.py` | Rules that turn disclosures into buy signals. |
| `broker.py` | Alpaca execution, wrapped in hard risk checks. |
| `main.py` | Runs one full pass of the pipeline. |
| `daemon.py` | Runs the pipeline continuously on an interval (the service). |
| `state.py` | Remembers acted-on disclosures so the daemon never double-buys. |
| `portfolio.py` | Trade ledger + P&L math; writes `transactions.log`. |
| `pricing.py` | Current-price provider (simulated offline; live-quote ready). |
| `dashboard.py` | Local web dashboard at http://localhost:5000. |
| `seed_dummy.py` | Generates dummy data so you can see it all with no API keys. |

## Setup
1. **Install Python 3.10+**, then install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. **Get API keys:**
   - Quiver (Hobbyist tier is enough): https://api.quiverquant.com/pricing/
   - Alpaca **paper** keys: https://alpaca.markets/  (dashboard → API keys)
3. **Configure:** copy `.env.example` to `.env` and fill in your keys.
   Keep `ALPACA_PAPER=true`.

## See it immediately with dummy data (no API keys needed)
```
pip install -r requirements.txt
python seed_dummy.py      # create fake trades, prices, equity history
python dashboard.py       # open http://localhost:5000
```
The dashboard shows: net P&L ($ and %), a portfolio-value-over-time graph,
every stock you hold with its % up/down, and the full transaction log.

## Run the real pipeline
```
python quiver_client.py   # sanity-check the data feed alone (needs keys)
python main.py            # ONE pass of the pipeline (dry run by default)
python daemon.py          # run CONTINUOUSLY on an interval (Ctrl+C to stop)
```
Run `daemon.py` and `dashboard.py` together (two terminals, or Docker) to watch
trades show up live. The daemon records every (simulated or real) order to the
ledger, so the dashboard fills in on its own.

`daemon.py` runs forever: it wakes every `RUN_INTERVAL_HOURS`, skips passes
while the market is closed, logs to `daemon.log`, recovers from errors, and
remembers acted-on disclosures in `state.json` so it never double-buys.

## Going from "simulated" to "really placing paper orders"
1. Run `python main.py` and confirm the signals + "[DRY RUN] would BUY ..."
   lines look correct.
2. In `config.py`, set `DRY_RUN = False`. It will now place **paper** orders.
3. Check them in your Alpaca paper dashboard.

## ⚠️ Before ever using real money
- Set `ALPACA_PAPER=false` only after **weeks** of paper testing.
- Re-read every value in `config.py` — especially `NOTIONAL_PER_TRADE`,
  `MAX_DAILY_SPEND`, and `MAX_OPEN_POSITIONS`.
- Understand the limits of the signal:
  - Congressional disclosures lag the actual trade by **up to 45 days**.
  - Reported amounts are **ranges**, never exact — all returns are estimates.
- Trading **your own** account is fine. Auto-trading **other people's** money is
  regulated — don't ship that to other users without legal/registration advice.
- This is educational software, not investment advice.

## Keeping it running 24/7
Congress data only updates daily, so `RUN_INTERVAL_HOURS = 6` is plenty. Pick
**one** of these ways to keep the daemon alive:

### Option A — Windows Service via NSSM (recommended: auto-starts on boot, restarts on crash)
1. Download NSSM from https://nssm.cc/ and unzip `nssm.exe`.
2. In an **admin** terminal:
   ```
   nssm install CongressTrader
   ```
   In the dialog:
   - **Path:**      `C:\Path\to\python.exe`   (run `where python` to find it)
   - **Arguments:** `C:\Users\domin\congress-trader\daemon.py`
   - **Startup dir:** `C:\Users\domin\congress-trader`
3. Start it:  `nssm start CongressTrader`   (stop/remove: `nssm stop` / `nssm remove`)
   It now runs in the background and restarts automatically.

### Option B — Task Scheduler (no extra download)
Create a Basic Task → Trigger: **At startup** → Action: Start a program:
- **Program:** `pythonw.exe`  (the windowless Python; `where pythonw`)
- **Arguments:** `C:\Users\domin\congress-trader\daemon.py`
- **Start in:** `C:\Users\domin\congress-trader`

In the task's properties, tick "Run whether user is logged on or not" and, on
the Settings tab, "If the task fails, restart every 1 minute."

### Option C — just a terminal (simplest, for testing)
```
python daemon.py        # stays in the foreground; closing the window stops it
```
On Mac/Linux you can background it: `nohup python daemon.py &`.

### Watch what it's doing
```
type daemon.log          # Windows
tail -f daemon.log       # Mac/Linux
```

## Option D — Docker (clean, portable, auto-restarts)
Runs the daemon in a container with no Python setup on your machine.

**You must install Docker first** — on Windows that's **Docker Desktop**
(https://www.docker.com/products/docker-desktop/, free for personal use).
Install it, reboot, and make sure it's running (whale icon in the tray).

Then, from this folder (with your `.env` filled in):
```
docker compose up -d --build      # builds image, starts daemon + dashboard
docker compose logs -f            # watch the logs
docker compose down               # stop and remove the containers
```
This starts **two** containers: the daemon and the dashboard (at
http://localhost:5000). To populate dummy data inside the container first:
```
docker compose run --rm dashboard python seed_dummy.py
```
- `restart: unless-stopped` makes it come back automatically after a crash or
  reboot (as long as Docker Desktop is set to start on login).
- `state.json` and `daemon.log` persist in the `./data` folder on your PC, so
  rebuilding the image never loses your dedupe history.

Note: the container still only runs while your PC (and Docker) is on. For true
always-on, run this same image on a small cloud VM.
