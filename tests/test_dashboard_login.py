#!/usr/bin/env python3
"""Test deliverer dashboard with login"""
import requests
from requests.sessions import Session

session = Session()

# Login
print("Logging in as deliverer...")
response = session.post(
    "http://localhost:5000/user/login",
    data={"email": "sipho.driver@sparzafi.com", "password": "driverpass"},
    allow_redirects=True
)
print(f"Login status: {response.status_code}")

# Access dashboard
print("\nAccessing deliverer dashboard...")
response = session.get("http://localhost:5000/deliverer/dashboard")
print(f"Dashboard status: {response.status_code}")

if response.status_code != 200:
    print(f"\nError response:\n{response.text[:1000]}")
else:
    print("Dashboard loaded successfully!")
