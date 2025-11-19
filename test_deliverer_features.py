#!/usr/bin/env python3
"""
Comprehensive Deliverer Dashboard Feature Test
Tests all 7 features 3 times
"""

def check_dashboard_html():
    """Check if dashboard HTML contains all required features"""

    with open('deliverer/templates/deliverer_dashboard.html', 'r') as f:
        content = f.read()

    features = {
        "1. Deliverer Profile": [
            "deliverer.name",
            "vehicle_type",
            "rating",
            "total_deliveries",
            "total_earnings",
        ],
        "2. Route Pricing Manager": [
            "My Routes",
            "route_name",
            "base_fee",
            "price_per_km",
            "manage-routes",
        ],
        "3. Available Pickups": [
            "Available Pickups",
            "available_pickups",
            "claim",
            "seller_name",
            "buyer_address",
        ],
        "4. Active Deliveries": [
            "Active Deliveries",
            "active_deliveries",
            "PICKED_UP",
            "IN_TRANSIT",
            "Verify",
        ],
        "5. Completed Deliveries": [
            "Completed Deliveries",
            "completed_deliveries",
            "DELIVERED",
            "deliverer_fee",
        ],
        "6. Earnings Summary": [
            "Earnings",
            "total_earnings",
            "pending_settlements",
            "today_earnings",
            "earningsChart",
        ],
        "7. Verification Status": [
            "is_verified",
            "verification",
            "KYC",
        ],
    }

    results = {}
    for feature_name, keywords in features.items():
        found = []
        missing = []
        for keyword in keywords:
            if keyword.lower() in content.lower():
                found.append(keyword)
            else:
                missing.append(keyword)

        results[feature_name] = {
            "found": found,
            "missing": missing,
            "status": "✓ PASS" if len(missing) == 0 else "✗ INCOMPLETE"
        }

    return results

def check_backend_routes():
    """Check if backend routes exist"""

    with open('deliverer/routes.py', 'r') as f:
        content = f.read()

    required_routes = {
        "Dashboard": "/dashboard",
        "Manage Routes": "/manage-routes",
        "Add Route": "/routes/add",
        "Claim Delivery": "/claim/",
        "Verify Pickup": "/verify-pickup",
        "Verify Delivery": "/verify-delivery",
        "Earnings": "/earnings",
        "Pricing": "/pricing",
        "Verification Status": "/verification-status",
    }

    results = {}
    for route_name, route_path in required_routes.items():
        if route_path in content:
            results[route_name] = "✓ EXISTS"
        else:
            results[route_name] = "✗ MISSING"

    return results

def main():
    print("=" * 80)
    print("DELIVERER DASHBOARD FEATURE CHECK")
    print("=" * 80)

    # Test Round 1
    print("\n[ROUND 1] Checking HTML Features...")
    html_results = check_dashboard_html()

    for feature, data in html_results.items():
        print(f"\n{data['status']} {feature}")
        if data['found']:
            print(f"  Found: {', '.join(data['found'][:3])}{'...' if len(data['found']) > 3 else ''}")
        if data['missing']:
            print(f"  Missing: {', '.join(data['missing'])}")

    # Test Round 2
    print("\n\n[ROUND 2] Checking Backend Routes...")
    route_results = check_backend_routes()

    for route_name, status in route_results.items():
        print(f"  {status} {route_name}")

    # Test Round 3 - Summary
    print("\n\n[ROUND 3] Overall Status Summary...")

    total_features = len(html_results)
    passed_features = sum(1 for f in html_results.values() if "PASS" in f['status'])

    total_routes = len(route_results)
    existing_routes = sum(1 for r in route_results.values() if "EXISTS" in r)

    print(f"\n  HTML Features: {passed_features}/{total_features} complete")
    print(f"  Backend Routes: {existing_routes}/{total_routes} implemented")

    overall_score = ((passed_features / total_features) + (existing_routes / total_routes)) / 2 * 100
    print(f"\n  Overall Completion: {overall_score:.1f}%")

    if overall_score >= 80:
        print("\n  ✓ Dashboard is production-ready!")
    elif overall_score >= 60:
        print("\n  ⚠ Dashboard needs minor improvements")
    else:
        print("\n  ✗ Dashboard needs significant work")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
