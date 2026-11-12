# Data Reliability Architecture

**Project:** Tamil Nadu Weather Intelligence Platform  
**Architecture Component:** Data Reliability, Cache Degradation, and Freshness Monitoring  
**Target Database:** `lh_tn_weather_intelligence` (Microsoft Fabric Lakehouse)  

---

## 1. Architectural Overview

The Data Reliability subsystem provides end-to-end transparency, fault tolerance, and provenance attribution across all layers of the application stack:

```
[ React Dashboard / Frontend Client ]
                  │
                  ▼
         [ FastAPI Endpoints ]
                  │
                  ▼
       [ WeatherService Layer ]
         │               │
         │ (Hit)         │ (Miss / Timeout)
         ▼               ▼
   [ TTLCache ]   [ Fabric SQL Executor ]
   - (Value,      - pyodbc + Azure CLI / SP
      Expiry,     - Connection Pooling
      Created_at) - Semantic Error Handling
         │               │
         │ (Fallback)    │ (Success / Failure)
         ◄───────────────┴───────────────► [ DataReliabilityService ]
                                           - Independent 5-Table Tracking
                                           - State Management: LIVE / CACHED / UNAVAILABLE
                                           - Asia/Kolkata IST Time formatting
```

---

## 2. The 4-State Data Status Model

Every response delivered by the backend is classified into exactly one of four operational states:

| Status | Indicator | Description | Cache Behavior |
|:---|:---|:---|:---|
| **`LIVE`** | Green | Direct, verified query execution against Microsoft Fabric SQL endpoint within latency tolerances. | Stored in cache with fresh TTL and creation timestamp. |
| **`CACHED`** | Amber | Data retrieved from in-memory cache. If query fails and cache has expired, served as stale cache with `is_stale=True`. | Age calculated dynamically from cache creation timestamp. |
| **`FALLBACK`** | Neutral | Algorithmic, baseline, or simulated data explicitly marked as non-production sample. | Bypasses Fabric Lakehouse. |
| **`UNAVAILABLE`** | Red | Fabric is unreachable and no cache exists in memory. HTTP 200 returned with clean empty payload, never HTTP 500. | KPIs render "Data Offline" or "N/A" instead of misleading 0. |

---

## 3. Data Query Lifecycle & Fallback Flowchart

```
                 Incoming Weather Request
                           │
                           ▼
                 Is fresh Cache valid?
                     /          \
              Yes  /              \ No
                 /                  \
        Return [CACHED]      Execute Fabric SQL Query
                             /                      \
                     Success/                        \ Failure / Timeout
                           /                          \
              Record Success in DR                    Record Failure in DR
              Update Cache with (Val, Exp, CreatedAt)  Check for Stale Cache in memory
              Return [LIVE] Data                      /                      \
                                              Found /                          \ None
                                                   /                            \
                                          Return [CACHED]               Return [UNAVAILABLE]
                                          with is_stale=True            with clean payload
                                          & Amber Banner                & Red Alert Notice
```

---

## 4. Microsoft Fabric Authentication Segregation

To maintain operational integrity across deployment tiers without security bypasses:

1. **Local Development Environment (`APP_ENV=development`):**
   - Authenticates against Microsoft Fabric Lakehouse using local Azure CLI tokens (`az login`).
   - Nominal mode: queries execute directly against Fabric Lakehouse Gold tables.
   - Live query duration averages 90–120 ms.

2. **Cloud Production Deployment on Render (`APP_ENV=production`):**
   - Microsoft Fabric Entra ID Service Principal authentication is deferred pending tenant administrator authorization.
   - The platform gracefully transitions to **Degraded Mode**:
     - Serves in-memory cached observations where available.
     - Returns transparent `UNAVAILABLE` status without crashing when cache is empty.
     - Never pretends cached or synthetic data is live Fabric data.
     - Automatically resumes `LIVE` queries as soon as Fabric connectivity is restored.

---

## 5. Zero-Fabrication & Zero-Hallucination Guarantees

1. **No Silent Numeric Conversions:** Missing rainfall or temperature data in Fabric Lakehouse (`NULL`) is preserved as `None` in Python, `null` in JSON, and `"N/A"` or `"Data Offline"` on the frontend. It is never replaced with `0.0`.
2. **AI Intent Grounding:** The AI assistant strictly inspects the `data_status` of the retrieved data. When data is cached or unavailable, it includes an unambiguous provenance footnote.
3. **Thread Safety:** `DataReliabilityService` uses threading locks (`threading.Lock`) to ensure safe state transitions under concurrent async FastAPI workers.
