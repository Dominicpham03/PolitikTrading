"""
Local web dashboard.  Run:  python dashboard.py
Then open:  http://localhost:5000

Shows net P&L, a portfolio-value graph over time, every stock you're invested
in with its % up/down, and the transaction log.
"""
from __future__ import annotations

from flask import Flask, jsonify, Response

import portfolio

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Congress Trader — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root { --bg:#0e1117; --card:#171c26; --line:#222a38; --txt:#e6edf3;
          --muted:#8b97a7; --green:#26a269; --red:#e0245e; --accent:#4c8dff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font-family:system-ui,Segoe UI,Roboto,sans-serif; }
  header { padding:20px 28px; border-bottom:1px solid var(--line);
           display:flex; align-items:center; justify-content:space-between; }
  h1 { font-size:18px; margin:0; }
  .muted { color:var(--muted); font-size:13px; }
  .wrap { padding:24px 28px; max-width:1100px; margin:0 auto; }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:16px 18px; }
  .card .label { color:var(--muted); font-size:12px; text-transform:uppercase;
                 letter-spacing:.04em; }
  .card .value { font-size:24px; font-weight:600; margin-top:6px; }
  .green { color:var(--green); } .red { color:var(--red); }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:18px; margin-top:20px; }
  .panel h2 { font-size:14px; margin:0 0 14px; color:var(--muted);
              text-transform:uppercase; letter-spacing:.04em; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th,td { text-align:right; padding:9px 10px; border-bottom:1px solid var(--line); }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:500; font-size:12px; }
  .pill { padding:2px 8px; border-radius:20px; font-size:12px; font-weight:600; }
  .pill.up { background:rgba(38,162,105,.15); color:var(--green); }
  .pill.down { background:rgba(224,36,94,.15); color:var(--red); }
  .log { font-family:ui-monospace,Consolas,monospace; font-size:12.5px;
         white-space:pre-wrap; color:#cbd5e1; max-height:300px; overflow:auto; }
  .sim { color:var(--accent); }
</style>
</head>
<body>
<header>
  <h1>📈 Congress Trader <span class="muted">— local dashboard</span></h1>
  <span class="muted" id="updated"></span>
</header>
<div class="wrap">
  <div class="cards">
    <div class="card"><div class="label">Invested</div><div class="value" id="invested">—</div></div>
    <div class="card"><div class="label">Current value</div><div class="value" id="value">—</div></div>
    <div class="card"><div class="label">Net P&L</div><div class="value" id="pnl">—</div></div>
    <div class="card"><div class="label">Net %</div><div class="value" id="pct">—</div></div>
  </div>

  <div class="panel">
    <h2>Portfolio value over time</h2>
    <canvas id="chart" height="90"></canvas>
  </div>

  <div class="panel">
    <h2>Holdings</h2>
    <table id="holdings">
      <thead><tr>
        <th>Ticker</th><th>Shares</th><th>Avg cost</th><th>Price</th>
        <th>Cost</th><th>Value</th><th>P&L</th><th>% up/down</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="panel">
    <h2>Transaction log</h2>
    <div class="log" id="log">loading…</div>
  </div>
</div>

<script>
const money = n => (n<0?"-$":"$") + Math.abs(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const cls = n => n>=0 ? "green" : "red";
let chart;

async function load() {
  const [s, hist, trades] = await Promise.all([
    fetch('/api/summary').then(r=>r.json()),
    fetch('/api/history').then(r=>r.json()),
    fetch('/api/trades').then(r=>r.json()),
  ]);

  // cards
  document.getElementById('invested').textContent = money(s.total_cost);
  document.getElementById('value').textContent = money(s.total_value);
  const pnlEl = document.getElementById('pnl');
  pnlEl.textContent = money(s.net_pnl); pnlEl.className = "value " + cls(s.net_pnl);
  const pctEl = document.getElementById('pct');
  pctEl.textContent = (s.net_pct>=0?"+":"") + s.net_pct + "%"; pctEl.className = "value " + cls(s.net_pct);
  document.getElementById('updated').textContent = "updated " + new Date().toLocaleTimeString();

  // holdings table
  const tb = document.querySelector('#holdings tbody');
  tb.innerHTML = s.rows.map(r => `
    <tr>
      <td><b>${r.ticker}</b></td>
      <td>${r.shares}</td><td>${money(r.avg_cost)}</td><td>${money(r.price)}</td>
      <td>${money(r.cost)}</td><td>${money(r.value)}</td>
      <td class="${cls(r.pnl)}">${money(r.pnl)}</td>
      <td><span class="pill ${r.pct>=0?'up':'down'}">${r.pct>=0?'▲':'▼'} ${Math.abs(r.pct)}%</span></td>
    </tr>`).join('') || `<tr><td colspan="8" class="muted">No positions yet. Run seed_dummy.py or the daemon.</td></tr>`;

  // chart
  const labels = hist.map(h => new Date(h.timestamp*1000).toLocaleDateString());
  const values = hist.map(h => h.value);
  const costs  = hist.map(h => h.cost);
  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('chart'), {
    type:'line',
    data:{ labels, datasets:[
      { label:'Value', data:values, borderColor:'#4c8dff', backgroundColor:'rgba(76,141,255,.12)', fill:true, tension:.25, pointRadius:0 },
      { label:'Invested', data:costs, borderColor:'#8b97a7', borderDash:[5,5], fill:false, tension:.25, pointRadius:0 },
    ]},
    options:{ plugins:{legend:{labels:{color:'#8b97a7'}}},
      scales:{ x:{ticks:{color:'#8b97a7'},grid:{color:'#222a38'}},
               y:{ticks:{color:'#8b97a7'},grid:{color:'#222a38'}} } }
  });

  // transaction log
  document.getElementById('log').innerHTML = trades.map(t => {
    const d = new Date(t.timestamp*1000).toLocaleString();
    const tag = t.simulated ? '<span class="sim">SIM </span>' : 'LIVE';
    return `${d}  ${tag} ${t.side} ${t.shares} ${t.ticker} @ ${money(t.price)} = ${money(t.notional)}  <span class="muted">${t.reason||''}</span>`;
  }).join('\\n') || 'No transactions yet.';
}

load();
setInterval(load, 15000);  // auto-refresh every 15s
</script>
</body>
</html>"""


@app.route("/")
def index() -> Response:
    return Response(PAGE, mimetype="text/html")


@app.route("/api/summary")
def api_summary():
    return jsonify(portfolio.summary())


@app.route("/api/history")
def api_history():
    return jsonify(portfolio.equity_history())


@app.route("/api/trades")
def api_trades():
    return jsonify(sorted(portfolio.trades(),
                          key=lambda t: t["timestamp"], reverse=True))


if __name__ == "__main__":
    print("Dashboard running at http://localhost:5000  (Ctrl+C to stop)")
    app.run(host="0.0.0.0", port=5000, debug=False)
