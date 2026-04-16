#!/usr/bin/env python3
"""
SHIVA Vercel Sync — Pushes log data from local Mac to Vercel-hosted API.
"""
import os, re, json, time, subprocess, logging
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    print("❌ requests required: pip3 install requests")
    exit(1)

# CONFIG
LOG_FILE = os.path.expanduser("~/logs/shiva_live.log")
TRADE_HISTORY_FILE = os.path.expanduser("~/trade_history.json")
VERCEL_URL = os.getenv("VERCEL_URL", "https://shiva-godmode-overlord-dday.vercel.app")
POLL_INTERVAL = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("shiva-sync")

class SHIVAParser:
    def parse_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except FileNotFoundError:
            return None
        blocks = content.split("🔱 SHIVA LIVE TRADING BOT")
        if len(blocks) < 2:
            return None
        last_block = blocks[-1]
        data = {"agents": []}
        
        def rx(pattern):
            m = re.search(pattern, last_block)
            return m
        
        m = rx(r"🕐\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})")
        if m: data["timestamp"] = m.group(1)
        
        m = rx(r"📊 Cycle:\s+#(\d+)\s*\|\s*Trades:\s*(\d+)\s*\|\s*W:(\d+)\s*L:(\d+)")
        if m:
            data["cycle"] = int(m.group(1))
            data["total_trades"] = int(m.group(2))
            data["wins"] = int(m.group(3))
            data["losses"] = int(m.group(4))
        
        m = rx(r"💰\s*EQUITY:\s*\$([\d,]+\.?\d*)\s*\|\s*Balance:\s*\$([\d,]+\.?\d*)")
        if m:
            data["equity"] = float(m.group(1).replace(",", ""))
            data["balance"] = float(m.group(2).replace(",", ""))
        
        m = rx(r"💵\s*PnL:\s*([+-]?)\$([\d,]+\.?\d*)\s*\(([-+]?[\d,]+\.?\d*)%\)")
        if m:
            sign = 1 if m.group(1) in ("+", "") else -1
            data["pnl"] = sign * float(m.group(2).replace(",", ""))
            data["pnl_pct"] = float(m.group(3).replace(",", ""))
        
        m = rx(r"💹\s*Price:\s*\$([\d,]+\.?\d*)\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*lots")
        if m:
            data["price"] = float(m.group(1).replace(",", ""))
            data["symbol"] = m.group(2)
            data["lot_size"] = float(m.group(3))
        
        m = rx(r"BUY:(\d+)\s*SELL:(\d+)\s*HOLD:(\d+)")
        if m:
            buy = int(m.group(1))
            sell = int(m.group(2))
            hold = int(m.group(3))
            data["buy_count"] = buy
            data["sell_count"] = sell
            data["hold_count"] = hold
            total = buy + sell
            if total > 0:
                buy_pct = round((buy / total) * 100)
                data["consensus"] = "BUY" if buy_pct > 50 else "SELL" if buy_pct < 50 else "HOLD"
                data["consensus_pct"] = max(buy_pct, 100 - buy_pct)
        
        for m in re.finditer(r"(?:✅\s*|  )\s*(\S+)\s+(\w+)\s+(BUY|SELL)", last_block):
            data["agents"].append({"emoji": m.group(1), "name": m.group(2), "signal": m.group(3)})
        
        m = rx(r"📋\s*(\d+)/(\d+)\s*positions full")
        if m:
            data["open_positions"] = int(m.group(1))
            data["max_positions"] = int(m.group(2))
        
        return data

class VercelSync:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.last_sync_hash = None

    def push_status(self, data):
        try:
            data_hash = hash(json.dumps(data, sort_keys=True))
            if data_hash == self.last_sync_hash:
                return True

            # Push to /api/status (accepts POST with dashboard data)
            resp = requests.post(f"{self.base_url}/api/status", json=data, timeout=10)
            if resp.status_code in (200, 204):
                self.last_sync_hash = data_hash
                return True
            else:
                log.warning(f"Status push failed: {resp.status_code} - {resp.text[:200]}")
                return False
        except Exception as e:
            log.error(f"Status push error: {e}")
            return False

    def push_trades(self, trades):
        try:
            resp = requests.post(f"{self.base_url}/api/trades", json=trades, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            log.error(f"Trade push error: {e}")
            return False

    def push_log(self, log_content):
        try:
            resp = requests.post(f"{self.base_url}/api/log", json={"log": log_content}, timeout=15)
            return resp.status_code in (200, 204)
        except Exception as e:
            log.error(f"Log push error: {e}")
            return False

def get_trade_history(limit=200):
    try:
        with open(TRADE_HISTORY_FILE, "r") as f:
            return json.load(f)[-limit:]
    except:
        return []

def get_log_tail(filepath, lines=500):
    try:
        result = subprocess.run(["tail", "-n", str(lines), filepath], capture_output=True, text=True)
        return result.stdout
    except:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            return "".join(all_lines[-lines:])
        except:
            return ""

def main():
    log.info("🔱 SHIVA → Vercel Sync starting...")
    log.info(f"📂 Log: {LOG_FILE}")
    log.info(f"🌐 Vercel: {VERCEL_URL}")
    log.info(f"⏱️  Interval: {POLL_INTERVAL}s")
    
    parser = SHIVAParser()
    sync = VercelSync(VERCEL_URL)
    time.sleep(2)
    
    last_log_push = 0
    push_count = 0
    
    while True:
        try:
            dashboard = parser.parse_file(LOG_FILE)
            if dashboard:
                sync.push_status(dashboard)
                push_count += 1
            
            if push_count % 5 == 0:
                trades = get_trade_history(200)
                sync.push_trades(trades)
            
            now = time.time()
            if now - last_log_push > 30:
                log_tail = get_log_tail(LOG_FILE, 500)
                if log_tail:
                    sync.push_log(log_tail)
                last_log_push = now
            
            log.info(f"✅ Synced (total: {push_count})")
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            log.error(f"Sync error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
