# Data Freshness & Quality Policy

**Platform:** Tamil Nadu Weather Intelligence Platform  
**Target Region:** 38 Districts of Tamil Nadu  
**Timezone Standard:** `Asia/Kolkata` (IST, UTC+5:30)  

---

## 1. Dataset Freshness Thresholds

Freshness thresholds reflect meteorological realities and ingestion frequencies across the Lakehouse medallion architecture:

| Lakehouse Gold Table | Metric Type | Freshness Threshold | Cache TTL | Staleness Condition (`is_stale = true`) |
|:---|:---|:---|:---|:---|
| `gold_current_weather_latest` | Real-time weather (Temp, Humidity, Wind, Conditions) | **1 hour** (3,600s) | 600s | Query/Cache age > 1 hour |
| `gold_air_quality_latest` | Real-time AQI, PM2.5, PM10, EPA/DEFRA indices | **1 hour** (3,600s) | 600s | Query/Cache age > 1 hour |
| `gold_district_daily_analytics` | 24-hour aggregated observations | **24 hours** (86,400s) | 3,600s | Observation date < Today - 1 day |
| `gold_district_monthly_analytics` | Monthly temperature/humidity climate summaries | **30 days** (2,592,000s) | 86,400s | Observation month < Current month - 1 |
| `gold_district_rainfall_analytics` | Monthly cumulative rainfall and anomalies | **30 days** (2,592,000s) | 86,400s | Analytics timestamp > 30 days old |

---

## 2. Timezone Policy: Strict Asia/Kolkata (IST)

All dates, times, timestamps, and intervals across backend logs, APIs, frontend UI, and AI conversational outputs are strictly anchored in Indian Standard Time (`Asia/Kolkata`, UTC+5:30):

1. **No UTC Timestamp Leakage:** APIs format timestamps as `YYYY-MM-DD HH:MM:SS IST` or ISO 8601 with explicit `+05:30` offset.
2. **Date Boundaries:** "Today" and "Yesterday" calculations evaluate according to IST midnight, preventing date-skew artifacts common with UTC servers hosted in international regions.
3. **Startup Verification:** `backend/app/main.py` performs a startup check on `zoneinfo.ZoneInfo("Asia/Kolkata")` to guarantee OS timezone support.

---

## 3. Strict Rainfall Data Quality & Null Preservation

Rainfall measurements require strict scientific distinction between zero rainfall and unmeasured precipitation:

### 3.1 Measured Zero vs Unmeasured (NULL)
- **Measured Zero (`0.0 mm`):** An active rain gauge or observation station operated for the observation interval and recorded exactly zero precipitation.
- **Unmeasured (`NULL`):** No station reported data, or data failed quality control. In SQL, this value is `NULL`.

### 3.2 Anti-Coercion Guarantee
1. **Database & ORM:** SQL `NULL` values are deserialized as Python `None`.
2. **JSON Payloads:** Emitted as JSON `null`.
3. **Frontend UI:** Displayed as `"N/A"` or `"Unmeasured"`.
4. **Calculations:** Sums and averages filter out unmeasured days rather than assuming 0.0 mm, preventing artificial downward bias in climate metrics.
5. **Quality Metadata:** API returns completeness percentage, measured zero days count, positive rainfall days count, and missing unmeasured days count via `RainfallQualityMetadata`.
