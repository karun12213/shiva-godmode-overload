"""SHIVA Log API — Reads from Upstash Redis (Railway bot source)"""
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


def upstash_lrange(key, start=0, stop=-1):
    """Get a range from a Redis list."""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return []
    try:
        req = urllib.request.Request(
            f"{UPSTASH_URL}/lrange/{key}/{start}/{stop}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("result", [])
    except Exception:
        return []


LOG_KEY = "shiva:log"
BOT_LOGS_KEY = "shiva:bot_logs"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            log_data = ""

            # Try bot logs first (Redis list from Railway)
            bot_logs = upstash_lrange(BOT_LOGS_KEY, -100, -1)
            if bot_logs and isinstance(bot_logs, list):
                log_lines = []
                for entry in bot_logs:
                    if isinstance(entry, str):
                        try:
                            parsed = json.loads(entry)
                            log_lines.append(f"{parsed.get('timestamp', '')} {parsed.get('icon', '')} {parsed.get('message', '')}")
                        except json.JSONDecodeError:
                            log_lines.append(entry)
                    elif isinstance(entry, dict):
                        log_lines.append(f"{entry.get('timestamp', '')} {entry.get('icon', '')} {entry.get('message', '')}")
                log_data = "\n".join(log_lines)

            # Fallback to raw log key
            if not log_data:
                raw = upstash_get(LOG_KEY)
                log_data = json.loads(raw) if raw else ""

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"log": log_data}).encode())
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"log": "", "error": str(e)}).encode())

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

        log_content = data.get("log", "")[-50000:]

        if UPSTASH_URL and UPSTASH_TOKEN:
            try:
                payload = json.dumps({LOG_KEY: json.dumps(log_content), "EX": 86400}).encode()
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
        self.wfile.write(json.dumps({"status": "ok", "bytes": len(log_content)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass
