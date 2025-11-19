#!/usr/bin/env python3
"""
Test script for Deliverer Dashboard
Tests the deliverer dashboard functionality and identifies errors
"""

import requests
from requests.sessions import Session

BASE_URL = "http://localhost:5000"

def test_deliverer_dashboard():
    """Test the deliverer dashboard"""
    print("=" * 60)
    print("DELIVERER DASHBOARD TEST")
    print("=" * 60)

    # Create session to maintain cookies
    session = Session()

    # Test 1: Login as deliverer
    print("\n[TEST 1] Testing deliverer login...")
    login_data = {
        'email': 'sipho.driver@sparzafi.com',
        'password': 'driverpass'
    }

    try:
        login_response = session.post(f"{BASE_URL}/user/login", data=login_data, allow_redirects=False)
        print(f"  Status Code: {login_response.status_code}")

        if login_response.status_code in [200, 302]:
            print("  ✓ Login successful")
        else:
            print(f"  ✗ Login failed: {login_response.text[:200]}")
            return
    except Exception as e:
        print(f"  ✗ Login error: {str(e)}")
        return

    # Test 2: Access deliverer dashboard
    print("\n[TEST 2] Testing deliverer dashboard access...")
    try:
        dashboard_response = session.get(f"{BASE_URL}/deliverer/dashboard", allow_redirects=False)
        print(f"  Status Code: {dashboard_response.status_code}")

        if dashboard_response.status_code == 200:
            print("  ✓ Dashboard accessible")

            # Check for common errors in response
            response_text = dashboard_response.text

            # Check for JavaScript errors
            if "Uncaught" in response_text or "TypeError" in response_text:
                print("  ⚠ Potential JavaScript errors detected")

            # Check for template rendering issues
            if "{{" in response_text or "}}" in response_text:
                print("  ⚠ Template variable not rendered properly")
                # Find the unrendered variables
                import re
                unrendered = re.findall(r'\{\{[^}]+\}\}', response_text)
                if unrendered:
                    print(f"    Unrendered variables: {unrendered[:5]}")

            # Check for None values displayed
            if "None" in response_text:
                print("  ⚠ 'None' values found in HTML (possible missing data)")

            # Check for NaN values
            if "NaN" in response_text or "undefined" in response_text:
                print("  ⚠ NaN or undefined values detected")

            # Check for error messages
            if "error" in response_text.lower() or "exception" in response_text.lower():
                print("  ⚠ Error keywords found in response")

            print(f"\n  Response length: {len(response_text)} bytes")

        elif dashboard_response.status_code == 302:
            print(f"  → Redirected to: {dashboard_response.headers.get('Location')}")
        elif dashboard_response.status_code == 500:
            print("  ✗ Server error (500)")
            print(f"    Error: {dashboard_response.text[:500]}")
        else:
            print(f"  ✗ Unexpected status code: {dashboard_response.status_code}")

    except Exception as e:
        print(f"  ✗ Dashboard access error: {str(e)}")

    # Test 3: Check for specific dashboard elements
    print("\n[TEST 3] Checking dashboard elements...")
    if dashboard_response.status_code == 200:
        response_text = dashboard_response.text

        elements_to_check = {
            "Performance Metrics": "📈 Performance Metrics" in response_text,
            "My Routes": "🚗 My Routes" in response_text,
            "Earnings": "📊 Earnings" in response_text,
            "Active Deliveries": "📦 Active Deliveries" in response_text,
            "Available Pickups": "🚀 Available Pickups" in response_text,
            "Charts": "earningsChart" in response_text,
        }

        for element, found in elements_to_check.items():
            status = "✓" if found else "✗"
            print(f"  {status} {element}: {'Found' if found else 'Missing'}")

    # Test 4: Test API endpoints
    print("\n[TEST 4] Testing API endpoints...")

    api_endpoints = [
        "/deliverer/api/check-new-deliveries",
        "/deliverer/api/earnings-data",
        "/deliverer/api/toggle-availability",
    ]

    for endpoint in api_endpoints:
        try:
            if "toggle-availability" in endpoint:
                response = session.post(f"{BASE_URL}{endpoint}", json={"is_available": True})
            else:
                response = session.get(f"{BASE_URL}{endpoint}")

            print(f"  {endpoint}")
            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    Response: {data}")
                except:
                    print(f"    Response: {response.text[:100]}")
            else:
                print(f"    Error: {response.text[:200]}")

        except Exception as e:
            print(f"    ✗ Error: {str(e)}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_deliverer_dashboard()
