#!/usr/bin/env python3
"""Fabric Production Diagnostics CLI Tool.

Performs non-destructive, safe diagnostic checks:
1. Environment configuration
2. ODBC Driver 18 availability
3. TCP port 1433 reachability
4. Entra ID token acquisition
5. SQL ping (SELECT 1 AS connection_status)
6. Five Gold tables queryability & record counts
7. Meteorological data freshness

Zero secret leakage. Safe for logs and CI/CD pipelines.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.services.fabric_connection import FabricConnectionService


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


async def run_diagnostics():
    print_banner("MICROSOFT FABRIC PRODUCTION CONNECTIVITY DIAGNOSTICS")
    settings = get_settings()
    svc = FabricConnectionService(settings)

    print("\n[1/6] Safe Configuration Inspection:")
    summary = svc.get_safe_summary()
    for k, v in summary.items():
        print(f"  - {k:<28}: {v}")

    print("\n[2/6] Multi-Step Connectivity Diagnostics:")
    diag = await svc.diagnose_fabric_connectivity()

    code = diag.get("code")
    status = diag.get("status")
    print(f"  - Overall Result Code        : {code}")
    print(f"  - Overall Status             : {status}")

    steps = diag.get("steps", {})
    for step_name, step_data in steps.items():
        print(f"\n  [Step: {step_name.upper()}]")
        if isinstance(step_data, dict):
            for sk, sv in step_data.items():
                print(f"    * {sk:<24}: {sv}")
        else:
            print(f"    * {step_data}")

    if status != "connected":
        print("\n" + "!" * 70)
        print("  DIAGNOSTIC FAILURE DETAILS")
        print("!" * 70)
        print(f"  - Error Code : {code}")
        print(f"  - Message    : {diag.get('message')}")
        if diag.get("diagnosis"):
            print(f"  - Diagnosis  : {diag.get('diagnosis')}")
        print("!" * 70)
        return False

    print("\n" + "=" * 70)
    print("  [SUCCESS] All Fabric connectivity checks and Gold tables passed!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_diagnostics())
    sys.exit(0 if success else 1)

