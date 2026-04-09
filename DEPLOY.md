# 🔱 SHIVA Admin — Vercel Deployment

## Architecture

```
[Your Mac]                          [Vercel]
┌──────────────────┐               ┌─────────────────────┐
│  SHIVA Bot       │               │  Static HTML        │
│  shiva_live_bot.js│               │  index.html         │
│                  │               │                     │
│  Sync Script     │───POST───────>│  API (Serverless)   │
│  shiva_vercel_   │   every 10s   │  /api/status        │
│  sync.py         │               │  /api/trades        │
│                  │               │  /api/log           │
│  Reads:          │               │                     │
│  ~/logs/shiva_   │               │  Vercel KV (Redis)  │
│  live.log        │               │  shiva:dashboard    │
│  ~/trade_history │               │  shiva:trades       │
└──────────────────┘               └─────────────────────┘
```

## Step 1: Deploy to Vercel

```bash
cd ~/shiva-vercel
vercel deploy --prod
```

Note the deployment URL (e.g., `https://shiva-admin-xxxx.vercel.app`)

## Step 2: Set Up Vercel KV (Required for Data Persistence)

Vercel serverless functions are stateless. We use Vercel KV (Redis) to persist data between requests.

1. Go to https://vercel.com/dashboard
2. Select your project → **Storage** → **Create Database** → **KV**
3. Copy the connection details
4. Add environment variables:
   ```bash
   vercel env add KV_REST_API_URL
   vercel env add KV_REST_API_TOKEN
   ```

## Step 3: Run Local Sync Script

The sync script reads your local log file and pushes data to Vercel every 10 seconds.

```bash
# Set your Vercel URL
export VERCEL_URL="https://your-deployment-url.vercel.app"

# Run sync
python3 ~/shiva_vercel_sync.py
```

The sync script will:
- Parse `~/logs/shiva_live.log` for the latest dashboard data
- POST it to `YOUR_VERCEL_URL/api/status`
- Push trade history every 5 cycles
- Push log tail every 30 seconds

## Step 4: Open Admin Panel

Visit your Vercel URL in a browser. The admin panel will fetch data from the API and display it.

---

## Alternative: No Vercel KV?

If you don't want to set up Vercel KV, use the **local admin panel** instead:

```bash
# Run local Flask admin (reads log file directly)
python3 ~/shiva_admin.py

# Open http://localhost:5000
```

The local admin panel doesn't need Vercel and reads the log file directly.

---

## Files

| File | Purpose |
|------|---------|
| `shiva-vercel/index.html` | Static admin panel hosted on Vercel |
| `shiva-vercel/api/status.py` | Serverless endpoint for dashboard data |
| `shiva-vercel/api/trades.py` | Serverless endpoint for trade history |
| `shiva-vercel/api/log.py` | Serverless endpoint for log tail |
| `shiva-vercel/api/config.py` | Serverless endpoint for configuration |
| `shiva-vercel/vercel.json` | Vercel project config |
| `shiva_vercel_sync.py` | Local sync script (runs on your Mac) |
| `shiva_admin.py` | Local Flask admin panel (alternative to Vercel) |
