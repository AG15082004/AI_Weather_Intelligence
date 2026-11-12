# Microsoft Fabric SQL Connectivity & Schema Discovery Report

**Project**: Tamil Nadu Weather Intelligence Platform  
**Target Lakehouse**: `lh_tn_weather_intelligence`  
**Phase**: Phase 4 – Microsoft Fabric SQL Connectivity & Schema Discovery  
**Status**: **VERIFIED & CONNECTED (LIVE)**  
**Authentication**: Azure CLI Token (`https://database.windows.net/.default` via ODBC attribute 1256 `SQL_COPT_SS_ACCESS_TOKEN`)  
**Generated At**: 2026-11-12  

---

## 1. Executive Summary

Phase 4 has achieved **100% verified live connectivity** between the FastAPI application and the Microsoft Fabric Lakehouse SQL Analytics Endpoint. 

- **Connection Verification**: Successfully executed `SELECT 1 AS connection_status;` with a round-trip query latency of **~2.1 seconds**.
- **Discovery Engine**: Dynamically queried `INFORMATION_SCHEMA` across all database catalogs without hardcoded assumptions.
- **Discovered Tables**: **24 total tables** across 3 schemas (`dbo`, `queryinsights`, `sys`).
- **Data Integrity Validation**: Verified all 5 Gold analytics datasets, confirming exact row counts, 38-district coverage, and historical/live date ranges matching Fabric platform statistics.
- **Generated Schema Artifact**: Serialized to [backend/app/database/fabric_schema.json](file:///d:/TN_Weather_Api/backend/app/database/fabric_schema.json) (4,713 lines).

---

## 2. Authentication Architecture & Token Handling

### 2.1 Azure CLI Token Acquisition
- **Library**: `azure-identity` (installed and added to `requirements.txt`).
- **Credential Class**: `AzureCliCredential`.
- **Target Resource**: `https://database.windows.net/.default`.
- **ODBC Attribute**: `SQL_COPT_SS_ACCESS_TOKEN` (`attribute 1256`).
- **Encoding & Packing**:
  - Access token encoded in `UTF-16-LE`.
  - Prefixed with 4-byte unsigned 32-bit little-endian length integer: `struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)`.
- **ODBC Connection String**:
  ```
  Driver={ODBC Driver 18 for SQL Server};Server=xjee6istmh4ujox46dsz6wf5p4-4bny2krhontunado6jkvf4o7my.datawarehouse.fabric.microsoft.com;Database=lh_tn_weather_intelligence;Encrypt=yes;TrustServerCertificate=no;APP=TN_Weather_Intelligence_Platform;
  ```
  *(Note: UID, PWD, and Authentication are strictly omitted from the token-based connection string)*.
- **Connection Invocation**:
  ```python
  pyodbc.connect(connection_string, attrs_before={1256: token_struct}, timeout=30)
  ```
- **Token Expiration & Refresh**:
  - Automatically tracks `token_obj.expires_on`.
  - Reuses valid tokens and refreshes proactively 300 seconds before expiration.
  - Zero token values exposed in logs, exceptions, or API endpoints.

### 2.2 Configured Environment Modes (`FABRIC_AUTH_MODE`)
1. `azure_cli`: Default local development mode using the active developer session.
2. `service_principal`: Production unattended mode via `FABRIC_CLIENT_ID` and `FABRIC_CLIENT_SECRET`.
3. `interactive`: Interactive browser-prompt Entra ID single sign-on.

---

## 3. Verified Live Connection Test

Executing `python test_fabric_connectivity.py`:

```
======================================================================
  PHASE 4: MICROSOFT FABRIC CONNECTIVITY & SCHEMA DISCOVERY
======================================================================

[Step 1] Configuration Inspection:
  - server                   : xjee6istmh4u....datawarehouse.fabric.microsoft.com
  - database                 : lh_tn_weather_intelligence
  - auth_mode                : azure_cli
  - driver                   : ODBC Driver 18 for SQL Server
  - encrypt                  : yes
  - trust_server_certificate : no
  - timeout_seconds          : 30
  - token_cached             : False
  - has_tenant_id            : True

[Step 2] ODBC Driver 18 Verification:
  [PASS] Driver 'ODBC Driver 18 for SQL Server' is installed on this system.

[Step 3] Live SQL Connection Test (SELECT 1 AS connection_status):
  - Status      : connected
  - Connected   : True
  - Latency     : 2417.41 ms
  [PASS] Successfully executed 'SELECT 1 AS connection_status' on Fabric SQL!
```

### 3.1 REST API Health Endpoint
- `GET /api/fabric/health` → **HTTP 200 OK**
```json
{
  "status": "connected",
  "connected": true,
  "query_status": 1,
  "latency_ms": 2112.03,
  "timestamp": "2026-11-12T06:12:52Z",
  "details": {
    "server": "xjee6istmh4u....datawarehouse.fabric.microsoft.com",
    "database": "lh_tn_weather_intelligence",
    "auth_mode": "azure_cli",
    "driver": "ODBC Driver 18 for SQL Server",
    "encrypt": "yes",
    "trust_server_certificate": "no",
    "timeout_seconds": 30,
    "token_cached": true,
    "has_tenant_id": true
  }
}
```

---

## 4. Discovered Microsoft Fabric Schema & Gold Tables

### 4.1 Summary of Discovered Tables (24 Tables)

| Schema | Table Name | Type | Row Count | Column Count | Description |
|---|---|---|---|---|---|
| `dbo` | `gold_district_daily_analytics` | BASE TABLE | **11,666** | 14 | Daily weather observations across all 38 districts |
| `dbo` | `gold_district_monthly_analytics` | BASE TABLE | **418** | 15 | Monthly aggregated weather metrics |
| `dbo` | `gold_district_rainfall_analytics` | BASE TABLE | **418** | 11 | Monthly precipitation and departure metrics |
| `dbo` | `gold_current_weather_latest` | BASE TABLE | **38** | 30 | Fresh current weather (one record per district) |
| `dbo` | `gold_air_quality_latest` | BASE TABLE | **38** | 17 | Fresh air quality / AQI (one record per district) |
| `dbo` | `dim_district` | BASE TABLE | **38** | 12 | Canonical Tamil Nadu district master |
| `dbo` | `dim_date` | BASE TABLE | **307** | 16 | Date dimension table |
| `dbo` | `dim_month` | BASE TABLE | **11** | 8 | Month dimension table |
| `dbo` | `silver_weather_daily` | BASE TABLE | 11,666 | 14 | Silver cleaned daily weather observations |
| `dbo` | `silver_weather_hourly` | BASE TABLE | 279,984 | 20 | Silver cleaned hourly weather observations |
| `dbo` | `silver_weather_current` | BASE TABLE | 532 | 44 | Silver current weather historical snapshots |
| `dbo` | `bronze_openmeteo_daily` | BASE TABLE | 11,666 | 16 | Bronze Open-Meteo daily raw ingestion |
| `dbo` | `bronze_openmeteo_hourly` | BASE TABLE | 279,984 | 22 | Bronze Open-Meteo hourly raw ingestion |
| `dbo` | `bronze_openmeteo_api_raw` | BASE TABLE | 418 | 16 | Bronze API payloads |
| `dbo` | `bronze_openmeteo_ingestion_audit` | BASE TABLE | 418 | 13 | Open-Meteo pipeline audit trail |
| `dbo` | `bronze_weatherapi_current` | BASE TABLE | 532 | 42 | Bronze WeatherAPI current observations |
| `dbo` | `bronze_weatherapi_current_raw` | BASE TABLE | 532 | 10 | Bronze WeatherAPI raw payloads |
| `dbo` | `bronze_weatherapi_ingestion_audit` | BASE TABLE | 14 | 8 | WeatherAPI pipeline audit trail |
| `queryinsights` | `sql_pool_insights` | VIEW | 44 | 7 | Fabric capacity performance insights |
| `queryinsights` | `exec_requests_history` | VIEW | 6 | 30 | Request execution logs |
| `queryinsights` | `frequently_run_queries` | VIEW | 1 | 14 | Query frequency analysis |
| `queryinsights` | `long_running_queries` | VIEW | 1 | 10 | Query execution performance |
| `queryinsights` | `exec_sessions_history` | VIEW | 0 | 35 | Session history |
| `queryinsights` | `external_api_call_stats` | VIEW | 0 | 19 | External call stats |

---

## 5. Discovered Column Schemas for Gold & Dimension Tables

### 1. `gold_district_daily_analytics` (11,666 rows)
- `district_id` (int)
- `district_name` (varchar 8000)
- `weather_date` (date)
- `temperature_2m_max` (float)
- `temperature_2m_min` (float)
- `temperature_2m_mean` (float)
- `precipitation_sum` (float)
- `relative_humidity_2m_mean` (float)
- `wind_speed_10m_max` (float)
- `wind_gusts_10m_max` (float)
- `weather_code` (int)
- `temperature_range_c` (float)
- `is_rainy_day` (int)
- `gold_transformed_at_utc` (datetime2)

### 2. `gold_district_monthly_analytics` (418 rows)
- `district_id` (int)
- `district_name` (varchar 8000)
- `year` (int)
- `month` (int)
- `month_start_date` (date)
- `observed_days` (int)
- `avg_temperature_c` (float)
- `max_temperature_c` (float)
- `min_temperature_c` (float)
- `avg_humidity_percent` (float)
- `avg_max_wind_speed_kph` (float)
- `avg_max_wind_gust_kph` (float)
- `total_rainfall_mm` (float)
- `rainy_days` (int)
- `gold_transformed_at_utc` (datetime2)

### 3. `gold_district_rainfall_analytics` (418 rows)
- `district_id` (int)
- `district_name` (varchar 8000)
- `year` (int)
- `month` (int)
- `month_start_date` (date)
- `total_rainfall_mm` (float)
- `avg_daily_rainfall_mm` (float)
- `max_daily_rainfall_mm` (float)
- `rainy_days` (int)
- `observed_days` (int)
- `gold_transformed_at_utc` (datetime2)

### 4. `gold_current_weather_latest` (38 rows)
- `snapshot_id` (varchar 8000), `run_id` (varchar 8000)
- `district_id` (int), `district_name` (varchar 8000)
- `latitude` (float), `longitude` (float)
- `location_name` (varchar 8000), `region` (varchar 8000), `country` (varchar 8000)
- `requested_at_utc` (datetime2), `local_time` (varchar 8000), `last_updated` (varchar 8000)
- `temperature_c` (float), `temperature_f` (float)
- `feels_like_c` (float), `heat_index_c` (float), `wind_chill_c` (float)
- `condition_text` (varchar 8000), `condition_code` (int)
- `wind_kph` (float), `wind_direction` (varchar 8000), `wind_gust_kph` (float)
- `pressure_mb` (float), `precipitation_mm` (float), `humidity` (int)
- `cloud_cover` (int), `visibility_km` (float), `uv_index` (float)
- `ingestion_date` (date), `gold_transformed_at_utc` (datetime2)

### 5. `gold_air_quality_latest` (38 rows)
- `snapshot_id` (varchar 8000), `run_id` (varchar 8000)
- `district_id` (int), `district_name` (varchar 8000)
- `requested_at_utc` (datetime2), `last_updated` (varchar 8000)
- `aqi_co` (float), `aqi_no2` (float), `aqi_o3` (float), `aqi_so2` (float), `aqi_pm2_5` (float), `aqi_pm10` (float)
- `us_epa_index` (int), `gb_defra_index` (int)
- `us_epa_category` (varchar 8000), `gb_defra_category` (varchar 8000)
- `gold_transformed_at_utc` (datetime2)

### 6. `dim_district` (38 rows)
- `district_id` (int), `district_name` (varchar 8000), `reference_location` (varchar 8000)
- `latitude` (float), `longitude` (float), `state_name` (varchar 8000), `timezone` (varchar 8000)
- `coordinate_type` (varchar 8000), `coordinate_source` (varchar 8000), `is_active` (bit)
- `created_at` (datetime2), `updated_at` (datetime2)

---

## 6. Data Validation Results vs Documented Benchmarks

| Table Name | Documented Benchmark | Discovered Live Rows | District Count | Date Range | Benchmark Status |
|---|---|---|---|---|---|
| `gold_district_daily_analytics` | 11,666 records | **11,666** | 38 districts | 2026-01-01 to 2026-11-03 | **100% MATCH** |
| `gold_district_monthly_analytics` | 418 records | **418** | 38 districts | 2026-01-01 to 2026-11-01 | **100% MATCH** |
| `gold_district_rainfall_analytics` | 418 records | **418** | 38 districts | 2026-01-01 to 2026-11-01 | **100% MATCH** |
| `gold_current_weather_latest` | 38 records | **38** | 38 districts | Fresh live observations | **100% MATCH** |
| `gold_air_quality_latest` | 38 records | **38** | 38 districts | Fresh live observations | **100% MATCH** |
| `dim_district` | 38 records | **38** | 38 districts | Active 38 districts of Tamil Nadu | **100% MATCH** |

---

## 7. Next Steps: Phase 5 & Phase 6

With live connectivity established and exact table/column names verified:
1. **Phase 5**: Connect `weather_service.py` and `analytics_service.py` to query these exact Gold tables (`gold_district_daily_analytics`, `gold_district_monthly_analytics`, `gold_district_rainfall_analytics`, `gold_current_weather_latest`, `gold_air_quality_latest`).
2. **Phase 6**: Stream live Fabric Lakehouse data directly into the React dashboards, replacing fallback placeholders with real-time analytics.
