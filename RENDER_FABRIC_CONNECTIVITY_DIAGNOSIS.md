# RENDER FABRIC CONNECTIVITY & PRODUCTION CONFIGURATION DIAGNOSIS

**Project:** Tamil Nadu Weather Intelligence Platform  
**Target Environments:** Local Workstation (Windows 11 / Azure CLI) & Cloud Production (Render PaaS)  
**Date:** 2026-11-13  
**Status:** Resolved & Validated  

---

## 1. Executive Summary

Recent production deployment logs on Render revealed three critical operational signals:
1. **Missing ODBC Driver:** `Can't open lib 'ODBC Driver 18 for SQL Server': file not found`.
2. **Fabric Configuration Mismatch:** `auth_mode=interactive`, `server=""`.
3. **Graceful Degraded Mode:** `/api/overview` returned HTTP 200 via cached/degraded-mode handling, but log traces contained driver initialization failures.

This document details the root cause analysis, the architectural separation between local workstation and cloud production authentication, the containerization strategy to support live ODBC on Render, and configuration requirements for complete operational readiness.

---

## 2. Root Cause Analysis

### 2.1 Why `server=""` Was Logged
- **Code Inspection:** `app/config.py` defines `fabric_server: str = Field(default="", validation_alias=...)`.
- **Render Dashboard:** Render's Environment Variables tab did not have `FABRIC_SERVER` or `FABRIC_SQL_ENDPOINT` populated.
- **Git Security Policy:** `.env` files are correctly excluded via `.gitignore` to prevent credential exposure. Consequently, the cloud instance initialized with `fabric_server=""`.

### 2.2 Why `auth_mode=interactive` Was Logged
- **Default Fallback:** `app/config.py` previously declared `fabric_auth_mode: str = "interactive"`.
- In the absence of an explicit `FABRIC_AUTH_MODE` environment variable on Render, the system defaulted to `interactive`.
- **Cloud Incompatibility:** `interactive` (`ActiveDirectoryInteractive`) requires an interactive browser prompt or device code flow, which is fundamentally unsupported in a headless Linux cloud container, resulting in connection failure.

### 2.3 Why `Can't open lib 'ODBC Driver 18 for SQL Server'` Occurred
- **Render Native Python Runtime:** Render's standard native Python runtime uses standard Linux (Ubuntu/Debian) base images without Microsoft's proprietary ODBC drivers (`msodbcsql18`).
- When `pyodbc.connect()` was called with `DRIVER={ODBC Driver 18 for SQL Server}`, the operating system's `unixODBC` driver manager could not locate the shared library (`libmsodbcsql-18.so`), raising file-not-found error `01000`.

---

## 3. Architecture: Local vs. Cloud Authentication Separation

The connection layer (`backend/app/services/fabric_connection.py`) has been upgraded with automated environment detection and auth mode resolution:

```
                      +-----------------------------+
                      |    Startup / connect()      |
                      +-----------------------------+
                                     |
                                     v
                       Is RENDER or CLOUD_ENV set?
                                    / \
                            YES    /   \   NO
                                  /     \
                                 v       v
         +--------------------------+  +-------------------------------+
         |    Cloud Environment     |  |   Local Development Workstation|
         +--------------------------+  +-------------------------------+
                      |                                |
       Missing ODBC driver, empty                      v
       server, or missing Service         Default: "azure_cli"
       Principal credentials?             Uses local 'az account get-access-token'
                     / \                  Fallback: "interactive" / "sql_login"
             YES    /   \   NO
                   /     \
                  v       v
      +--------------+  +--------------------+
      |  "deferred"  |  | "service_principal"|
      +--------------+  +--------------------+
             |                    |
             v                    v
      Fail fast (0.05ms)     Token acquisition via
      No pyodbc call         Tenant / Client ID / Secret
      Zero log noise         Direct Lakehouse queries
      Serve cache/degraded
```

### Key Safety Guarantees:
1. **Zero Interactive Prompts in Cloud:** Under no circumstances will Render attempt interactive browser/device-code authentication.
2. **Instant Deferred Resolution:** If Service Principal credentials or the ODBC driver are missing in the cloud, `resolve_auth_mode()` returns `("deferred", "<safe_reason>")`.
3. **No Retries on Deferred Auth:** `connect()` raises `FabricConnectionError` immediately without calling `pyodbc.connect()`, eliminating driver lookup crashes and eliminating 30-second connection timeouts.
4. **Preserved Local Azure CLI:** Local development continues seamlessly using `azure_cli` authentication without requiring secrets in `.env`.
5. **Phase 9 Compliance Preserved:**
   - Degraded mode returns HTTP 200 with `source="cache"` when available.
   - If cache is empty, returns HTTP 200 with `source="unavailable"` and `status="DEGRADED"`.
   - Never crashes with HTTP 500.
   - Strictly preserves `NULL` semantics for unmeasured rainfall (no synthetic zero values).

---

## 4. Environment Variables Reference

To enable live Microsoft Fabric queries on Render, the following environment variables must be configured in the Render Dashboard (**Environment** tab):

| Variable Name | Required For Live Fabric | Description / Recommended Value |
|---|---|---|
| `FABRIC_SERVER` | Yes | Microsoft Fabric SQL Connection String (e.g. `xjee6istmh4ujox...datawarehouse.fabric.microsoft.com`) |
| `FABRIC_DATABASE` | Yes | Lakehouse Database Name (default: `lh_tn_weather_intelligence`) |
| `FABRIC_AUTH_MODE` | Optional (Auto) | Set to `service_principal` (automatically selected if credentials exist) |
| `FABRIC_TENANT_ID` | Yes (for live auth) | Azure Entra Tenant ID (UUID) |
| `FABRIC_CLIENT_ID` | Yes (for live auth) | Entra Service Principal App / Client ID (UUID) |
| `FABRIC_CLIENT_SECRET` | Yes (for live auth) | Entra Service Principal Client Secret |
| `OPENAI_API_KEY` | Recommended | OpenAI API Key for GPT-6 Luna AI conversational intelligence |
| `OPENAI_MODEL` | Optional | `gpt-6-luna` (default: `gpt-6-luna`) |
| `AI_PROVIDER` | Optional | `openai` (falls back to deterministic if key not present) |
| `ENVIRONMENT` | Yes | `production` |
| `RENDER` | Yes (Automatic) | Set to `true` by Render runtime |
| `CORS_ORIGINS` | Yes | `https://ai-weather-intelligence-1.onrender.com` |

> **Note:** If `FABRIC_CLIENT_ID` or `FABRIC_CLIENT_SECRET` is not yet provisioned due to pending tenant administrator approvals, the platform automatically runs in graceful **DEFERRED** mode.

---

## 5. Linux ODBC Driver 18 & Containerization Guide

Because Render native Python web services lack root access to install proprietary apt packages, a production-grade `Dockerfile` has been added to `backend/Dockerfile`.

### 5.1 Dockerfile Structure (`backend/Dockerfile`)
- **Base Image:** `python:3.11-slim-bookworm`
- **System Dependencies:** `curl`, `gnupg2`, `unixodbc`, `unixodbc-dev`
- **Microsoft ODBC Repository:**
  ```dockerfile
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
  curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list
  apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18
  ```
- **Application Startup:** Non-root user `appuser` (UID 10001), running `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### 5.2 Switching Render Backend to Docker Runtime (When Ready)
To enable live Fabric queries on Render:
1. In the **Render Dashboard**, navigate to the backend service (`ai-weather-intelligence`).
2. Go to **Settings** -> **Build & Deploy**.
3. Change **Environment** from `Python 3` to `Docker`.
4. Set **Dockerfile Path** to `backend/Dockerfile` and **Docker Context** to `backend`.
5. Enter the `FABRIC_SERVER`, `FABRIC_CLIENT_ID`, and `FABRIC_CLIENT_SECRET` in **Environment Variables**.
6. Trigger a deployment. Render will build the container with Microsoft ODBC Driver 18 installed.

---

## 6. Test & Validation Evidence

### 6.1 Dedicated Fabric Cloud Connectivity Tests (`test_fabric_render_connectivity.py`)
| Test Case | Scenario Verified | Result |
|---|---|---|
| `test_01_missing_fabric_server_configuration` | Empty server triggers clean deferred status without crash | PASS |
| `test_02_missing_odbc_driver` | Missing ODBC driver gracefully flagged as deferred with install instructions | PASS |
| `test_03_local_azure_cli_mode` | Local dev defaults to `azure_cli` and preserves az token flow | PASS |
| `test_04_render_without_service_principal` | Render without SP credentials safely defers without interactive auth | PASS |
| `test_05_render_with_complete_service_principal` | Render with complete SP credentials selects `service_principal` | PASS |
| `test_06_successful_sql_query` | Live Fabric query execution succeeds and populates weather metrics | PASS |
| `test_07_fabric_unavailable_and_cache_empty` | Deferred auth + empty cache returns HTTP 200 with UNAVAILABLE status | PASS |
| `test_08_fabric_unavailable_with_cached_data` | Deferred auth + cached data returns HTTP 200 with CACHE status | PASS |

```
Ran 8 tests in 0.128s
OK
```

### 6.2 Acceptance & Reliability Regression Suite
- Acceptance tests (`test_phase10_acceptance.py` + `test_phase9_data_reliability.py`):
  `Ran 36 tests in 20.087s. OK`
- Production CORS, AI engine, and preflight tests:
  `Ran 55 tests in 1.688s. OK`
- Frontend Build (`npm run build`):
  `✓ 3169 modules transformed. built in 724ms. 0 errors.`
