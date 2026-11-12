# Production Deployment Guide – Tamil Nadu Weather Intelligence Platform

This guide documents the procedures for deploying, configuring, and operating the Tamil Nadu Weather Intelligence Platform on cloud hosting platforms (such as Render) and local staging environments.

---

## 1. Architecture and Component Overview

The application is deployed as two distinct decoupled web services:
1. **Frontend Service**: Single-Page Application (SPA) built with React 19, TypeScript, and Vite, served as static assets.
2. **Backend Service**: Asynchronous REST API powered by FastAPI, Uvicorn, and Python 3.11 with ODBC Driver 18 for SQL Server.

---

## 2. Environment Variables Reference

### 2.1 Backend Environment Variables

| Variable Name | Required? | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | Runtime mode: `production` or `development`. |
| `CORS_ORIGINS` | Yes | `https://ai-weather-intelligence-1.onrender.com,http://localhost:5173` | Comma-separated allowlist of allowed web origins. |
| `AZURE_SQL_SERVER` | Yes | `xjee...datawarehouse.fabric.microsoft.com` | Microsoft Fabric SQL Analytics Endpoint hostname. |
| `AZURE_SQL_DATABASE` | Yes | `lh_tn_weather_intelligence` | Microsoft Fabric Lakehouse database name. |
| `FABRIC_AUTH_MODE` | Yes | `azure_cli` (Local) / `service_principal` (Cloud) | Authentication strategy (`azure_cli`, `service_principal`, `interactive`). |
| `AZURE_TENANT_ID` | Conditional | *(Azure Entra ID Directory ID)* | Required when `FABRIC_AUTH_MODE=service_principal`. |
| `AZURE_CLIENT_ID` | Conditional | *(Application / Client ID)* | Required when `FABRIC_AUTH_MODE=service_principal`. |
| `AZURE_CLIENT_SECRET` | Conditional | *(Client Secret Value)* | Required when `FABRIC_AUTH_MODE=service_principal`. |
| `ADMIN_API_KEY` | Optional | *(Secure random token)* | Protects administrative endpoints (e.g. `/api/monitoring/cache/clear`). |
| `AI_PROVIDER` | No | `auto` | `auto` (Ollama if reachable, else deterministic), `ollama`, or `deterministic`. |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Endpoint for Ollama LLM if running on a remote cloud GPU. |
| `OLLAMA_MODEL` | No | `qwen3:4b` | Default Ollama model name. |
| `CACHE_MAX_ENTRIES`| No | `500` | Maximum entries in thread-safe memory cache. |

### 2.2 Frontend Environment Variables

| Variable Name | Required? | Example Value | Description |
| :--- | :---: | :--- | :--- |
| `VITE_API_BASE_URL` | Yes | `https://ai-weather-intelligence.onrender.com` | Base URL of the deployed FastAPI backend (omit trailing slash). |

---

## 3. Render Deployment Step-by-Step

### 3.1 Deploying the Backend Web Service on Render

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository: `AG15082004/AI_Weather_Intelligence`.
4. Configure service parameters:
   - **Name**: `ai-weather-intelligence`
   - **Region**: Choose region closest to users (e.g. Singapore or Frankfurt).
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: `Free` (or `Starter` for non-sleeping workloads).
5. In the **Environment Variables** tab, add:
   - `ENVIRONMENT`: `production`
   - `CORS_ORIGINS`: `https://ai-weather-intelligence-1.onrender.com,http://localhost:5173`
   - `AZURE_SQL_SERVER`: `<your-fabric-sql-endpoint>`
   - `AZURE_SQL_DATABASE`: `lh_tn_weather_intelligence`
   - `FABRIC_AUTH_MODE`: `service_principal` (when credentials available)
   - `ADMIN_API_KEY`: `<generate-a-uuid-or-secret>`
   - `AI_PROVIDER`: `auto`
6. Click **Create Web Service**.

### 3.2 Deploying the Frontend Static Site on Render

1. Click **New +** $\rightarrow$ **Static Site**.
2. Connect the same repository: `AG15082004/AI_Weather_Intelligence`.
3. Configure static site parameters:
   - **Name**: `ai-weather-intelligence-1`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**:
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory**: `dist`
4. In the **Environment Variables** tab, add:
   - `VITE_API_BASE_URL`: `https://ai-weather-intelligence.onrender.com`
5. In **Redirects / Rewrites**, add a rewrite rule for client-side routing:
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - **Action**: `Rewrite`
6. Click **Create Static Site**.

---

## 4. Enabling Microsoft Fabric Service Principal Authentication

To connect the deployed cloud backend to Microsoft Fabric SQL Analytics Endpoints without manual user login, perform the following Azure Entra ID configuration:

### Step 1: Azure App Registration
1. In the [Azure Portal](https://portal.azure.com), navigate to **Microsoft Entra ID** $\rightarrow$ **App registrations** $\rightarrow$ **New registration**.
2. Name the app: `tn-weather-intelligence-service`.
3. Select single-tenant account type and click **Register**.
4. Note down the **Application (client) ID** and **Directory (tenant) ID**.

### Step 2: Generate Client Secret
1. In the registered application, navigate to **Certificates & secrets** $\rightarrow$ **New client secret**.
2. Set description (e.g. `Render Backend Secret`) and expiration duration.
3. Immediately copy the secret **Value** (it will be masked permanently after leaving the screen).

### Step 3: Enable Fabric Service Principal Tenant Switch
*(Requires Fabric / Power BI Tenant Administrator)*
1. Open the [Microsoft Fabric Admin Portal](https://app.fabric.microsoft.com).
2. Go to **Tenant settings** $\rightarrow$ **Developer settings**.
3. Enable:
   - **Service principals can use Fabric APIs**
   - **Service principals can access Lakehouse SQL endpoints**
4. Add the security group containing your registered app.

### Step 4: Grant Lakehouse Permissions
1. Navigate to the `lh_tn_weather_intelligence` workspace in Fabric.
2. Click **Manage access** $\rightarrow$ **Add people or groups**.
3. Enter the Application Name or Client ID.
4. Assign the role **Viewer** or **Contributor** (or execute `GRANT SELECT ON SCHEMA::dbo TO [app-name]` in SQL).

### Step 5: Configure Render Backend
Update Render Backend environment variables:
```bash
FABRIC_AUTH_MODE=service_principal
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
```
Redeploy the backend service.

---

## 5. Post-Deployment Verification Checklist

Execute the following checks after any deployment:

- [ ] **Heartbeat Check**:
  ```bash
  curl -s https://ai-weather-intelligence.onrender.com/api/health
  # Expected: {"status":"healthy", ...}
  ```
- [ ] **AI Health Check**:
  ```bash
  curl -s https://ai-weather-intelligence.onrender.com/api/ai/health
  # Expected: {"status":"healthy", "service":"AI Weather Intelligence Agent", ...}
  ```
- [ ] **Frontend Loading**: Open `https://ai-weather-intelligence-1.onrender.com` in a browser. Ensure dashboard cards render without blank screens.
- [ ] **CORS Verification**: Inspect browser developer console network requests to ensure preflight `OPTIONS` requests receive HTTP 200 with `Access-Control-Allow-Origin`.
- [ ] **AI Chat Test**: Send a query on `/ai-assistant` (e.g., "What is the weather in Chennai?"). Ensure a grounded response with source metadata is returned.
- [ ] **Security Verification**: Attempt to POST `/api/monitoring/cache/clear` without an API key. Verify it responds with HTTP 401 Unauthorized.

