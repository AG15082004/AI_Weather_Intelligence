# Final Architecture Documentation: Tamil Nadu Weather Intelligence Platform

**System:** Enterprise Weather Intelligence & Conversational Analytics  
**Coverage:** 38 Districts of Tamil Nadu  
**Timezone Standard:** `Asia/Kolkata` (IST, UTC+5:30)  
**Database:** Microsoft Fabric Lakehouse (`lh_tn_weather_intelligence`)  

---

## 1. System Architecture Diagram

```
                                  +----------------------------------------------------+
                                  |                 Browser Client                     |
                                  |    (React 19 + Vite + Tailwind + Recharts)         |
                                  +-------------------------+--------------------------+
                                                            |
                                                   HTTPS / JSON REST
                                                            |
                                                            v
+---------------------------------------------------------------------------------------------------------------+
|                                      FastAPI Backend Application                                              |
|                                                                                                               |
|  +-----------------------------+   +-------------------------------+   +-----------------------------------+  |
|  |     Security Middleware     |   |       Routing Layer           |   |       AI Engine Subsystem         |  |
|  | - OWASP Security Headers    |   | - /api/overview               |   | - Intent Classifier (15 intents)  |  |
|  | - CORS Preflight & Origins  |   | - /api/temperature            |   | - Grounded Response Generator     |  |
|  | - In-Memory Rate Limiting   |   | - /api/rainfall               |   | - ChartSpec Visualizer            |  |
|  | - Payload Size Restrictor   |   | - /api/districts              |   | - Session Memory Context          |  |
|  | - Secret Masking Logger     |   | - /api/current-weather        |   | - Deterministic Provider Fallback |  |
|  +-----------------------------+   | - /api/air-quality            |   | - Ollama Qwen3:4b (Local)         |  |
|                                    | - /api/monitoring             |   +-----------------------------------+  |
|                                    +---------------+---------------+                                          |
|                                                    |                                                          |
|                                                    v                                                          |
|  +-------------------------------------------------+-------------------------------------------------------+  |
|  |                             WeatherService & Data Reliability Layer                                      |  |
|  |                                                                                                         |  |
|  |    +-----------------------------+                           +-------------------------------------+    |  |
|  |    |        TTLCache             |                           |      DataReliabilityService         |    |  |
|  |    | - (Value, Expiry, CreatedAt)|                           | - Thread-safe Singleton             |    |  |
|  |    | - Bounded Max Entries (500) |                           | - Independent 5-Table Freshness     |    |  |
|  |    | - Stale Cache Grace Fetch   |                           | - State Machine: LIVE / CACHED /    |    |  |
|  |    +--------------+--------------+                           |   FALLBACK / UNAVAILABLE            |    |  |
|  |                   |                                          +-------------------------------------+    |  |
|  |                   v                                                                                     |  |
|  |    +-----------------------------------------------------------------------------------------------+    |  |
|  |    |                                    QueryExecutor                                              |    |  |
|  |    | - pyodbc SQL Connection Pool                                                                  |    |  |
|  |    | - Parameterized Query Sanitization                                                            |    |  |
|  |    | - Semantic Exception Hierarchy (Timeout, Connection, Auth)                                    |    |  |
|  |    +-----------------------------------------------+-----------------------------------------------+    |  |
+-------------------------------------------------------|-------------------------------------------------------+
                                                        |
                                            ODBC Driver 18 / TCP 1433
                                                        |
                                                        v
+---------------------------------------------------------------------------------------------------------------+
|                                      Microsoft Fabric Lakehouse                                               |
|                                       (lh_tn_weather_intelligence)                                            |
|                                                                                                               |
|   +------------------------------------+             +----------------------------------------------------+   |
|   |            Gold Layer              |             |                    Silver Layer                    |   |
|   | - gold_district_daily_analytics    |             | - silver_weather_current                           |   |
|   | - gold_district_monthly_analytics  |             | - silver_weather_forecast                          |   |
|   | - gold_district_rainfall_analytics |             +----------------------------------------------------+   |
|   | - gold_current_weather_latest      |                                                                      |
|   | - gold_air_quality_latest          |                                                                      |
|   | - dim_district                     |                                                                      |
|   +------------------------------------+                                                                      |
+---------------------------------------------------------------------------------------------------------------+
```

---

## 2. Key Subsystems and Design Decisions

### 2.1 The Medallion Data Architecture (Microsoft Fabric)
1. **Bronze Layer:** Raw JSON ingestion from Open-Meteo and IMD weather stations.
2. **Silver Layer (`dbo.silver_*`):** Cleaned, typed, deduplicated tables storing hourly observations.
3. **Gold Layer (`dbo.gold_*`):** Aggregated, analytical models optimized for direct dashboard querying:
   - `gold_district_daily_analytics`: Daily temperature extremes and rainfall.
   - `gold_district_monthly_analytics`: 30-day climate trends and averages.
   - `gold_district_rainfall_analytics`: Cumulative precipitation, monsoon tracking, and deviation anomalies.
   - `gold_current_weather_latest`: District-level latest observations.
   - `gold_air_quality_latest`: AQI metrics and sub-pollutant concentrations.

### 2.2 Dual AI Provider Strategy: Ollama vs Deterministic Engine
To guarantee zero-cost operation and eliminate dependencies on paid external APIs (such as OpenAI or Anthropic):
- **Local Development:** When Ollama is running locally with `qwen3:4b`, queries leverage natural language formulation.
- **Cloud Production:** In environments where Ollama is absent (Render containers), the system automatically selects the **Deterministic Grounded Response Generator**:
  - Classifies user questions into one of 15 meteorological intents using regex and entity extractors.
  - Extracts parameters (district name, date range, metric).
  - Queries Lakehouse Gold tables directly.
  - Formats human-readable responses with strict mathematical precision.
  - Generates valid `ChartSpec` JSON for dynamic Recharts visualization.
  - Zero token costs, zero latency overhead (under 10ms generation).

### 2.3 Strict Data Quality & Rainfall Null Preservation
- In meteorological science, an unrecorded observation (`NULL`) must never be misrepresented as a dry day (`0.0 mm`).
- The application guarantees end-to-end NULL preservation:
  - SQL `NULL` -> Python `None` -> JSON `null` -> React `"N/A"` / `"Data Offline"`.
  - Aggregations compute completeness percentages without downward bias.

### 2.4 Bounded Caching & Degraded Mode
- `TTLCache` enforces a hard limit of 500 entries with thread-safe locking and LRU eviction.
- During Fabric connection timeouts or outages:
  1. Serves existing cache as stale data with an amber warning banner.
  2. If cache is empty, returns `UNAVAILABLE` status without crashing with HTTP 500.
  3. Resumes `LIVE` execution upon Fabric reconnection.
