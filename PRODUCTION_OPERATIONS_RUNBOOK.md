# Production Operations Runbook

**System:** Tamil Nadu Weather Intelligence Platform  
**Target Hosts:** Render Cloud (Free Tier) + Microsoft Fabric Lakehouse  
**Version:** 1.0.0 (Release Candidate)  

---

## 1. Routine Deployment & Release Procedures

### 1.1 Triggering a Manual Deployment on Render
Because Render Free tier may not automatically trigger new builds upon push:
1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Select the Backend Web Service: `ai-weather-intelligence`.
3. In the top-right corner, click **Manual Deploy** > **Clear build cache & deploy**.
4. Verify build logs show:
   - Python virtual environment created.
   - Dependencies installed from `requirements.txt`.
   - Uvicorn startup completed: `Application startup complete.`
5. Select the Frontend Static Site: `ai-weather-intelligence-1`.
6. Click **Manual Deploy** > **Clear build cache & deploy**.
7. Verify build logs show `✓ built in ~1-2s` and dist assets deployed.

### 1.2 Configuring the Static Site SPA Rewrite Rule
To enable direct URL navigation (preventing 404s on `/temperature`, `/ai-assistant`, etc.):
1. In Render Dashboard, open `ai-weather-intelligence-1`.
2. Navigate to **Redirects/Rewrites** in the left sidebar.
3. Click **Add Rule**.
4. Fill in:
   - **Type:** `Rewrite`
   - **Source:** `/*`
   - **Destination:** `/index.html`
5. Click **Save Changes**.

---

## 2. Environment Variables Configuration Reference

### 2.1 Backend Environment Variables (`ai-weather-intelligence`)

| Variable Name | Production Value | Description |
|:---|:---|:---|
| `APP_ENV` | `production` | Enforces production mode, security headers, and skips localhost Ollama checks |
| `API_V1_PREFIX` | `/api` | Root prefix for API routes |
| `CORS_ORIGINS` | `https://ai-weather-intelligence-1.onrender.com` | Production CORS allowed origins |
| `FABRIC_SERVER` | `xjee6istmh4ujox...database.windows.net` | Microsoft Fabric SQL endpoint |
| `FABRIC_DATABASE` | `lh_tn_weather_intelligence` | Target Lakehouse database |
| `FABRIC_AUTH_MODE` | `service_principal` | Cloud authentication mode |
| `AZURE_CLIENT_ID` | `[Configured SP Client ID]` | Entra Service Principal App ID |
| `AZURE_CLIENT_SECRET` | `[Configured SP Secret]` | Entra Service Principal Secret |
| `AZURE_TENANT_ID` | `[Configured Tenant ID]` | Entra Tenant ID |
| `AI_PROVIDER` | `auto` | Automatically uses deterministic fallback in cloud |
| `AI_RATE_LIMIT_PER_MINUTE` | `30` | In-memory sliding window rate limit |

### 2.2 Frontend Environment Variables (`ai-weather-intelligence-1`)

| Variable Name | Value | Description |
|:---|:---|:---|
| `VITE_API_BASE_URL` | `https://ai-weather-intelligence.onrender.com` | Base URL of the deployed FastAPI backend |

---

## 3. Microsoft Fabric Service Principal Activation Guide

When Microsoft Entra ID tenant administrator consent is granted:
1. Register an Application in Entra ID (Azure AD).
2. Create a Client Secret and note the `Client ID`, `Secret`, and `Tenant ID`.
3. In Microsoft Fabric Lakehouse (`lh_tn_weather_intelligence`):
   - Open Lakehouse Settings > Manage Permissions.
   - Add the Service Principal with **Read** and **Execute** permissions on the Lakehouse SQL endpoint.
4. Set the environment variables in Render Dashboard under `ai-weather-intelligence` > **Environment**:
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `AZURE_TENANT_ID`
5. Redeploy backend service.
6. Check `GET /api/monitoring/operational-status` to verify `fabric_auth_state: "service_principal"` and `overall_status: "LIVE"`.

---

## 4. Incident Response & Troubleshooting

### Scenario A: Backend Returns 500 or Times Out
- **Symptom:** UI displays error state or request times out after 30 seconds.
- **Cause:** Render free tier instance is spinning up from idle sleep (cold start).
- **Resolution:** Render instances wake automatically after 30–45 seconds. Wait 45 seconds and refresh.

### Scenario B: Data Shows as "UNAVAILABLE" or "Data Offline"
- **Symptom:** KPIs show `Data Offline` or `N/A`, and Data Reliability badge is Red.
- **Cause:** Microsoft Fabric SQL endpoint is unreachable or tenant SP authorization is deferred.
- **Resolution:** This is intentional Degraded Mode behavior. The system protects users from false numbers. Use local environment with `az login` for full Fabric access, or toggle the "Preview Sample TN Data" banner on the frontend.

### Scenario C: Frontend Route Returns 404 on Page Refresh
- **Symptom:** Navigating directly to `/ai-assistant` returns `404 Not Found`.
- **Cause:** Missing SPA rewrite rule on Render static site.
- **Resolution:** Follow Section 1.2 above to add `/* -> /index.html` rewrite rule.
