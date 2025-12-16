from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from typing import Dict
from fastapi.responses import HTMLResponse
from datetime import timezone
import time
import json
from pathlib import Path

app = FastAPI(title="Kolache Inventory")

START_TIME = time.time()

STORE = Path("inventory.json")
LAYOUT_PATH = Path("config/layout.json")

from datetime import datetime

def load_layout():
    """Load tray definitions (name, max, category) from config."""
    layout = json.loads(LAYOUT_PATH.read_text())
    return layout["trays"]

def load_inventory():
    """
    Returns inventory in a UI-friendly structure:
    - current count
    - max count
    - category
    - last updated timestamp
    """
    trays = load_layout()

    if STORE.exists():
        raw_counts = json.loads(STORE.read_text())
    else:
        raw_counts = {}

    items = {}

    for tray in trays:
        name = tray["name"]
        items[name] = {
            "current": int(raw_counts.get(name, 0)),
            "max": int(tray["max"]),
            "category": tray["category"]
        }

    return {
        "updated": datetime.utcnow().isoformat() + "Z",
        "items": items
    }

@app.get("/inventory")
def inventory():
    return load_inventory()

def load_raw_counts():
    if STORE.exists():
        return json.loads(STORE.read_text())
    return {}

def compute_summary():
    trays = load_layout()
    raw = load_raw_counts()

    total_trays = len(trays)
    sold_out = 0
    low = 0
    total_current = 0

    for t in trays:
        name = t["name"]
        cur = int(raw.get(name, 0))
        mx = int(t["max"])
        total_current += cur
        if cur <= 0:
            sold_out += 1
        elif cur <= max(1, (mx + 3) // 4):  # <= 25% (rounded up)
            low += 1

    return {
        "total_trays": total_trays,
        "total_current": total_current,
        "sold_out_trays": sold_out,
        "low_trays": low,
    }

@app.get("/health")
def health():
    # lightweight JSON health check (great for debugging / uptime monitoring)
    uptime_s = int(time.time() - START_TIME)
    return {
        "ok": True,
        "uptime_seconds": uptime_s,
        "inventory_file_exists": STORE.exists(),
        "layout_file_exists": LAYOUT_PATH.exists(),
        "summary": compute_summary(),
    }

@app.get("/status", response_class=HTMLResponse)
def status_page():
    h = health()
    summary = h["summary"]
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Kolache Status</title>
  <style>
    body {{ font-family: system-ui; background:#111; color:#fff; padding:20px; }}
    .card {{ background:#1a1f27; border:1px solid rgba(255,255,255,0.12); border-radius:14px; padding:16px; max-width:520px; }}
    .row {{ display:flex; justify-content:space-between; margin:8px 0; }}
    .ok {{ color:#7CFC98; font-weight:800; }}
    .warn {{ color:#FFD36E; font-weight:800; }}
    a {{ color:#9cf; }}
  </style>
</head>
<body>
  <h1>📟 System Status</h1>
  <div class="card">
    <div class="row"><span>Server</span><span class="ok">OK</span></div>
    <div class="row"><span>Uptime</span><span>{h["uptime_seconds"]}s</span></div>
    <div class="row"><span>layout.json</span><span>{"✅" if h["layout_file_exists"] else "❌"}</span></div>
    <div class="row"><span>inventory.json</span><span>{"✅" if h["inventory_file_exists"] else "❌"}</span></div>
    <hr style="border:0;border-top:1px solid rgba(255,255,255,0.12);margin:14px 0;">
    <div class="row"><span>Total trays</span><span>{summary["total_trays"]}</span></div>
    <div class="row"><span>Total remaining</span><span>{summary["total_current"]}</span></div>
    <div class="row"><span>Low trays</span><span class="warn">{summary["low_trays"]}</span></div>
    <div class="row"><span>Sold out trays</span><span class="warn">{summary["sold_out_trays"]}</span></div>
  </div>

  <p style="margin-top:16px;">
    <a href="/">Back to board</a> · <a href="/inventory">View inventory JSON</a> · <a href="/health">Health JSON</a>
  </p>
</body>
</html>
"""
    return html
# Serve the web page
app.mount("/", StaticFiles(directory="static", html=True), name="static")
