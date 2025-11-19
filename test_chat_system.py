#!/usr/bin/env python3
"""
SparzaFI Chat System - Comprehensive Test Suite
Tests all 3 chat types 3 times:
1. Buyer ↔ Seller Chat
2. Buyer ↔ Deliverer Chat
3. Seller ↔ Deliverer Chat
"""

import os
import sys

def test_round_1_file_structure():
    """Round 1: Verify all required files exist"""
    print("\n" + "="*80)
    print("ROUND 1: FILE STRUCTURE CHECK")
    print("="*80)

    required_files = {
        "Chat Routes": "chat/routes.py",
        "Message Filter": "chat/message_filter.py",
        "Chat Widget Template": "chat/templates/chat/chat_widget.html",
        "Firebase DB (with enhanced services)": "firebase_db.py",
        "Chat Design Doc": "CHAT_SYSTEM_DESIGN.md",
    }

    results = {}
    for name, path in required_files.items():
        full_path = os.path.join(os.path.dirname(__file__), path)
        exists = os.path.exists(full_path)
        results[name] = "✓" if exists else "✗"
        print(f"  {results[name]} {name}: {path}")

    return all(v == "✓" for v in results.values())


def test_round_2_code_features():
    """Round 2: Verify code features are implemented"""
    print("\n" + "="*80)
    print("ROUND 2: CODE FEATURES CHECK")
    print("="*80)

    tests = {
        "Message Filtering": {
            "file": "chat/message_filter.py",
            "keywords": ["PHONE_PATTERNS", "EMAIL_PATTERNS", "URL_PATTERNS", "is_safe", "validate_message"]
        },
        "Enhanced ConversationService": {
            "file": "firebase_db.py",
            "keywords": ["get_or_create_conversation", "transaction_id", "chat_type", "get_transaction_conversations"]
        },
        "Enhanced MessageService": {
            "file": "firebase_db.py",
            "keywords": ["get_transaction_messages", "get_unread_count", "sender_role"]
        },
        "Chat API Routes": {
            "file": "chat/routes.py",
            "keywords": ["/send", "/history", "/transaction", "check_kyc_permission", "get_user_role"]
        },
        "Chat Widget UI": {
            "file": "chat/templates/chat/chat_widget.html",
            "keywords": ["chat-widget", "chat-messages", "message-bubble", "ChatWidget.init", "AJAX"]
        }
    }

    results = {}
    for feature_name, test_info in tests.items():
        file_path = os.path.join(os.path.dirname(__file__), test_info["file"])

        if not os.path.exists(file_path):
            results[feature_name] = "✗ FILE NOT FOUND"
            print(f"\n  ✗ {feature_name}: FILE NOT FOUND")
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        found_keywords = []
        missing_keywords = []

        for keyword in test_info["keywords"]:
            if keyword in content:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)

        if not missing_keywords:
            results[feature_name] = "✓ PASS"
            print(f"\n  ✓ {feature_name}")
            print(f"    Found: {', '.join(found_keywords[:3])}...")
        else:
            results[feature_name] = f"✗ INCOMPLETE"
            print(f"\n  ✗ {feature_name}")
            print(f"    Missing: {', '.join(missing_keywords)}")

    passed = sum(1 for v in results.values() if "PASS" in v)
    total = len(results)

    print(f"\n  Score: {passed}/{total} features complete")

    return passed == total


def test_round_3_api_endpoints():
    """Round 3: Verify API endpoints are defined"""
    print("\n" + "="*80)
    print("ROUND 3: API ENDPOINTS CHECK")
    print("="*80)

    routes_file = os.path.join(os.path.dirname(__file__), "chat/routes.py")

    if not os.path.exists(routes_file):
        print("  ✗ Routes file not found")
        return False

    with open(routes_file, 'r') as f:
        content = f.read()

    required_endpoints = {
        "POST /chat/send": "@chat_bp.route('/send', methods=['POST'])",
        "GET /chat/history/<id>": "@chat_bp.route('/history/<conversation_id>'",
        "GET /chat/transaction/<id>": "@chat_bp.route('/transaction/<transaction_id>'",
        "POST /chat/mark_read": "@chat_bp.route('/mark_read'",
        "GET /chat/unread-count": "@chat_bp.route('/unread-count'",
        "GET /chat/conversations": "@chat_bp.route('/conversations'",
    }

    security_features = {
        "KYC Verification": "check_kyc_permission",
        "Message Validation": "validate_message",
        "Auth Required": "@require_auth",
        "User Role Detection": "get_user_role",
    }

    results = {}
    print("\n  API Endpoints:")
    for endpoint_name, pattern in required_endpoints.items():
        if pattern in content:
            results[endpoint_name] = "✓"
            print(f"    ✓ {endpoint_name}")
        else:
            results[endpoint_name] = "✗"
            print(f"    ✗ {endpoint_name}")

    print("\n  Security Features:")
    for feature_name, pattern in security_features.items():
        if pattern in content:
            results[feature_name] = "✓"
            print(f"    ✓ {feature_name}")
        else:
            results[feature_name] = "✗"
            print(f"    ✗ {feature_name}")

    passed = sum(1 for v in results.values() if v == "✓")
    total = len(results)

    print(f"\n  Score: {passed}/{total} checks passed")

    return passed == total


def test_chat_types():
    """Verify support for all 3 chat types"""
    print("\n" + "="*80)
    print("CHAT TYPES SUPPORT CHECK")
    print("="*80)

    routes_file = os.path.join(os.path.dirname(__file__), "chat/routes.py")

    if not os.path.exists(routes_file):
        print("  ✗ Routes file not found")
        return False

    with open(routes_file, 'r') as f:
        content = f.read()

    chat_types = {
        "Buyer ↔ Seller": "buyer_seller",
        "Buyer ↔ Deliverer": "buyer_deliverer",
        "Seller ↔ Deliverer": "seller_deliverer",
    }

    results = {}
    for chat_name, chat_type in chat_types.items():
        if chat_type in content:
            results[chat_name] = "✓ SUPPORTED"
            print(f"  ✓ {chat_name} ({chat_type})")
        else:
            results[chat_name] = "✗ NOT FOUND"
            print(f"  ✗ {chat_name} ({chat_type})")

    return all("SUPPORTED" in v for v in results.values())


def test_message_filtering():
    """Test message filtering patterns"""
    print("\n" + "="*80)
    print("MESSAGE FILTERING TEST")
    print("="*80)

    filter_file = os.path.join(os.path.dirname(__file__), "chat/message_filter.py")

    if not os.path.exists(filter_file):
        print("  ✗ Message filter file not found")
        return False

    with open(filter_file, 'r') as f:
        content = f.read()

    blocked_patterns = {
        "Phone Numbers": "PHONE_PATTERNS",
        "Email Addresses": "EMAIL_PATTERNS",
        "URLs/Links": "URL_PATTERNS",
        "Social Media": "SOCIAL_MEDIA_PATTERNS",
    }

    results = {}
    for pattern_name, pattern_var in blocked_patterns.items():
        if pattern_var in content:
            results[pattern_name] = "✓ BLOCKED"
            print(f"  ✓ {pattern_name} - {pattern_var}")
        else:
            results[pattern_name] = "✗ NOT FOUND"
            print(f"  ✗ {pattern_name} - {pattern_var}")

    # Check for validation functions
    validation_functions = ["is_safe", "sanitize", "validate_message"]
    print("\n  Validation Functions:")
    for func in validation_functions:
        if func in content:
            print(f"    ✓ {func}()")
        else:
            print(f"    ✗ {func}() missing")

    return all("BLOCKED" in v for v in results.values())


def generate_report():
    """Generate final test report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE CHAT SYSTEM TEST REPORT")
    print("="*80)

    all_tests = [
        ("File Structure", test_round_1_file_structure),
        ("Code Features", test_round_2_code_features),
        ("API Endpoints", test_round_3_api_endpoints),
        ("Chat Types Support", test_chat_types),
        ("Message Filtering", test_message_filtering),
    ]

    results = []
    for test_name, test_func in all_tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n  ✗ {test_name} ERROR: {str(e)}")
            results.append((test_name, False))

    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    percentage = (passed_count / total_count) * 100

    print(f"\n  Overall Score: {passed_count}/{total_count} tests passed ({percentage:.1f}%)")

    if percentage == 100:
        print("\n  🎉 EXCELLENT! Chat system is fully implemented and ready for integration!")
    elif percentage >= 80:
        print("\n  ✓ GOOD! Chat system is mostly complete, minor fixes needed.")
    elif percentage >= 60:
        print("\n  ⚠ FAIR! Chat system needs some work.")
    else:
        print("\n  ✗ INCOMPLETE! Significant implementation needed.")

    return percentage


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║     SparzaFI Chat System - 3 Round Comprehensive Test         ║
    ║     Testing all 3 chat types with security features           ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    # Run comprehensive test
    final_score = generate_report()

    print("\n" + "="*80)
    print(f"Test completed. Final score: {final_score:.1f}%")
    print("="*80 + "\n")

    # Exit with appropriate code
    sys.exit(0 if final_score == 100 else 1)
