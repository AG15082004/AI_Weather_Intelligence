# RENDER PRODUCTION DEPLOYMENT & SYNCHRONIZATION GUIDE

**Project:** Tamil Nadu Weather Intelligence Platform  
**Target Services:**
* **Frontend:** `ai-weather-intelligence-1` (`https://ai-weather-intelligence-1.onrender.com`)
* **Backend:** `ai-weather-intelligence` (`https://ai-weather-intelligence.onrender.com`)

---

## 1. Why Render Is Failing & Out of Sync

Our live probes confirmed that the deployed Render backend is still running legacy commit `abef45a`, missing all updates from Phase 8.1 through Phase 10.1:
1. `GET /api/monitoring/operational-status` returned `404 Not Found`.
2. `OPTIONS /api/overview` returned `400 Bad Request: Disallowed CORS origin`.
3. `GET /api/overview` returned unhandled `500 Internal Server Error`.

**Once the latest code is deployed on Render, both the CORS error and the 500 error will be completely resolved.**

---

## 2. Deployment Instructions

### Step 1: Push Code to GitHub
Push the verified commits to the repository:
```powershell
git push origin main
git push origin dev
```

### Step 2: Configure Render Backend Environment Variables
In the **Render Dashboard -> ai-weather-intelligence -> Environment**, verify and configure:

| Key | Value | Purpose |
|---|---|---|
| `APP_ENV` | `production` | Enables production provider selection & security policies |
| `CORS_ORIGINS` | `https://ai-weather-intelligence-1.onrender.com,https://ai-weather-intelligence.onrender.com` | Allowed frontend origins |
| `CORS_ORIGIN_REGEX` | `^https://ai-weather-intelligence(-\w+)?\.onrender\.com$` | Matches Render preview and production domains |
| `AI_PROVIDER` | `openai` | Enables online GPT-6 Luna AI engine |
| `OPENAI_MODEL` | `gpt-6-luna` | Primary OpenAI model |
| `OPENAI_API_KEY` | `sk-proj-...` | Your active OpenAI API key |
| `OPENAI_TIMEOUT_SECONDS` | `30` | Timeout threshold |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1024` | Token cost guard |

### Step 3: Trigger Backend Manual Deploy on Render
1. Navigate to **Render Dashboard** -> Service `ai-weather-intelligence`.
2. Click **Manual Deploy** -> **Deploy latest commit** (or "Clear build cache & deploy").
3. Verify Build & Start commands:
   * **Root Directory:** `backend` (or repo root with command pointing to backend)
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 4: Verify Frontend Configuration on Render
1. Navigate to **Render Dashboard** -> Static Site `ai-weather-intelligence-1`.
2. Verify Environment Variables:
   * `VITE_API_BASE_URL` = `https://ai-weather-intelligence.onrender.com`
3. Click **Manual Deploy** -> **Deploy latest commit**.

---

## 3. Post-Deployment Verification Checklist

Run these curl commands after Render finishes deploying:

```powershell
# 1. Health check with detailed service status
curl -i https://ai-weather-intelligence.onrender.com/api/health

# 2. CORS OPTIONS preflight from frontend origin
curl -i -X OPTIONS -H "Origin: https://ai-weather-intelligence-1.onrender.com" -H "Access-Control-Request-Method: GET" https://ai-weather-intelligence.onrender.com/api/overview

# 3. Overview API request from frontend origin
curl -i -H "Origin: https://ai-weather-intelligence-1.onrender.com" "https://ai-weather-intelligence.onrender.com/api/overview?start_date=2026-11-06&end_date=2026-11-12"

# 4. Operational status
curl -i https://ai-weather-intelligence.onrender.com/api/monitoring/operational-status

# 5. AI Health status
curl -i https://ai-weather-intelligence.onrender.com/api/ai/health
```

Expected Outcome:
* Preflight returns HTTP 200 with `Access-Control-Allow-Origin: https://ai-weather-intelligence-1.onrender.com`.
* Overview returns HTTP 200 with JSON payload (`status: "unavailable"` when Fabric is offline without crashing).
* The dashboard displays graceful status badges without browser console errors.

