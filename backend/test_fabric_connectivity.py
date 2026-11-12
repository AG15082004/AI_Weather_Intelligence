"""Microsoft Fabric Connectivity & Schema Discovery Verification Script.

Executes:
1. Environment & settings inspection
2. ODBC Driver 18 presence check
3. Fabric SQL endpoint connection test via SELECT 1 AS connection_status
4. Schema discovery & metadata inspection
5. Gold tables validation & benchmark comparison
6. Summary reporting
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import pyodbc
from app.config import get_settings
from app.services.fabric_connection import FabricConnectionService
from app.services.fabric_data_validator import FabricDataValidator
from app.services.fabric_schema_service import FabricSchemaService


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def main():
    print_banner("PHASE 4: MICROSOFT FABRIC CONNECTIVITY & SCHEMA DISCOVERY")
    settings = get_settings()

    # Step 1: Configuration inspection
    print("\n[Step 1] Configuration Inspection:")
    conn_svc = FabricConnectionService(settings)
    summary = conn_svc.get_safe_summary()
    for k, v in summary.items():
        print(f"  - {k:<25}: {v}")

    # Step 2: ODBC Driver check
    print("\n[Step 2] ODBC Driver 18 Verification:")
    installed_drivers = pyodbc.drivers()
    driver_name = settings.fabric_odbc_driver
    if driver_name in installed_drivers:
        print(f"  [PASS] Driver '{driver_name}' is installed on this system.")
    else:
        print(f"  [FAIL] Driver '{driver_name}' NOT found! Installed drivers: {installed_drivers}")

    # Step 3: Connection verification via SELECT 1
    print("\n[Step 3] Live SQL Connection Test (SELECT 1 AS connection_status):")
    health = await conn_svc.verify_connection()
    print(f"  - Status      : {health.get('status')}")
    print(f"  - Connected   : {health.get('connected')}")
    print(f"  - Latency     : {health.get('latency_ms')} ms")

    if not health.get("connected"):
        print(f"\n  [ERROR DETAILS]")
        print(f"  - Error Type  : {health.get('error_type')}")
        print(f"  - Message     : {health.get('error')}")
        if health.get("diagnosis"):
            print(f"  - Guidance    : {health.get('diagnosis')}")
        print("\n" + "-" * 70)
        print("Fabric endpoint connection could not complete with the current credentials.")
        print("Application state is fully preserved. Please review the guidance above.")
        print("-" * 70)
        return health

    print(f"  [PASS] Successfully executed 'SELECT 1 AS connection_status' on Fabric SQL!")

    # Step 4: Schema discovery
    print("\n[Step 4] Schema Discovery:")
    schema_svc = FabricSchemaService(conn_svc)
    schema_doc = await schema_svc.generate_schema_json()
    tables = schema_doc.get("tables", [])
    print(f"  - Discovered Schemas : {schema_doc.get('schemas')}")
    print(f"  - Total Tables Found : {len(tables)}")
    for t in tables:
        print(f"    * {t['full_name']:<35} ({t['type']}) - Rows: {t.get('row_count')}, Columns: {t.get('column_count')}")

    # Step 5: Data validation
    print("\n[Step 5] Gold Analytics Data Validation:")
    validator = FabricDataValidator(conn_svc, schema_svc)
    val_report = await validator.validate_all_tables()
    print(f"  - Validated Tables  : {val_report.get('total_tables_validated')}")
    print(f"  - Accessible Tables : {val_report.get('accessible_tables')}")

    for r in val_report.get("results", []):
        print(f"\n  Table: [{r['schema']}].[{r['table_name']}]")
        print(f"    - Accessible       : {r['accessible']}")
        print(f"    - Row Count        : {r['row_count']}")
        print(f"    - District Column  : {r['district_column']} (Count: {r['district_count']})")
        print(f"    - Date Range       : {r['min_date']} to {r['max_date']}")
        if r.get("benchmark_comparison"):
            b = r["benchmark_comparison"]
            print(f"    - Benchmark Match  : Rows={b['row_match']} (Expected: {b['expected_rows']})")

    print_banner("PHASE 4 COMPLETE")
    return {"health": health, "schema": schema_doc, "validation": val_report}


if __name__ == "__main__":
    asyncio.run(main())

