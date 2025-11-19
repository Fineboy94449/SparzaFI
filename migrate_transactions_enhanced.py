"""
Migration script to add enhanced transaction fields

Adds:
- transaction_code (SPZ-XXXXXX-XXXXXXXX-YYYYMMDD)
- transaction_hash (integrity verification)
- immutable_timestamp (locked when completed)
- timestamp_locked (boolean)
- verification_logs (array)
- pickup_code and delivery_code
"""

import os
import sys
from datetime import datetime
from transaction_explorer_service import get_transaction_explorer_service
from firebase_config import initialize_firebase, get_firestore_db
from google.cloud import firestore


def migrate_existing_transactions():
    """
    Migrate all existing transactions to add enhanced fields
    """
    print("=" * 60)
    print("SPARZAFI TRANSACTION MIGRATION - ENHANCED EXPLORER")
    print("=" * 60)

    # Initialize Firebase
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT', './firebase-service-account.json')
    initialize_firebase(service_account_path)

    db = get_firestore_db()
    explorer_service = get_transaction_explorer_service()

    # Get all transactions
    print("\n[1] Fetching all transactions...")
    transactions_ref = db.collection('transactions')
    docs = transactions_ref.stream()

    transactions = []
    for doc in docs:
        transactions.append({**doc.to_dict(), 'id': doc.id})

    print(f"✓ Found {len(transactions)} transactions to migrate")

    if len(transactions) == 0:
        print("\n⚠ No transactions found. Exiting.")
        return

    # Process each transaction
    print("\n[2] Migrating transactions...")
    success_count = 0
    error_count = 0

    for idx, transaction in enumerate(transactions, 1):
        transaction_id = transaction['id']
        print(f"\n[{idx}/{len(transactions)}] Migrating transaction: {transaction_id}")

        try:
            # Get transaction ref
            transaction_ref = transactions_ref.document(transaction_id)

            # Prepare update data
            update_data = {}

            # Generate transaction code if not exists
            if not transaction.get('transaction_code'):
                timestamp = transaction.get('timestamp', datetime.utcnow().isoformat())
                transaction_code = explorer_service.generate_transaction_code(transaction_id, timestamp)
                update_data['transaction_code'] = transaction_code
                print(f"  ✓ Generated transaction_code: {transaction_code}")

            # Generate transaction hash if not exists
            if not transaction.get('transaction_hash'):
                transaction_hash = explorer_service.generate_transaction_hash(transaction)
                update_data['transaction_hash'] = transaction_hash
                print(f"  ✓ Generated transaction_hash: {transaction_hash[:16]}...")

            # Add pickup code if not exists
            if not transaction.get('pickup_code'):
                pickup_code = explorer_service.generate_pickup_code(transaction_id)
                update_data['pickup_code'] = pickup_code
                print(f"  ✓ Generated pickup_code: {pickup_code}")

            # Add delivery code if not exists
            if not transaction.get('delivery_code'):
                delivery_code = explorer_service.generate_delivery_code(transaction_id)
                update_data['delivery_code'] = delivery_code
                print(f"  ✓ Generated delivery_code: {delivery_code}")

            # Initialize verification logs if not exists
            if 'verification_logs' not in transaction:
                update_data['verification_logs'] = []
                print(f"  ✓ Initialized verification_logs")

            # Add immutable timestamp for completed transactions
            if transaction.get('status', '').upper() in ['COMPLETED', 'DELIVERED']:
                if not transaction.get('immutable_timestamp'):
                    immutable_timestamp = transaction.get('timestamp', datetime.utcnow().isoformat())
                    update_data['immutable_timestamp'] = immutable_timestamp
                    update_data['timestamp_locked'] = True
                    print(f"  ✓ Set immutable_timestamp (locked): {immutable_timestamp}")
            else:
                # For pending transactions, set to None
                if 'immutable_timestamp' not in transaction:
                    update_data['immutable_timestamp'] = None
                    update_data['timestamp_locked'] = False
                    print(f"  ✓ Set timestamp_locked: False (pending)")

            # Add status_history if not exists
            if 'status_history' not in transaction:
                update_data['status_history'] = [{
                    'status': transaction.get('status', 'pending'),
                    'timestamp': transaction.get('timestamp', datetime.utcnow().isoformat()),
                    'updated_by': 'system_migration'
                }]
                print(f"  ✓ Initialized status_history")

            # Perform update if there's data to update
            if update_data:
                transaction_ref.update(update_data)
                print(f"  ✅ Successfully migrated!")
                success_count += 1
            else:
                print(f"  ⚠ No updates needed (already migrated)")
                success_count += 1

        except Exception as e:
            print(f"  ❌ Error migrating transaction {transaction_id}: {str(e)}")
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total transactions: {len(transactions)}")
    print(f"Successfully migrated: {success_count}")
    print(f"Errors: {error_count}")
    print("=" * 60)

    if error_count == 0:
        print("\n✅ All transactions migrated successfully!")
    else:
        print(f"\n⚠ Migration completed with {error_count} errors")


if __name__ == '__main__':
    try:
        migrate_existing_transactions()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
