"""
SHIVA Status API — Reads live data from Upstash Redis (Railway bot source)
"""
import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "https://growing-crow-80382.upstash.io")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "gQAAAAAAATn-AAIncDJlNjdjM2M4OTQzOTg0OGRhYjE3MzRjNjNhM2U1ZDUzNnAyODAzODI")


def upstash_get(key):
    """Get a value from Upstash Redis via REST API."""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return None
    try:
        req = urllib.request.Request(
            f"{UPSTASH_URL}/get/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("result")
    except Exception:
        return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Read individual keys the Railway bot pushes
            positions_raw = upstash_get("shiva:positions")
            account_raw = upstash_get("shiva:account_info")
            lastrun_raw = upstash_get("shiva:last_run")

            positions = json.loads(positions_raw) if positions_raw else []
            account = json.loads(account_raw) if account_raw else {}
            lastrun = json.loads(lastrun_raw) if lastrun_raw else {}

            equity = account.get("equity", 0)
            balance = account.get("balance", 0)
            pnl = account.get("pnl", 0)

            result = {
                "equity": equity,
                "balance": balance,
                "pnl": pnl,
                "pnl_pct": round((pnl / balance * 100) if balance > 0 else 0, 2),
                "positions": len(positions) if isinstance(positions, list) else 0,
                "cycle": lastrun.get("cycle", 0),
                "timestamp": lastrun.get("time", ""),
                "status": "live"
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e),
                "equity": 0, "balance": 0, "pnl": 0,
                "positions": 0, "cycle": 0, "timestamp": ""
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass
