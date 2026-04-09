"""
SHIVA Config API — Vercel Serverless Function
GET: Returns stored config
POST: Updates config (admin panel)
"""
import json
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone


def get_kv():
    try:
        from kv import kv
        return kv
    except ImportError:
        return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        kv = get_kv()
        config = {
            "METAAPI_ACCOUNT_ID": "",
            "METAAPI_TOKEN": "[hidden]",
            "SHIVA_LOG_FILE": "~/logs/shiva_live.log",
        }

        if kv:
            stored = kv.get("shiva:config")
            if stored:
                config.update(stored)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(config).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            config = json.loads(body.decode())
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        kv = get_kv()
        if kv:
            existing = kv.get("shiva:config") or {}
            existing.update(config)
            kv.set("shiva:config", existing, ex=2592000)  # 30 day TTL

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass
