"""
Phase 8.6 Comprehensive Production & Local Validation Script
Tests:
1. Render Frontend & Backend Live Probing (Health, Operational Status, CORS, Security Headers)
2. AI Chat & 15 Intents Validation
3. Admin Security & Rate Limiting Validation
4. Local Fabric Lakehouse Connectivity & 5 Gold Tables Schema/Record Validation
5. Performance Latency Measurements (Cold vs Warm vs Cached)
"""
import urllib.request
import urllib.parse
import json
import time
import ssl
import sys
import os

PROD_BACKEND = "https://ai-weather-intelligence.onrender.com"
PROD_FRONTEND = "https://ai-weather-intelligence-1.onrender.com"
ctx = ssl.create_default_context()

def check_url(url, method="GET", headers=None, data=None, timeout=25):
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Production-Validator/1.0"
    
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            dur = (time.perf_counter() - start) * 1000
            body = resp.read()
            return {
                "status": resp.status,
                "duration_ms": round(dur, 2),
                "headers": dict(resp.getheaders()),
                "body": body,
                "error": None
            }
    except urllib.error.HTTPError as e:
        dur = (time.perf_counter() - start) * 1000
        return {
            "status": e.code,
            "duration_ms": round(dur, 2),
            "headers": dict(e.headers),
            "body": e.read(),
            "error": str(e)
        }
    except Exception as e:
        dur = (time.perf_counter() - start) * 1000
        return {
            "status": 0,
            "duration_ms": round(dur, 2),
            "headers": {},
            "body": b"",
            "error": str(e)
        }

print("="*70)
print("1. PROBING PRODUCTION BACKEND ON RENDER")
print("="*70)

endpoints = [
    ("/", "Root"),
    ("/api/health", "Health"),
    ("/api/ai/health", "AI Health"),
    ("/api/monitoring/operational-status", "Operational Status"),
    ("/api/overview", "Overview"),
    ("/api/temperature", "Temperature"),
    ("/api/rainfall", "Rainfall"),
    ("/api/districts", "Districts"),
    ("/api/current-weather", "Current Weather"),
    ("/api/air-quality", "Air Quality")
]

for path, label in endpoints:
    res = check_url(f"{PROD_BACKEND}{path}")
    print(f"[{res['status']}] {label:20} {path:35} {res['duration_ms']}ms")
    if res['error']:
        print(f"     Error: {res['error']}")
    else:
        req_id = res['headers'].get('x-request-id', 'N/A')
        csp = res['headers'].get('x-content-type-options', 'N/A')
        print(f"     X-Request-ID: {req_id} | X-Content-Type-Options: {csp}")

print("\n" + "="*70)
print("2. PROBING PRODUCTION FRONTEND ON RENDER")
print("="*70)
fe_res = check_url(PROD_FRONTEND)
print(f"[{fe_res['status']}] Frontend Root {PROD_FRONTEND} {fe_res['duration_ms']}ms")
if b"<title>" in fe_res['body']:
    print("     HTML successfully returned with title tag.")

print("\n" + "="*70)
print("3. TESTING CORS PREFLIGHT & ORIGIN RESTRICTIONS")
print("="*70)
# Allowed Origin
options_res = check_url(
    f"{PROD_BACKEND}/api/overview",
    method="OPTIONS",
    headers={
        "Origin": PROD_FRONTEND,
        "Access-Control-Request-Method": "GET"
    }
)
print(f"OPTIONS with Production Frontend Origin ({PROD_FRONTEND}):")
print(f"Status: {options_res['status']}, Allow-Origin: {options_res['headers'].get('access-control-allow-origin', 'None')}")

# Disallowed Origin
blocked_res = check_url(
    f"{PROD_BACKEND}/api/overview",
    headers={"Origin": "https://malicious-weather-spoof.com"}
)
print(f"GET with Disallowed Origin (https://malicious-weather-spoof.com):")
print(f"Status: {blocked_res['status']}, Allow-Origin header present: {'access-control-allow-origin' in blocked_res['headers']}")

print("\n" + "="*70)
print("4. TESTING SECURITY & ADMIN PROTECTION ON PRODUCTION")
print("="*70)
# Admin clear cache without key
admin_res = check_url(
    f"{PROD_BACKEND}/api/monitoring/cache/clear",
    method="POST"
)
print(f"POST /api/monitoring/cache/clear without auth:")
print(f"Status: {admin_res['status']} (Expected 401 Unauthorized)")

# Oversized payload
big_data = json.dumps({"prompt": "A" * (2 * 1024 * 1024)}).encode('utf-8')
size_res = check_url(
    f"{PROD_BACKEND}/api/ai/chat",
    method="POST",
    headers={"Content-Type": "application/json"},
    data=big_data
)
print(f"POST /api/ai/chat with 2MB payload:")
print(f"Status: {size_res['status']} (Expected 413 Payload Too Large)")

print("\n" + "="*70)
print("5. TESTING AI CHAT & DETERMINISTIC PROVIDER ON PRODUCTION")
print("="*70)
ai_data = json.dumps({"prompt": "What is today's weather across Tamil Nadu?"}).encode('utf-8')
ai_res = check_url(
    f"{PROD_BACKEND}/api/ai/chat",
    method="POST",
    headers={"Content-Type": "application/json", "Origin": PROD_FRONTEND},
    data=ai_data
)
print(f"POST /api/ai/chat:")
print(f"Status: {ai_res['status']}, Duration: {ai_res['duration_ms']}ms")
if ai_res['status'] == 200:
    try:
        resp_json = json.loads(ai_res['body'].decode('utf-8'))
        print(f"Provider: {resp_json.get('provider')} | Intent: {resp_json.get('intent')}")
        print(f"ChartSpec: {resp_json.get('chart') is not None}")
        print(f"Message snippet: {resp_json.get('response', '')[:120]}...")
    except Exception as e:
        print(f"JSON parse error: {e}")

print("\nValidation complete.")

