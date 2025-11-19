#!/usr/bin/env python3
"""Deep test of deliverer dashboard with proper login"""
import requests
from requests.sessions import Session

BASE_URL = "http://localhost:5000"
session = Session()

print("="*60)
print("DELIVERER DASHBOARD DEEP TEST")
print("="*60)

# Test 1: Login
print("\n[1] Login as deliverer...")
login_response = session.post(
    f"{BASE_URL}/user/login",
    data={
        "email": "sipho.driver@sparzafi.com",
        "password": "driverpass"
    },
    allow_redirects=True
)
print(f"  Login status: {login_response.status_code}")
if login_response.status_code != 200:
    print(f"  Login failed. Trying alternative login...")
    # Try POST to root with credentials
    login_response = session.post(
        f"{BASE_URL}/login",
        data={
            "email": "sipho.driver@sparzafi.com",
            "password": "driverpass"
        },
        allow_redirects=True
    )
    print(f"  Alternative login status: {login_response.status_code}")

# Test 2: Access dashboard
print("\n[2] Access deliverer dashboard...")
dashboard_response = session.get(f"{BASE_URL}/deliverer/dashboard", allow_redirects=False)
print(f"  Dashboard status: {dashboard_response.status_code}")

if dashboard_response.status_code == 302:
    redirect_url = dashboard_response.headers.get('Location', '')
    print(f"  Redirected to: {redirect_url}")

    # Follow redirect if it's to setup
    if 'setup' in redirect_url:
        print("\n[3] Following redirect to setup...")
        setup_response = session.get(f"{BASE_URL}{redirect_url}", allow_redirects=False)
        print(f"  Setup page status: {setup_response.status_code}")

        if setup_response.status_code == 500:
            print(f"  ERROR: Setup page returned 500")
            print(f"  Response: {setup_response.text[:500]}")
        elif setup_response.status_code == 200:
            print(f"  ✓ Setup page loaded successfully")

elif dashboard_response.status_code == 500:
    print(f"  ERROR: Dashboard returned 500")
    print(f"  Error content: {dashboard_response.text[:1000]}")

elif dashboard_response.status_code == 200:
    print(f"  ✓ Dashboard loaded successfully!")

    # Check for specific elements
    content = dashboard_response.text
    checks = {
        "Performance Metrics": "📈 Performance Metrics" in content,
        "Active Deliveries": "📦 Active Deliveries" in content,
        "Available Pickups": "🚀 Available Pickups" in content,
        "Charts (earningsChart)": "earningsChart" in content,
        "Verification Modal": "verificationModal" in content,
    }

    print("\n[4] Dashboard element checks:")
    for element, found in checks.items():
        status = "✓" if found else "✗"
        print(f"  {status} {element}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
