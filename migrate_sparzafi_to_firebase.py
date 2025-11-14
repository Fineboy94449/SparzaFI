"""
SparzaFI SQLite to Firebase Migration Script
Migrates actual SparzaFI database to Firestore
"""

import sqlite3
import argparse
from datetime import datetime
import sys
import os
import json

# Initialize Firebase
from firebase_config import initialize_firebase, get_firestore_db

def migrate_users(db_conn, firestore_db, dry_run=False):
    """Migrate users table"""
    print("\n📊 Migrating users...")

    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    migrated = 0
    failed = 0

    for row in users:
        user_data = {
            'email': row['email'],
            'password_hash': row['password_hash'],
            'user_type': row['user_type'],
            'kyc_completed': bool(row['kyc_completed']),
            'is_admin': bool(row['is_admin']),
            'is_verified': bool(row['is_verified']),
            'phone': row['phone'],
            'address': row['address'],
            'profile_picture': row['profile_picture'],
            'balance': float(row['balance']) if row['balance'] else 0.0,
            'token_balance': float(row['token_balance']) if row['token_balance'] else 0.0,
            'loyalty_points': float(row['loyalty_points']) if row['loyalty_points'] else 0.0,
            'referral_code': row['referral_code'],
            'referred_by': row['referred_by'],
            'email_verified': bool(row['email_verified']),
            'theme_preference': row['theme_preference'],
            'language_preference': row['language_preference'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'last_login': row['last_login']
        }

        if not dry_run:
            try:
                doc_id = f"user_{row['id']}"
                firestore_db.collection('users').document(doc_id).set(user_data)
                migrated += 1
                print(f"  ✓ Migrated user: {row['email']}")
            except Exception as e:
                print(f"  ✗ Failed to migrate user {row['email']}: {e}")
                failed += 1
        else:
            migrated += 1
            print(f"  [DRY-RUN] Would migrate user: {row['email']}")

    print(f"✓ Users: {migrated}/{len(users)} migrated" + (f", {failed} failed" if failed > 0 else ""))
    return {'migrated': migrated, 'total': len(users), 'failed': failed}


def migrate_products(db_conn, firestore_db, dry_run=False):
    """Migrate products table"""
    print("\n📦 Migrating products...")

    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT p.*, s.name as seller_name, s.handle as seller_handle, u.email as seller_email
        FROM products p
        LEFT JOIN sellers s ON p.seller_id = s.id
        LEFT JOIN users u ON s.user_id = u.id
    """)
    products = cursor.fetchall()

    migrated = 0
    failed = 0

    for row in products:
        # Parse images JSON if present
        images = []
        if row['images']:
            try:
                images = json.loads(row['images'])
            except:
                images = [row['images']] if row['images'] else []

        product_data = {
            'name': row['name'],
            'description': row['description'],
            'category': row['category'],
            'price': float(row['price']),
            'original_price': float(row['original_price']) if row['original_price'] else float(row['price']),
            'stock_count': int(row['stock_count']),
            'sku': row['sku'],
            'images': images,
            'is_active': bool(row['is_active']),
            'is_featured': bool(row['is_featured']),
            'total_sales': int(row['total_sales']) if row['total_sales'] else 0,
            'avg_rating': float(row['avg_rating']) if row['avg_rating'] else 0.0,
            'total_reviews': int(row['total_reviews']) if row['total_reviews'] else 0,
            'seller_id': f"seller_{row['seller_id']}",
            'seller': {
                'name': row['seller_name'] if row['seller_name'] else 'Unknown Seller',
                'handle': row['seller_handle'] if row['seller_handle'] else '',
                'email': row['seller_email'] if row['seller_email'] else ''
            },
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }

        if not dry_run:
            try:
                doc_id = f"product_{row['id']}"
                firestore_db.collection('products').document(doc_id).set(product_data)
                migrated += 1
                print(f"  ✓ Migrated product: {row['name']}")
            except Exception as e:
                print(f"  ✗ Failed to migrate product {row['name']}: {e}")
                failed += 1
        else:
            migrated += 1
            print(f"  [DRY-RUN] Would migrate product: {row['name']}")

    print(f"✓ Products: {migrated}/{len(products)} migrated" + (f", {failed} failed" if failed > 0 else ""))
    return {'migrated': migrated, 'total': len(products), 'failed': failed}


def migrate_notifications(db_conn, firestore_db, dry_run=False):
    """Migrate notifications table"""
    print("\n🔔 Migrating notifications...")

    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM notifications")
    notifications = cursor.fetchall()

    migrated = 0
    failed = 0

    for row in notifications:
        notif_data = {
            'user_id': f"user_{row['user_id']}",
            'title': row['title'],
            'message': row['message'],
            'notification_type': row['notification_type'],
            'related_id': row['related_id'],
            'is_read': bool(row['is_read']),
            'read_at': row['read_at'],
            'created_at': row['created_at']
        }

        if not dry_run:
            try:
                doc_id = f"notification_{row['id']}"
                firestore_db.collection('notifications').document(doc_id).set(notif_data)
                migrated += 1
            except Exception as e:
                print(f"  ✗ Failed to migrate notification: {e}")
                failed += 1
        else:
            migrated += 1

    print(f"✓ Notifications: {migrated}/{len(notifications)} migrated" + (f", {failed} failed" if failed > 0 else ""))
    return {'migrated': migrated, 'total': len(notifications), 'failed': failed}


def migrate_transactions(db_conn, firestore_db, dry_run=False):
    """Migrate transactions table"""
    print("\n💰 Migrating transactions...")

    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM transactions LIMIT 50")  # Limit to first 50
    transactions = cursor.fetchall()

    migrated = 0
    failed = 0

    for row in transactions:
        trans_data = {
            'user_id': f"user_{row['user_id']}",
            'seller_id': f"seller_{row['seller_id']}" if row['seller_id'] else None,
            'deliverer_id': f"deliverer_{row['deliverer_id']}" if row['deliverer_id'] else None,
            'total_amount': float(row['total_amount']) if row['total_amount'] else 0.0,
            'seller_amount': float(row['seller_amount']) if row['seller_amount'] else 0.0,
            'deliverer_fee': float(row['deliverer_fee']) if row['deliverer_fee'] else 0.0,
            'platform_commission': float(row['platform_commission']) if row['platform_commission'] else 0.0,
            'tax_amount': float(row['tax_amount']) if row['tax_amount'] else 0.0,
            'discount_amount': float(row['discount_amount']) if row['discount_amount'] else 0.0,
            'promotion_code': row['promotion_code'],
            'status': row['status'],
            'payment_method': row['payment_method'],
            'delivery_method': row['delivery_method'],
            'delivery_address': row['delivery_address'],
            'pickup_code': row['pickup_code'],
            'delivery_code': row['delivery_code'],
            'timestamp': row['timestamp'],
            'updated_at': row['updated_at']
        }

        if not dry_run:
            try:
                doc_id = f"transaction_{row['id']}"
                firestore_db.collection('transactions').document(doc_id).set(trans_data)
                migrated += 1
            except Exception as e:
                print(f"  ✗ Failed to migrate transaction: {e}")
                failed += 1
        else:
            migrated += 1

    print(f"✓ Transactions: {migrated}/{len(transactions)} migrated (first 50 only)" + (f", {failed} failed" if failed > 0 else ""))
    return {'migrated': migrated, 'total': len(transactions), 'failed': failed}


def main():
    parser = argparse.ArgumentParser(description='Migrate SparzaFI SQLite to Firebase')
    parser.add_argument('--db', default='sparzafi.db', help='SQLite database path')
    parser.add_argument('--dry-run', action='store_true', help='Test without writing to Firebase')
    parser.add_argument('--tables', nargs='+', choices=['users', 'products', 'notifications', 'transactions', 'all'],
                        default=['all'], help='Tables to migrate')

    args = parser.parse_args()

    # Initialize Firebase
    print("🔥 Initializing Firebase...")
    initialize_firebase()
    firestore_db = get_firestore_db()

    # Connect to SQLite
    if not os.path.exists(args.db):
        print(f"❌ Database file not found: {args.db}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(args.db)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"\n🚀 Starting migration from SQLite to Firebase...")
    if args.dry_run:
        print("⚠️  DRY-RUN MODE - No data will be written to Firebase\n")

    results = {}
    tables = args.tables if 'all' not in args.tables else ['users', 'products', 'notifications', 'transactions']

    # Migrate tables
    if 'users' in tables:
        results['users'] = migrate_users(sqlite_conn, firestore_db, args.dry_run)

    if 'products' in tables:
        results['products'] = migrate_products(sqlite_conn, firestore_db, args.dry_run)

    if 'notifications' in tables:
        results['notifications'] = migrate_notifications(sqlite_conn, firestore_db, args.dry_run)

    if 'transactions' in tables:
        results['transactions'] = migrate_transactions(sqlite_conn, firestore_db, args.dry_run)

    # Print summary
    print("\n" + "="*60)
    print("📊 MIGRATION SUMMARY")
    print("="*60)

    total_migrated = 0
    total_records = 0
    total_failed = 0

    for table, stats in results.items():
        total_migrated += stats['migrated']
        total_records += stats['total']
        total_failed += stats.get('failed', 0)
        status = "✓" if stats['migrated'] == stats['total'] else "⚠"
        print(f"{status} {table.upper():<20} {stats['migrated']}/{stats['total']} migrated")

    print("="*60)
    print(f"TOTAL: {total_migrated}/{total_records} migrated" + (f", {total_failed} failed" if total_failed > 0 else ""))
    print("="*60)

    if args.dry_run:
        print("\n✓ Dry-run complete! Run without --dry-run to actually migrate.")
    else:
        print("\n✓ Migration complete!")

    sqlite_conn.close()


if __name__ == '__main__':
    main()
