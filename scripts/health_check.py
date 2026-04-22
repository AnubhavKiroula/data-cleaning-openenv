#!/usr/bin/env python3
"""
Post-deployment health check script.

Usage:
    python scripts/health_check.py https://data-cleaning-backend.onrender.com

Or with the frontend URL:
    python scripts/health_check.py https://data-cleaning-frontend.onrender.com --frontend
"""

import argparse
import sys
import time
from urllib.parse import urljoin

import requests


def check_backend_health(base_url: str, retries: int = 5, delay: int = 10) -> bool:
    """Check if backend health endpoint is responding."""
    health_url = urljoin(base_url, "/health")

    for attempt in range(retries):
        try:
            print(f"  Attempt {attempt + 1}/{retries}: GET {health_url}")
            response = requests.get(health_url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                print(f"    Status: {data.get('status', 'unknown')}")
                print("    Backend is HEALTHY")
                return True
            else:
                print(f"    Status code: {response.status_code}")

        except requests.exceptions.ConnectionError:
            print(f"    Connection refused (service may be starting)")
        except requests.exceptions.Timeout:
            print(f"    Request timed out")
        except Exception as e:
            print(f"    Error: {e}")

        if attempt < retries - 1:
            print(f"    Retrying in {delay} seconds...")
            time.sleep(delay)

    return False


def check_api_docs(base_url: str) -> bool:
    """Check if API docs (FastAPI Swagger) are accessible."""
    docs_url = urljoin(base_url, "/docs")
    print(f"\n[2/5] Checking API Documentation: {docs_url}")

    try:
        response = requests.get(docs_url, timeout=30)
        if response.status_code == 200 and "swagger" in response.text.lower():
            print("    API docs are accessible")
            return True
        else:
            print(f"    Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def check_frontend(base_url: str) -> bool:
    """Check if frontend is loading."""
    print(f"\n[3/5] Checking Frontend: {base_url}")

    try:
        response = requests.get(base_url, timeout=30)
        if response.status_code == 200:
            print(f"    Status: {response.status_code}")
            print("    Frontend is responding")
            return True
        else:
            print(f"    Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def check_cors(base_url: str, frontend_url: str) -> bool:
    """Check CORS headers from backend."""
    print(f"\n[4/5] Checking CORS Configuration")

    try:
        response = requests.options(
            urljoin(base_url, "/api/datasets"),
            headers={
                "Origin": frontend_url,
                "Access-Control-Request-Method": "POST",
            },
            timeout=10,
        )

        cors_header = response.headers.get("Access-Control-Allow-Origin", "")
        if frontend_url in cors_header or "*" in cors_header:
            print("    CORS is properly configured")
            return True
        else:
            print(f"    CORS header: {cors_header}")
            print("    WARNING: CORS may not be configured for your frontend")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def run_all_checks(backend_url: str, frontend_url: str | None = None) -> bool:
    """Run all health checks."""
    print("=" * 60)
    print("DATA CLEANING PLATFORM - DEPLOYMENT HEALTH CHECK")
    print("=" * 60)

    results = []

    # 1. Backend health
    print(f"\n[1/5] Checking Backend Health: {backend_url}")
    results.append(check_backend_health(backend_url))

    # 2. API docs
    results.append(check_api_docs(backend_url))

    # 3. Frontend (if provided)
    if frontend_url:
        results.append(check_frontend(frontend_url))
    else:
        print("\n[3/5] Skipping frontend check (no URL provided)")
        results.append(True)

    # 4. CORS
    if frontend_url:
        results.append(check_cors(backend_url, frontend_url))
    else:
        print("\n[4/5] Skipping CORS check (no frontend URL provided)")
        results.append(True)

    # 5. Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    checks = [
        "Backend Health",
        "API Documentation",
        "Frontend",
        "CORS Configuration",
    ]

    for check, passed in zip(checks, results):
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {check}: {status}")

    all_passed = all(results)
    print("\n" + "=" * 60)

    if all_passed:
        print("ALL CHECKS PASSED - Deployment is healthy!")
        print("=" * 60)
        return True
    else:
        print("SOME CHECKS FAILED - See details above")
        print("=" * 60)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Health check for data-cleaning-openenv deployment"
    )
    parser.add_argument(
        "backend_url",
        help="Backend URL (e.g., https://data-cleaning-backend.onrender.com)",
    )
    parser.add_argument(
        "--frontend",
        dest="frontend_url",
        help="Frontend URL (e.g., https://data-cleaning-frontend.onrender.com)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help="Number of retry attempts for health check (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=10,
        help="Delay between retries in seconds (default: 10)",
    )

    args = parser.parse_args()

    success = run_all_checks(args.backend_url, args.frontend_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
