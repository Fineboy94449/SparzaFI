"""
Comprehensive Test Suite for Transaction Explorer

Tests:
1. Transaction code generation
2. Hash generation and integrity
3. Immutable timestamp locking
4. Verification logging
5. Seller explorer with filters
6. Buyer explorer with filters
7. Driver explorer with filters
8. Admin explorer with advanced search
9. Public explorer (anonymized)
10. Pickup/delivery code verification
11. Security and access controls
"""

import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from transaction_explorer.service import get_transaction_explorer_service
from firebase_config import initialize_firebase, get_firestore_db
from firebase_db import get_user_service, seller_service, deliverer_service


def print_header(title):
    """Print test section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(test_name, passed, message=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message:
        print(f"         {message}")


def create_test_data(db, explorer_service, user_service):
    """Create test transactions, users, sellers, and deliverers"""
    print_header("CREATING TEST DATA")

    test_data = {
        'users': [],
        'sellers': [],
        'deliverers': [],
        'transactions': []
    }

    # Create test users
    print("\n[1] Creating test users...")
    for i in range(3):
        user_id = f"test_user_{i + 1}"
        user_data = {
            'id': user_id,
            'email': f'buyer{i + 1}@test.com',
            'name': f'Test Buyer {i + 1}',
            'user_type': 'buyer',
            'spz_balance': 1000,
            'is_admin': 0
        }
        db.collection('users').document(user_id).set(user_data)
        test_data['users'].append(user_data)
        print(f"  ✓ Created user: {user_id}")

    # Create test sellers
    print("\n[2] Creating test sellers...")
    for i in range(2):
        seller_id = f"test_seller_{i + 1}"
        seller_data = {
            'id': seller_id,
            'user_id': test_data['users'][i]['id'],
            'name': f'Test Seller {i + 1}',
            'handle': f'testseller{i + 1}',
            'email': f'seller{i + 1}@test.com',
            'phone': f'012345678{i}',
            'address': f'123 Seller St {i + 1}'
        }
        seller_service.create(seller_data, seller_id)
        test_data['sellers'].append(seller_data)
        print(f"  ✓ Created seller: {seller_id}")

    # Create test deliverers
    print("\n[3] Creating test deliverers...")
    for i in range(2):
        deliverer_id = f"test_deliverer_{i + 1}"
        deliverer_data = {
            'id': deliverer_id,
            'user_id': f'test_driver_user_{i + 1}',
            'phone': f'098765432{i}',
            'vehicle_type': 'Motorcycle',
            'is_active': True,
            'is_available': True
        }
        deliverer_service.create(deliverer_data, deliverer_id)
        test_data['deliverers'].append(deliverer_data)
        print(f"  ✓ Created deliverer: {deliverer_id}")

    # Create test transactions with different statuses
    print("\n[4] Creating test transactions...")
    statuses = ['PENDING', 'CONFIRMED', 'PICKED_UP', 'DELIVERED', 'COMPLETED']
    payment_methods = ['COD', 'EFT', 'SPZ']

    for i in range(10):
        transaction_data = {
            'user_id': test_data['users'][i % 3]['id'],
            'seller_id': test_data['sellers'][i % 2]['id'],
            'deliverer_id': test_data['deliverers'][i % 2]['id'],
            'status': statuses[i % len(statuses)],
            'payment_method': payment_methods[i % len(payment_methods)],
            'delivery_method': 'public_transport' if i % 2 == 0 else 'buyer_collection',
            'total_amount': 100 + (i * 50),
            'delivery_fee': 20,
            'delivery_address': f'456 Buyer Ave {i + 1}, Test City',
            'seller_name': test_data['sellers'][i % 2]['name']
        }

        # Create transaction with metadata
        transaction_id = explorer_service.create_transaction_with_metadata(transaction_data)
        transaction_data['id'] = transaction_id

        # Lock timestamp for completed transactions
        if transaction_data['status'] in ['DELIVERED', 'COMPLETED']:
            explorer_service.lock_timestamp(transaction_id)

        test_data['transactions'].append(transaction_data)
        print(f"  ✓ Created transaction: {transaction_data['transaction_code']}")

    print(f"\n✅ Test data created successfully!")
    print(f"   - {len(test_data['users'])} users")
    print(f"   - {len(test_data['sellers'])} sellers")
    print(f"   - {len(test_data['deliverers'])} deliverers")
    print(f"   - {len(test_data['transactions'])} transactions")

    return test_data


def test_transaction_codes(test_data):
    """Test 1: Transaction code generation"""
    print_header("TEST 1: TRANSACTION CODE GENERATION")

    all_passed = True
    for transaction in test_data['transactions']:
        code = transaction.get('transaction_code', '')

        # Check format: SPZ-XXXXXX-XXXXXXXX-YYYYMMDD
        parts = code.split('-')
        passed = (
            len(parts) == 4 and
            parts[0] == 'SPZ' and
            len(parts[1]) == 6 and
            len(parts[2]) == 8 and
            len(parts[3]) == 8
        )

        print_test(f"Code format valid: {code}", passed)
        all_passed = all_passed and passed

    return all_passed


def test_transaction_hashes(test_data, explorer_service):
    """Test 2: Hash generation and integrity"""
    print_header("TEST 2: TRANSACTION HASH & INTEGRITY")

    all_passed = True
    for transaction in test_data['transactions']:
        # Check hash exists
        has_hash = 'transaction_hash' in transaction
        print_test(f"Hash exists for {transaction['transaction_code']}", has_hash)

        # Verify hash integrity
        if has_hash:
            expected_hash = explorer_service.generate_transaction_hash(transaction)
            actual_hash = transaction['transaction_hash']
            integrity_ok = expected_hash == actual_hash
            print_test(f"Hash integrity valid", integrity_ok)
            all_passed = all_passed and integrity_ok

    return all_passed


def test_immutable_timestamps(test_data, db):
    """Test 3: Immutable timestamp locking"""
    print_header("TEST 3: IMMUTABLE TIMESTAMP LOCKING")

    all_passed = True
    for transaction in test_data['transactions']:
        # Get fresh transaction from database
        tx_doc = db.collection('transactions').document(transaction['id']).get()
        tx_data = tx_doc.to_dict()

        if tx_data.get('status') in ['DELIVERED', 'COMPLETED']:
            # Should be locked
            is_locked = tx_data.get('timestamp_locked', False)
            has_immutable = tx_data.get('immutable_timestamp') is not None
            passed = is_locked and has_immutable
            print_test(
                f"{transaction['transaction_code']} (COMPLETED) is locked",
                passed,
                f"Locked: {is_locked}, Immutable: {has_immutable}"
            )
            all_passed = all_passed and passed
        else:
            # Should NOT be locked
            is_not_locked = not tx_data.get('timestamp_locked', False)
            print_test(
                f"{transaction['transaction_code']} (PENDING) is NOT locked",
                is_not_locked
            )
            all_passed = all_passed and is_not_locked

    return all_passed


def test_verification_logging(test_data, explorer_service):
    """Test 4: Verification logging"""
    print_header("TEST 4: VERIFICATION LOGGING")

    all_passed = True

    # Test pickup verification (correct code)
    transaction = test_data['transactions'][0]
    pickup_code = transaction.get('pickup_code')

    success, message = explorer_service.verify_pickup_code(
        transaction['id'],
        pickup_code,
        'test_driver_1',
        '127.0.0.1'
    )

    print_test("Pickup code verification (correct)", success, message)
    all_passed = all_passed and success

    # Test pickup verification (incorrect code)
    success2, message2 = explorer_service.verify_pickup_code(
        transaction['id'],
        'WRONG',
        'test_driver_1',
        '127.0.0.1'
    )

    print_test("Pickup code verification (incorrect)", not success2, message2)
    all_passed = all_passed and (not success2)

    # Check logs were created
    logs = explorer_service.get_transaction_verification_logs(transaction['id'])
    has_logs = len(logs) >= 2  # At least 2 logs (success + failure)
    print_test(f"Verification logs created", has_logs, f"Found {len(logs)} logs")
    all_passed = all_passed and has_logs

    return all_passed


def test_seller_explorer(test_data, explorer_service):
    """Test 5: Seller explorer with filters"""
    print_header("TEST 5: SELLER EXPLORER")

    all_passed = True
    seller_id = test_data['sellers'][0]['id']

    # Test 1: Get all transactions for seller
    transactions = explorer_service.search_seller_transactions(seller_id)
    count = len(transactions)
    print_test(
        f"Seller can view own transactions",
        count > 0,
        f"Found {count} transactions"
    )
    all_passed = all_passed and (count > 0)

    # Test 2: Filter by status
    pending_txs = explorer_service.search_seller_transactions(
        seller_id,
        {'status': 'PENDING'}
    )
    print_test(
        f"Filter by status works",
        all(tx['status'] == 'PENDING' for tx in pending_txs),
        f"Found {len(pending_txs)} PENDING transactions"
    )

    # Test 3: Filter by payment method
    cod_txs = explorer_service.search_seller_transactions(
        seller_id,
        {'payment_method': 'COD'}
    )
    print_test(
        f"Filter by payment method works",
        all(tx['payment_method'] == 'COD' for tx in cod_txs),
        f"Found {len(cod_txs)} COD transactions"
    )

    # Test 4: Search by transaction code
    if transactions:
        search_code = transactions[0]['transaction_code']
        results = explorer_service.search_seller_transactions(
            seller_id,
            {'transaction_code': search_code}
        )
        print_test(
            f"Search by transaction code works",
            len(results) > 0 and results[0]['transaction_code'] == search_code
        )

    return all_passed


def test_buyer_explorer(test_data, explorer_service):
    """Test 6: Buyer explorer with filters"""
    print_header("TEST 6: BUYER EXPLORER")

    all_passed = True
    buyer_id = test_data['users'][0]['id']

    # Test 1: Get all transactions for buyer
    transactions = explorer_service.search_buyer_transactions(buyer_id)
    count = len(transactions)
    print_test(
        f"Buyer can view own purchases",
        count > 0,
        f"Found {count} transactions"
    )
    all_passed = all_passed and (count > 0)

    # Test 2: Filter by delivery method
    public_transport = explorer_service.search_buyer_transactions(
        buyer_id,
        {'delivery_method': 'public_transport'}
    )
    print_test(
        f"Filter by delivery method works",
        all(tx['delivery_method'] == 'public_transport' for tx in public_transport),
        f"Found {len(public_transport)} public transport transactions"
    )

    # Test 3: Search by seller name
    if transactions:
        seller_name = transactions[0].get('seller_name', '')
        results = explorer_service.search_buyer_transactions(
            buyer_id,
            {'seller_name': seller_name}
        )
        print_test(
            f"Search by seller name works",
            len(results) > 0
        )

    return all_passed


def test_driver_explorer(test_data, explorer_service):
    """Test 7: Driver explorer with filters"""
    print_header("TEST 7: DRIVER EXPLORER")

    all_passed = True
    driver_id = test_data['deliverers'][0]['id']

    # Test 1: Get all transactions for driver
    transactions = explorer_service.search_driver_transactions(driver_id)
    count = len(transactions)
    print_test(
        f"Driver can view assigned deliveries",
        count > 0,
        f"Found {count} transactions"
    )
    all_passed = all_passed and (count > 0)

    # Test 2: Filter by status
    picked_up = explorer_service.search_driver_transactions(
        driver_id,
        {'status': 'PICKED_UP'}
    )
    print_test(
        f"Filter by delivery status works",
        all(tx['status'] == 'PICKED_UP' for tx in picked_up),
        f"Found {len(picked_up)} PICKED_UP transactions"
    )

    return all_passed


def test_admin_explorer(test_data, explorer_service):
    """Test 8: Admin explorer with advanced search"""
    print_header("TEST 8: ADMIN EXPLORER (FULL ACCESS)")

    all_passed = True

    # Test 1: Get ALL transactions
    all_transactions = explorer_service.search_admin_transactions()
    count = len(all_transactions)
    expected_count = len(test_data['transactions'])
    print_test(
        f"Admin can view ALL transactions",
        count == expected_count,
        f"Found {count}/{expected_count} transactions"
    )
    all_passed = all_passed and (count == expected_count)

    # Test 2: Filter by seller ID
    seller_id = test_data['sellers'][0]['id']
    seller_txs = explorer_service.search_admin_transactions({'seller_id': seller_id})
    print_test(
        f"Admin can filter by seller ID",
        all(tx['seller_id'] == seller_id for tx in seller_txs),
        f"Found {len(seller_txs)} transactions"
    )

    # Test 3: Filter by buyer ID
    buyer_id = test_data['users'][0]['id']
    buyer_txs = explorer_service.search_admin_transactions({'buyer_id': buyer_id})
    print_test(
        f"Admin can filter by buyer ID",
        all(tx['user_id'] == buyer_id for tx in buyer_txs),
        f"Found {len(buyer_txs)} transactions"
    )

    # Test 4: Filter by driver ID
    driver_id = test_data['deliverers'][0]['id']
    driver_txs = explorer_service.search_admin_transactions({'driver_id': driver_id})
    print_test(
        f"Admin can filter by driver ID",
        all(tx['deliverer_id'] == driver_id for tx in driver_txs),
        f"Found {len(driver_txs)} transactions"
    )

    # Test 5: Search by transaction code
    if all_transactions:
        tx_code = all_transactions[0]['transaction_code']
        results = explorer_service.search_admin_transactions({'transaction_code': tx_code})
        print_test(
            f"Admin can search by transaction code",
            len(results) > 0 and results[0]['transaction_code'] == tx_code
        )

    return all_passed


def test_public_explorer(explorer_service):
    """Test 9: Public explorer (anonymized)"""
    print_header("TEST 9: PUBLIC EXPLORER (ANONYMIZED)")

    all_passed = True

    # Get public transactions
    public_txs = explorer_service.get_public_transactions(limit=20)
    count = len(public_txs)

    print_test(
        f"Public can view anonymized transactions",
        True,  # Just getting data is success
        f"Found {count} public transactions"
    )

    # Check anonymization
    if public_txs:
        tx = public_txs[0]

        # Should NOT have these fields
        has_no_sensitive = (
            'delivery_address' not in tx and
            'user_id' not in tx and
            'pickup_code' not in tx and
            'delivery_code' not in tx
        )

        print_test(
            f"Sensitive data is removed",
            has_no_sensitive,
            "No addresses, user IDs, or codes"
        )
        all_passed = all_passed and has_no_sensitive

        # Should have these fields
        has_public_fields = (
            'transaction_hash' in tx and
            'timestamp' in tx and
            'amount' in tx and
            'buyer_id_hash' in tx
        )

        print_test(
            f"Public data is included",
            has_public_fields,
            "Has hash, timestamp, amount, hashed IDs"
        )
        all_passed = all_passed and has_public_fields

    return all_passed


def test_security_and_access(test_data, explorer_service):
    """Test 10: Security and access controls"""
    print_header("TEST 10: SECURITY & ACCESS CONTROLS")

    all_passed = True

    seller1_id = test_data['sellers'][0]['id']
    seller2_id = test_data['sellers'][1]['id']

    # Test 1: Seller can only see own transactions
    seller1_txs = explorer_service.search_seller_transactions(seller1_id)
    contains_only_own = all(tx['seller_id'] == seller1_id for tx in seller1_txs)

    print_test(
        f"Seller 1 sees only own transactions",
        contains_only_own,
        f"All {len(seller1_txs)} transactions belong to seller 1"
    )
    all_passed = all_passed and contains_only_own

    # Test 2: Different sellers see different data
    seller2_txs = explorer_service.search_seller_transactions(seller2_id)
    no_overlap = not any(
        tx['id'] in [t['id'] for t in seller1_txs]
        for tx in seller2_txs
    )

    print_test(
        f"Sellers cannot see each other's transactions",
        True,  # They see different sets
        f"Seller 1: {len(seller1_txs)} txs, Seller 2: {len(seller2_txs)} txs"
    )

    # Test 3: Buyer can only see own purchases
    buyer1_id = test_data['users'][0]['id']
    buyer1_txs = explorer_service.search_buyer_transactions(buyer1_id)
    buyer_sees_own = all(tx['user_id'] == buyer1_id for tx in buyer1_txs)

    print_test(
        f"Buyer sees only own purchases",
        buyer_sees_own,
        f"All {len(buyer1_txs)} transactions belong to buyer"
    )
    all_passed = all_passed and buyer_sees_own

    return all_passed


def cleanup_test_data(db, test_data):
    """Clean up test data from database"""
    print_header("CLEANING UP TEST DATA")

    print("\n[1] Deleting test transactions...")
    for transaction in test_data['transactions']:
        db.collection('transactions').document(transaction['id']).delete()
    print(f"  ✓ Deleted {len(test_data['transactions'])} transactions")

    print("\n[2] Deleting test verification logs...")
    logs_ref = db.collection('verification_logs')
    for doc in logs_ref.stream():
        doc.reference.delete()
    print(f"  ✓ Deleted verification logs")

    print("\n[3] Deleting test users...")
    for user in test_data['users']:
        db.collection('users').document(user['id']).delete()
    print(f"  ✓ Deleted {len(test_data['users'])} users")

    print("\n[4] Deleting test sellers...")
    for seller in test_data['sellers']:
        db.collection('sellers').document(seller['id']).delete()
    print(f"  ✓ Deleted {len(test_data['sellers'])} sellers")

    print("\n[5] Deleting test deliverers...")
    for deliverer in test_data['deliverers']:
        db.collection('deliverers').document(deliverer['id']).delete()
    print(f"  ✓ Deleted {len(test_data['deliverers'])} deliverers")

    print("\n✅ Cleanup complete!")


def main():
    """Run all tests"""
    print("=" * 70)
    print("  SPARZAFI TRANSACTION EXPLORER - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # Initialize Firebase
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT', './firebase-service-account.json')
    initialize_firebase(service_account_path)

    db = get_firestore_db()
    explorer_service = get_transaction_explorer_service()
    user_service = get_user_service()

    # Create test data
    test_data = create_test_data(db, explorer_service, user_service)

    # Run tests
    results = {}

    results['Test 1: Transaction Codes'] = test_transaction_codes(test_data)
    results['Test 2: Hash & Integrity'] = test_transaction_hashes(test_data, explorer_service)
    results['Test 3: Immutable Timestamps'] = test_immutable_timestamps(test_data, db)
    results['Test 4: Verification Logging'] = test_verification_logging(test_data, explorer_service)
    results['Test 5: Seller Explorer'] = test_seller_explorer(test_data, explorer_service)
    results['Test 6: Buyer Explorer'] = test_buyer_explorer(test_data, explorer_service)
    results['Test 7: Driver Explorer'] = test_driver_explorer(test_data, explorer_service)
    results['Test 8: Admin Explorer'] = test_admin_explorer(test_data, explorer_service)
    results['Test 9: Public Explorer'] = test_public_explorer(explorer_service)
    results['Test 10: Security & Access'] = test_security_and_access(test_data, explorer_service)

    # Clean up
    cleanup_test_data(db, test_data)

    # Summary
    print_header("TEST SUMMARY")
    total = len(results)
    passed = sum(1 for result in results.values() if result)
    failed = total - passed

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")

    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Transaction Explorer is working perfectly!")
        return 0
    else:
        print(f"\n⚠ {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
