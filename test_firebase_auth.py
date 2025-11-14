#!/usr/bin/env python3
"""
Firebase Authentication Test Script for SparzaFI
Tests the migrated authentication and shared utilities functions

Usage:
    python test_firebase_auth.py
"""

import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_firebase_connection():
    """Test 1: Firebase connection"""
    print("\n" + "="*60)
    print("TEST 1: Firebase Connection")
    print("="*60)

    try:
        from firebase_config import initialize_firebase, get_firestore_db

        # Initialize Firebase
        initialize_firebase()
        print("✓ Firebase initialized successfully")

        # Get database client
        db = get_firestore_db()
        print(f"✓ Firestore client obtained: {type(db)}")

        # Test connection by listing collections
        collections = list(db.collections())
        print(f"✓ Connected to Firestore - {len(collections)} collections found")

        return True

    except Exception as e:
        print(f"✗ Firebase connection failed: {e}")
        return False


def test_user_service():
    """Test 2: User service operations"""
    print("\n" + "="*60)
    print("TEST 2: User Service Operations")
    print("="*60)

    try:
        from firebase_db import get_user_service
        import secrets

        user_service = get_user_service()
        print("✓ User service initialized")

        # Create test user
        test_email = f"test_{secrets.token_hex(4)}@sparzafi.test"
        test_user_id = str(uuid.uuid4())

        user_data = {
            'email': test_email,
            'password_hash': 'test_hash_123',
            'full_name': 'Test User',
            'user_type': 'buyer',
            'spz_balance': 1500.0,
            'email_verified': True,
            'phone_verified': False,
            'status': 'active',
            'kyc_status': 'pending'
        }

        user_service.create(user_data, doc_id=test_user_id)
        print(f"✓ Created test user: {test_email}")

        # Test get by ID
        user = user_service.get(test_user_id)
        assert user is not None
        assert user['email'] == test_email
        print(f"✓ Retrieved user by ID: {user['id']}")

        # Test get by email
        user_by_email = user_service.get_by_email(test_email)
        assert user_by_email is not None
        assert user_by_email['id'] == test_user_id
        print(f"✓ Retrieved user by email: {user_by_email['email']}")

        # Test update
        user_service.update(test_user_id, {'full_name': 'Updated Test User'})
        updated_user = user_service.get(test_user_id)
        assert updated_user['full_name'] == 'Updated Test User'
        print("✓ Updated user successfully")

        # Test balance update
        user_service.update_spz_balance(test_user_id, 500.0, 'credit')
        user_after_credit = user_service.get(test_user_id)
        assert user_after_credit['spz_balance'] == 2000.0
        print(f"✓ Updated SPZ balance: {user_after_credit['spz_balance']}")

        # Cleanup
        user_service.delete(test_user_id)
        print("✓ Deleted test user")

        return True

    except Exception as e:
        print(f"✗ User service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_shared_utils():
    """Test 3: Shared utilities functions"""
    print("\n" + "="*60)
    print("TEST 3: Shared Utilities Functions")
    print("="*60)

    try:
        from shared.utils import (
            hash_password, check_password,
            generate_referral_code, generate_verification_code,
            get_user_by_email, get_user_token_balance
        )
        from firebase_db import get_user_service
        import secrets

        # Test password hashing
        password = "test_password_123"
        hashed = hash_password(password)
        assert check_password(hashed, password)
        assert not check_password(hashed, "wrong_password")
        print("✓ Password hashing and verification works")

        # Test referral code generation
        ref_code = generate_referral_code()
        assert len(ref_code) == 8
        print(f"✓ Generated referral code: {ref_code}")

        # Test verification code generation
        ver_code = generate_verification_code()
        assert len(ver_code) == 6
        assert ver_code.isdigit()
        print(f"✓ Generated verification code: {ver_code}")

        # Test get user by email
        user_service = get_user_service()
        test_email = f"test_{secrets.token_hex(4)}@sparzafi.test"
        test_user_id = str(uuid.uuid4())

        user_service.create({
            'email': test_email,
            'password_hash': 'test',
            'user_type': 'buyer',
            'spz_balance': 1000.0,
            'email_verified': True,
            'status': 'active'
        }, doc_id=test_user_id)

        user = get_user_by_email(test_email)
        assert user is not None
        assert user['email'] == test_email
        print(f"✓ get_user_by_email works: {user['email']}")

        # Test get token balance
        balance = get_user_token_balance(test_user_id)
        assert balance == 1000.0
        print(f"✓ get_user_token_balance works: {balance} SPZ")

        # Cleanup
        user_service.delete(test_user_id)

        return True

    except Exception as e:
        print(f"✗ Shared utils test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_transfer():
    """Test 4: Token transfer functionality"""
    print("\n" + "="*60)
    print("TEST 4: Token Transfer (Atomic Transaction)")
    print("="*60)

    try:
        from shared.utils import transfer_tokens
        from firebase_db import get_user_service
        import secrets

        user_service = get_user_service()

        # Create two test users
        sender_email = f"sender_{secrets.token_hex(4)}@sparzafi.test"
        sender_id = str(uuid.uuid4())

        recipient_email = f"recipient_{secrets.token_hex(4)}@sparzafi.test"
        recipient_id = str(uuid.uuid4())

        user_service.create({
            'email': sender_email,
            'password_hash': 'test',
            'user_type': 'buyer',
            'spz_balance': 1000.0,
            'email_verified': True,
            'status': 'active'
        }, doc_id=sender_id)

        user_service.create({
            'email': recipient_email,
            'password_hash': 'test',
            'user_type': 'buyer',
            'spz_balance': 500.0,
            'email_verified': True,
            'status': 'active'
        }, doc_id=recipient_id)

        print(f"✓ Created sender ({sender_email}) with 1000 SPZ")
        print(f"✓ Created recipient ({recipient_email}) with 500 SPZ")

        # Test transfer
        result = transfer_tokens(sender_id, recipient_email, 300.0, "Test transfer")

        assert result['success']
        print(f"✓ Transfer successful: {result['reference_id']}")

        # Verify balances
        sender = user_service.get(sender_id)
        recipient = user_service.get(recipient_id)

        assert sender['spz_balance'] == 700.0
        assert recipient['spz_balance'] == 800.0

        print(f"✓ Sender balance: 1000 → {sender['spz_balance']} SPZ")
        print(f"✓ Recipient balance: 500 → {recipient['spz_balance']} SPZ")

        # Test insufficient balance
        result2 = transfer_tokens(sender_id, recipient_email, 10000.0)
        assert not result2['success']
        assert 'Insufficient balance' in result2['error']
        print("✓ Insufficient balance check works")

        # Cleanup
        user_service.delete(sender_id)
        user_service.delete(recipient_id)

        return True

    except Exception as e:
        print(f"✗ Token transfer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_flow():
    """Test 5: Complete authentication flow"""
    print("\n" + "="*60)
    print("TEST 5: Authentication Flow")
    print("="*60)

    try:
        from shared.utils import hash_password, check_password, get_user_by_email
        from firebase_db import get_user_service
        import secrets

        user_service = get_user_service()

        # Simulate registration
        email = f"auth_test_{secrets.token_hex(4)}@sparzafi.test"
        password = "secure_password_123"
        user_id = str(uuid.uuid4())

        hashed_pwd = hash_password(password)

        user_service.create({
            'email': email,
            'password_hash': hashed_pwd,
            'user_type': 'buyer',
            'spz_balance': 1500.0,
            'email_verified': False,
            'status': 'active',
            'verification_token': secrets.token_urlsafe(32)
        }, doc_id=user_id)

        print(f"✓ User registered: {email}")

        # Simulate login
        user = get_user_by_email(email)
        assert user is not None

        if check_password(user['password_hash'], password):
            print("✓ Login successful - password verified")
        else:
            print("✗ Login failed - password mismatch")
            return False

        # Simulate email verification
        user_service.update(user_id, {
            'email_verified': True,
            'verification_token': None
        })

        verified_user = user_service.get(user_id)
        assert verified_user['email_verified'] == True
        print("✓ Email verified")

        # Cleanup
        user_service.delete(user_id)

        return True

    except Exception as e:
        print(f"✗ Auth flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SparzaFI Firebase Authentication Test Suite")
    print("="*60)

    tests = [
        ("Firebase Connection", test_firebase_connection),
        ("User Service", test_user_service),
        ("Shared Utilities", test_shared_utils),
        ("Token Transfer", test_token_transfer),
        ("Auth Flow", test_auth_flow),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {test_name}")

    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! Firebase migration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
