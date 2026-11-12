"""Comprehensive Phase 5 Verification Test Suite for Microsoft Fabric Weather Analytics.

Tests every endpoint against live Microsoft Fabric Lakehouse data:
1. /api/overview
2. /api/temperature (with date & district filters)
3. /api/rainfall (with monthly metrics & category classifications)
4. /api/districts & /api/districts/{name} (all 38 districts)
5. /api/current-weather (38 districts live telemetry)
6. /api/air-quality (38 districts AQI & pollutant metrics)
7. Security: Parameterized SQL injection protection
8. Edge cases: Empty filters, non-existent district handling
"""

import sys
from pathlib import Path

# Add backend root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_overview():
    print("\n[Test 1] GET /api/overview")
    res = client.get("/api/overview")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    body = res.json()
    assert body.get("status") == "success"
    data = body.get("data", {})

    print(f"  - Districts covered  : {data.get('districts_covered')} (Expected: 38)")
    print(f"  - Avg Temperature    : {data.get('avg_temperature')} °C")
    print(f"  - Max Temperature    : {data.get('max_temperature')} °C")
    print(f"  - Min Temperature    : {data.get('min_temperature')} °C")
    print(f"  - Total Rainfall     : {data.get('total_rainfall')} mm")
    print(f"  - Avg Humidity       : {data.get('avg_humidity')} %")
    print(f"  - Latest Observation : {data.get('latest_observation')}")
    print(f"  - Temperature Trends : {len(data.get('temperature_trend', []))} points")
    print(f"  - Rainfall Trends    : {len(data.get('rainfall_trend', []))} points")
    print(f"  - District Comp Rows : {len(data.get('district_comparison', []))} districts")

    assert data.get("districts_covered") == 38, "Should cover all 38 districts"
    assert len(data.get("district_comparison", [])) == 38, "Should have 38 district comparison items"
    assert len(data.get("temperature_trend", [])) > 0, "Should have temperature trends"
    print("  [PASS] /api/overview verified successfully!")


def test_temperature():
    print("\n[Test 2] GET /api/temperature")
    # Base unfiltered test
    res = client.get("/api/temperature")
    assert res.status_code == 200
    data = res.json().get("data", [])
    print(f"  - Unfiltered records returned : {len(data)}")
    assert len(data) > 0, "Temperature data must not be empty"
    first = data[0]
    print(f"  - Sample row: date={first.get('date')}, district={first.get('district')}, avg_temp={first.get('avg_temp')} °C")

    # Filtered by district
    res_dist = client.get("/api/temperature?district=Chennai")
    assert res_dist.status_code == 200
    data_dist = res_dist.json().get("data", [])
    print(f"  - District filter 'Chennai'   : {len(data_dist)} rows")
    assert all(r.get("district") == "Chennai" for r in data_dist), "All rows should be Chennai"

    # Filtered by date range
    res_date = client.get("/api/temperature?start_date=2026-10-01&end_date=2026-10-07&district=Madurai")
    assert res_date.status_code == 200
    data_date = res_date.json().get("data", [])
    print(f"  - Date range + district filter: {len(data_date)} rows (Expected: 7 rows for 7 days)")
    assert len(data_date) == 7, f"Expected 7 daily observations, got {len(data_date)}"
    print("  [PASS] /api/temperature verified with filters!")


def test_rainfall():
    print("\n[Test 3] GET /api/rainfall")
    res = client.get("/api/rainfall")
    assert res.status_code == 200
    body = res.json()
    data = body.get("data", [])
    meta = body.get("metadata", {})
    monthly = meta.get("monthly_trends", [])

    print(f"  - Daily rainfall records  : {len(data)}")
    print(f"  - Monthly trend records   : {len(monthly)}")
    assert len(data) > 0, "Rainfall data must not be empty"
    assert len(monthly) > 0, "Monthly trends must be present in metadata"

    # Filtered by district
    res_dist = client.get("/api/rainfall?district=Coimbatore")
    assert res_dist.status_code == 200
    data_dist = res_dist.json().get("data", [])
    assert all(r.get("district") == "Coimbatore" for r in data_dist)
    print(f"  - District filter 'Coimbatore': {len(data_dist)} daily records")
    print("  [PASS] /api/rainfall verified successfully!")


def test_districts():
    print("\n[Test 4] GET /api/districts & /api/districts/{name}")
    # All 38 districts list
    res = client.get("/api/districts")
    assert res.status_code == 200
    data = res.json().get("data", [])
    print(f"  - Total districts returned: {len(data)} (Expected: 38)")
    assert len(data) == 38, f"Expected 38 districts, got {len(data)}"

    # Specific district detail
    res_single = client.get("/api/districts/Madurai")
    assert res_single.status_code == 200
    data_single = res_single.json().get("data", [])
    assert len(data_single) == 1, "Should return 1 district"
    madurai = data_single[0]
    print(f"  - Madurai KPIs: avg_temp={madurai.get('avg_temp')} °C, current_temp={madurai.get('current_temp')} °C, condition={madurai.get('current_condition')}")
    assert madurai.get("district") == "Madurai"
    print("  [PASS] /api/districts verified successfully!")


def test_current_weather():
    print("\n[Test 5] GET /api/current-weather")
    res = client.get("/api/current-weather")
    assert res.status_code == 200
    data = res.json().get("data", [])
    print(f"  - Current weather reporting districts: {len(data)} (Expected: 38)")
    assert len(data) == 38, f"Expected 38 records in gold_current_weather_latest, got {len(data)}"

    sample = data[0]
    print(f"  - Sample ({sample.get('district')}): temp={sample.get('temperature')} °C, feels_like={sample.get('feels_like')} °C, humidity={sample.get('humidity')} %, condition={sample.get('condition')}, wind={sample.get('wind_speed')} km/h {sample.get('wind_direction')}, updated={sample.get('last_updated')}")

    # Single district filter
    res_dist = client.get("/api/current-weather?district=Salem")
    assert res_dist.status_code == 200
    data_dist = res_dist.json().get("data", [])
    assert len(data_dist) == 1 and data_dist[0].get("district") == "Salem"
    print(f"  - Filter 'Salem': {data_dist[0].get('district')} -> {data_dist[0].get('temperature')} °C, {data_dist[0].get('condition')}")
    print("  [PASS] /api/current-weather verified successfully!")


def test_air_quality():
    print("\n[Test 6] GET /api/air-quality")
    res = client.get("/api/air-quality")
    assert res.status_code == 200
    data = res.json().get("data", [])
    print(f"  - Air quality reporting districts: {len(data)} (Expected: 38)")
    assert len(data) == 38, f"Expected 38 records in gold_air_quality_latest, got {len(data)}"

    sample = data[0]
    print(f"  - Highest AQI ({sample.get('district')}): EPA Index={sample.get('aqi')} ({sample.get('category')}), PM2.5={sample.get('pm25')} µg/m³, PM10={sample.get('pm10')} µg/m³, DEFRA={sample.get('gb_defra_category')}")

    # Single district filter
    res_dist = client.get("/api/air-quality?district=Tiruchirappalli")
    assert res_dist.status_code == 200
    data_dist = res_dist.json().get("data", [])
    assert len(data_dist) == 1 and data_dist[0].get("district") == "Tiruchirappalli"
    print(f"  - Filter 'Tiruchirappalli': AQI Category={data_dist[0].get('category')}, PM2.5={data_dist[0].get('pm25')}")
    print("  [PASS] /api/air-quality verified successfully!")


def test_security_and_edge_cases():
    print("\n[Test 7] Security (SQL Injection Protection) & Edge Cases")

    # SQL Injection attempt in district parameter
    malicious = "Chennai' OR 1=1 --"
    res_inj = client.get(f"/api/temperature?district={malicious}")
    assert res_inj.status_code == 200, "Parameterized queries must not crash or execute injection"
    data_inj = res_inj.json().get("data", [])
    assert len(data_inj) == 0, "Injection parameter should match 0 rows"
    print("  [PASS] Parameterized SQL injection protection verified!")

    # Non-existent district query
    res_none = client.get("/api/districts/ImaginaryDistrict999")
    assert res_none.status_code == 200
    data_none = res_none.json().get("data", [])
    assert len(data_none) == 0, "Non-existent district should return empty list"
    print("  [PASS] Empty response for non-existent district verified!")


def main():
    print_banner("PHASE 5: LIVE FABRIC WEATHER ANALYTICS VERIFICATION TEST")
    test_overview()
    test_temperature()
    test_rainfall()
    test_districts()
    test_current_weather()
    test_air_quality()
    test_security_and_edge_cases()
    print_banner("ALL PHASE 5 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()

