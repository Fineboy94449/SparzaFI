"""
Test Chat System Integration
- Verify chat buttons are connected
- Test chat widget route
- Test end-to-end chat flow
"""

import os
import sys
from firebase_config import initialize_firebase, get_firestore_db
from firebase_db import seller_service, get_user_service


def test_sellers_have_handles():
    """Test if sellers have handle field for chat"""
    print("\n" + "=" * 70)
    print("  TEST 1: SELLERS HAVE HANDLES")
    print("=" * 70)

    sellers = seller_service.get_all_sellers(limit=5)

    if not sellers:
        print("\n  ⚠️  No sellers found in database")
        return False

    sellers_with_handles = 0
    for seller in sellers:
        if 'handle' in seller and seller['handle']:
            sellers_with_handles += 1
            print(f"  ✅ {seller.get('name', 'Unknown')}: handle='{seller['handle']}'")
        else:
            print(f"  ❌ {seller.get('name', 'Unknown')}: NO HANDLE")

    print(f"\n  Found {sellers_with_handles}/{len(sellers)} sellers with handles")

    return sellers_with_handles == len(sellers)


def test_chat_widget_route():
    """Test if chat widget route is accessible"""
    print("\n" + "=" * 70)
    print("  TEST 2: CHAT WIDGET ROUTE")
    print("=" * 70)

    import requests

    # Get a seller with handle
    sellers = seller_service.get_all_sellers(limit=1)

    if not sellers or 'handle' not in sellers[0]:
        print("\n  ⚠️  No sellers with handles found")
        return False

    seller_handle = sellers[0]['handle']

    # Test chat widget route (should return 401 without login)
    response = requests.get(f'http://localhost:5000/chat/widget/{seller_handle}')

    print(f"\n  Testing: /chat/widget/{seller_handle}")
    print(f"  Status: HTTP {response.status_code}")

    if response.status_code == 401:
        print(f"  ✅ Route exists and requires authentication")
        return True
    elif response.status_code == 200:
        print(f"  ⚠️  Route accessible without auth (unexpected)")
        return True
    else:
        print(f"  ❌ Route not found or error")
        return False


def test_chat_routes_exist():
    """Test if all required chat routes exist"""
    print("\n" + "=" * 70)
    print("  TEST 3: CHAT ROUTES EXIST")
    print("=" * 70)

    import requests

    routes_to_test = [
        ('/chat/send', 'POST', [401, 405]),  # POST only, requires auth
        ('/chat/unread-count', 'GET', [200, 401]),  # May work without auth or require it
        ('/chat/conversations', 'GET', [200, 401]),  # May work without auth or require it
    ]

    all_exist = True

    for route, method, expected_codes in routes_to_test:
        try:
            if method == 'GET':
                response = requests.get(f'http://localhost:5000{route}')
            else:
                response = requests.post(f'http://localhost:5000{route}')

            status_ok = response.status_code in expected_codes

            status_icon = "✅" if status_ok else "❌"
            print(f"  {status_icon} {method:6} {route:30} → HTTP {response.status_code}")

            if not status_ok:
                all_exist = False

        except Exception as e:
            print(f"  ❌ {method:6} {route:30} → ERROR: {str(e)[:50]}")
            all_exist = False

    return all_exist


def test_marketplace_routes():
    """Test if marketplace routes are accessible"""
    print("\n" + "=" * 70)
    print("  TEST 4: MARKETPLACE ROUTES")
    print("=" * 70)

    import requests

    routes = [
        '/marketplace/',
        '/marketplace/cart',
    ]

    all_ok = True

    for route in routes:
        response = requests.get(f'http://localhost:5000{route}')
        status_ok = response.status_code == 200

        status_icon = "✅" if status_ok else "❌"
        print(f"  {status_icon} GET {route:30} → HTTP {response.status_code}")

        if not status_ok:
            all_ok = False

    return all_ok


def main():
    """Run all tests"""
    print("=" * 70)
    print("  SPARZAFI CHAT INTEGRATION TEST")
    print("=" * 70)

    # Initialize Firebase
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT', './firebase-service-account.json')
    initialize_firebase(service_account_path)

    results = {}

    # Run tests
    results['Sellers Have Handles'] = test_sellers_have_handles()
    results['Chat Widget Route'] = test_chat_widget_route()
    results['Chat Routes Exist'] = test_chat_routes_exist()
    results['Marketplace Routes'] = test_marketplace_routes()

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")

    total = len(results)
    passed = sum(1 for result in results.values() if result)

    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n🎉 ALL CHAT INTEGRATION TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) need attention")
        return 1


if __name__ == '__main__':
    sys.exit(main())
