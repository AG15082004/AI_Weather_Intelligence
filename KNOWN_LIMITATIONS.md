# Known Limitations and Operational Considerations

**Project**: Tamil Nadu Weather Intelligence Platform  
**Document Version**: 1.0 (Phase 8.6 Release Readiness)  
**Last Updated**: November 12, 2026  

This document provides a transparent and technical breakdown of current platform limitations, infrastructure constraints, and operational design choices across the Tamil Nadu Weather Intelligence Platform.

---

## 1. Microsoft Fabric SQL Cloud Authentication (Deferred SP)

### Context & Current Status
- **Local Environment**: Fully operational. Python connects to Microsoft Fabric SQL Analytics Endpoint via `ODBC Driver 18 for SQL Server` using access tokens obtained through `AzureCliCredential` (`az login`). All 24 tables and Gold analytical queries execute cleanly.
- **Render Production Environment**: Direct Fabric SQL queries return HTTP 500 when executed from the Render container because `AzureCliCredential` requires interactive or local machine context. 
- **Deferred Capability**: Automated non-interactive authentication via Azure Entra ID Service Principal (`ActiveDirectoryServicePrincipal`) is **deferred** because registering an enterprise application in the target Azure tenant and granting Lakehouse workspace access requires Microsoft Entra ID Tenant Administrator privileges.

### Impact
- Live SQL queries from the deployed Render backend are non-functional until a registered Service Principal (`AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET`) is provisioned and injected.
- When running in self-hosted or local production mode with Azure CLI, all 5 Gold tables and analytical views function normally.

### Remediation Path
Refer to [PRODUCTION_DEPLOYMENT_GUIDE.md](file:///d:/TN_Weather_Api/PRODUCTION_DEPLOYMENT_GUIDE.md) Section 4 for instructions to activate Service Principal access once tenant administrator approval is secured.

---

## 2. Render Free Tier Hosting Characteristics

The platform is deployed under the Render Free Tier to maintain a **zero-additional-cost** hosting profile. This introduces specific hosting constraints:

### A. Ephemeral Container Sleep & Cold-Start Latency
- Render free-tier web services automatically spin down into a suspended state after 15 minutes of inactivity.
- The first inbound request to either the backend or frontend after spin-down incurs a **15 to 30 second cold-start penalty** while the container provisions.
- Subsequent requests once warm respond within **280 to 350 ms**.

### B. Memory Ceiling (512 MB RAM)
- The free container has a strict 512 MB memory limit.
- **Mitigation Implemented**: The backend memory cache ([cache.py](file:///d:/TN_Weather_Api/backend/app/utils/cache.py)) is explicitly bounded to `max_entries=500` with LRU/FIFO eviction (`popitem(last=False)`). Request body sizes are capped at 1 MB via security middleware to prevent memory exhaustion (OOM) crashes.

### C. Ephemeral Local Storage
- Free containers do not have persistent disk storage.
- Application logs are streamed directly to stdout/stderr using `structlog` for consumption via cloud log drivers rather than written to persistent local files.

---

## 3. AI Weather Intelligence Engine: Operational Modes

The AI Weather Agent features a hybrid architecture designed to balance intelligence depth with cloud hosting feasibility:

| Operational Mode | Host / Trigger | Provider | Latency | Capabilities |
| :--- | :--- | :--- | :---: | :--- |
| **Local Development** | Local Machine | **Ollama Qwen3:4b** | ~2–4 s | Conversational fluency, complex phrasing, context carryover, and ChartSpec generation. |
| **Cloud Production** | Render Cloud | **Deterministic Grounded Engine** | **~250–300 ms** | Strict numerical accuracy, ChartSpec generation, source provenance metadata, zero LLM hosting fees. |

### Operational Note
Ollama Qwen3:4b requires a local GPU or CPU inference server. Render's free tier does not provide GPUs or sufficient CPU power for local LLM inference. Therefore, on Render, `ai_service.py` automatically routes prompts to the verified deterministic response generator. This guarantees reliable responses without incurring paid third-party API costs (e.g. OpenAI or Anthropic tokens).

---

## 4. Meteorological Data Quality and Strict NULL Semantics

### Missing Historical Rainfall Data
- In raw meteorological datasets (such as historical periods from Open-Meteo or sparse regional rain gauges), certain district dates have no recorded precipitation data.
- **IMD Meteorological Standard**: A day without a rain gauge reading is **unrecorded (NULL)**, not **zero rainfall (0.0 mm)**. Reporting `0.0 mm` for an unmonitored day introduces false drought or dry-spell indicators.
- **Handling**: The backend strictly preserves `None` (SQL `NULL`) throughout the Python service layer, serialization schemas, and memory cache. Frontend charts render broken lines or missing-data badges rather than plotting artificial 0 mm data points.

---

## 5. Summary of Risk Matrix

| Risk Factor | Probability | Impact | Mitigation Status |
| :--- | :---: | :---: | :--- |
| Render Free Spindown | High | Low (Temporary latency) | Keep-alive heartbeat ping or upgrade to Starter tier. |
| Memory OOM on Backend | Low | Medium | Strict bounded cache (`max_entries=500`) + 1MB payload ceiling. |
| Fabric SP Delay | Medium | Medium | Local Azure CLI gateway operates with zero downtime. |
| LLM Token Exhaustion | None | None | 100% deterministic fallback; no paid token APIs used. |

