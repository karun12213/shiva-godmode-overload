"""SHIVA Trades API — Reads from Upstash Redis (Railway bot source)"""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")


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


TRADES_KEY = "shiva:trades"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            trades_raw = upstash_get(TRADES_KEY)
            trades = json.loads(trades_raw) if trades_raw else []

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(trades).encode())
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps([]).encode())

    def do_POST(self):
        """Accept trade data from bot and store in Upstash."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            trades = json.loads(body.decode())
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        if UPSTASH_URL and UPSTASH_TOKEN:
            try:
                payload = json.dumps({TRADES_KEY: json.dumps(trades[-200:]), "EX": 86400}).encode()
                req = urllib.request.Request(
                    f"{UPSTASH_URL}/set",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {UPSTASH_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5):
                    pass
            except Exception:
                pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "count": len(trades)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass
