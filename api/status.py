"""
SHIVA Status API — Vercel Serverless Function
Uses in-memory storage (Lambda persists ~15 min between recycles).
Sync script pushes every 10s so data stays fresh.
"""
import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone

# In-memory store (persists across requests on same Lambda instance)
_store = {}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = _store.get("dashboard")

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if data:
            self.wfile.write(json.dumps(data).encode())
        else:
            self.wfile.write(json.dumps({
                "status": "no_data",
                "message": "No data pushed yet. Run the sync script on your Mac.",
                "setup": "VERCEL_URL=<url> python3 ~/shiva_vercel_sync.py"
            }).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        data["server_timestamp"] = datetime.now(timezone.utc).isoformat()
        _store["dashboard"] = data

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "timestamp": data["server_timestamp"]}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass
