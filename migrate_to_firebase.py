"""
SQLite to Firebase Migration Script for SparzaFI
Migrates data from SQLite database to Firestore

Usage:
    python migrate_to_firebase.py --all                    # Migrate all tables
    python migrate_to_firebase.py --tables users products   # Migrate specific tables
    python migrate_to_firebase.py --dry-run                 # Test without writing
"""

import sqlite3
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Initialize Firebase
from firebase_config import initialize_firebase, get_firestore_db
from firebase_service import (
    ProductService, OrderService, UserService,
    DeliveryService, NotificationService
)


class SQLiteToFirebaseMigration:
    """Handles migration from SQLite to Firestore"""

    def __init__(self, sqlite_db_path: str = 'instance/sparzafi.db', dry_run: bool = False):
        self.sqlite_db_path = sqlite_db_path
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        # Connect to SQLite
        if not os.path.exists(sqlite_db_path):
            raise FileNotFoundError(f"SQLite database not found: {sqlite_db_path}")

        self.sqlite_conn = sqlite3.connect(sqlite_db_path)
        self.sqlite_conn.row_factory = sqlite3.Row  # Access columns by name

        # Initialize Firebase services
        self.product_service = ProductService()
        self.order_service = OrderService()
        self.user_service = UserService()
        self.delivery_service = DeliveryService()
        self.notification_service = NotificationService()

    def migrate_users(self) -> Dict[str, int]:
        """Migrate users table"""
        print("\n📊 Migrating users...")

        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        migrated = 0
        for row in users:
            user_data = {
                'user_id': row['user_id'],
                'email': row['email'],
                'phone': row['phone'],
                'password_hash': row['password'],
                'full_name': row['full_name'],
                'user_type': row['user_type'],
                'status': row['status'],
                'spz_balance': float(row['spz_balance']) if row['spz_balance'] else 0.0,
                'email_verified': bool(row['email_verified']),
                'phone_verified': bool(row['phone_verified']),
                'profile_image': row['profile_image'],
                'date_of_birth': row['date_of_birth'],
                'id_number': row['id_number'],
                'kyc_status': row['kyc_status'],
                'referral_code': row['referral_code'],
                'referred_by': row['referred_by'],
                'created_at': row['created_at'],
                'last_login': row['last_login']
            }

            if not self.dry_run:
                try:
                    self.user_service.create(user_data, doc_id=row['user_id'])
                    migrated += 1
                    print(f"  ✓ Migrated user: {row['email']}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate user {row['email']}: {e}")
            else:
                migrated += 1
                print(f"  [DRY-RUN] Would migrate user: {row['email']}")

        print(f"✓ Users migrated: {migrated}/{len(users)}")
        return {'migrated': migrated, 'total': len(users)}

    def migrate_products(self) -> Dict[str, int]:
        """Migrate products table with denormalized seller data"""
        print("\n📦 Migrating products...")

        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT p.*, u.full_name as seller_name, u.email as seller_email
            FROM products p
            LEFT JOIN users u ON p.seller_id = u.user_id
        """)
        products = cursor.fetchall()

        migrated = 0
        for row in products:
            # Denormalize seller data into product
            product_data = {
                'product_id': row['product_id'],
                'seller_id': row['seller_id'],
                'seller': {
                    'name': row['seller_name'],
                    'email': row['seller_email']
                },
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'subcategory': row['subcategory'],
                'price_zar': float(row['price_zar']) if row['price_zar'] else 0.0,
                'price_spz': float(row['price_spz']) if row['price_spz'] else 0.0,
                'stock_quantity': int(row['stock_quantity']) if row['stock_quantity'] else 0,
                'status': row['status'],
                'image_url': row['image_url'],
                'view_count': int(row['view_count']) if row['view_count'] else 0,
                'sale_count': int(row['sale_count']) if row['sale_count'] else 0,
                'rating': float(row['rating']) if row['rating'] else 0.0,
                'brand': row['brand'],
                'condition': row['condition'],
                'weight_kg': float(row['weight_kg']) if row['weight_kg'] else None,
                'is_featured': bool(row['is_featured']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

            if not self.dry_run:
                try:
                    self.product_service.create(product_data, doc_id=row['product_id'])
                    migrated += 1
                    print(f"  ✓ Migrated product: {row['name']}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate product {row['name']}: {e}")
            else:
                migrated += 1
                print(f"  [DRY-RUN] Would migrate product: {row['name']}")

        print(f"✓ Products migrated: {migrated}/{len(products)}")
        return {'migrated': migrated, 'total': len(products)}

    def migrate_orders(self) -> Dict[str, int]:
        """Migrate orders with order items embedded"""
        print("\n🛒 Migrating orders...")

        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()

        migrated = 0
        for row in orders:
            # Get order items for this order
            cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (row['order_id'],))
            items = cursor.fetchall()

            order_items = []
            for item in items:
                order_items.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': int(item['quantity']),
                    'price_zar': float(item['price_zar']) if item['price_zar'] else 0.0,
                    'price_spz': float(item['price_spz']) if item['price_spz'] else 0.0,
                    'subtotal_zar': float(item['subtotal_zar']) if item['subtotal_zar'] else 0.0,
                    'subtotal_spz': float(item['subtotal_spz']) if item['subtotal_spz'] else 0.0
                })

            order_data = {
                'order_id': row['order_id'],
                'user_id': row['user_id'],
                'seller_id': row['seller_id'],
                'status': row['status'],
                'payment_method': row['payment_method'],
                'payment_status': row['payment_status'],
                'total_zar': float(row['total_zar']) if row['total_zar'] else 0.0,
                'total_spz': float(row['total_spz']) if row['total_spz'] else 0.0,
                'delivery_fee': float(row['delivery_fee']) if row['delivery_fee'] else 0.0,
                'delivery_address': row['delivery_address'],
                'delivery_type': row['delivery_type'],
                'items': order_items,  # Embed order items
                'notes': row['notes'],
                'tracking_number': row['tracking_number'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'status_history': []  # Initialize empty history
            }

            if not self.dry_run:
                try:
                    self.order_service.create(order_data, doc_id=row['order_id'])
                    migrated += 1
                    print(f"  ✓ Migrated order: {row['order_id']} ({len(order_items)} items)")
                except Exception as e:
                    print(f"  ✗ Failed to migrate order {row['order_id']}: {e}")
            else:
                migrated += 1
                print(f"  [DRY-RUN] Would migrate order: {row['order_id']}")

        print(f"✓ Orders migrated: {migrated}/{len(orders)}")
        return {'migrated': migrated, 'total': len(orders)}

    def migrate_deliveries(self) -> Dict[str, int]:
        """Migrate delivery tracking data"""
        print("\n🚚 Migrating deliveries...")

        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM deliveries")
        deliveries = cursor.fetchall()

        migrated = 0
        for row in deliveries:
            delivery_data = {
                'delivery_id': row['delivery_id'],
                'order_id': row['order_id'],
                'deliverer_id': row['deliverer_id'],
                'vehicle_type': row['vehicle_type'],
                'status': row['status'],
                'pickup_address': row['pickup_address'],
                'delivery_address': row['delivery_address'],
                'distance_km': float(row['distance_km']) if row['distance_km'] else 0.0,
                'delivery_fee': float(row['delivery_fee']) if row['delivery_fee'] else 0.0,
                'current_location': {
                    'latitude': None,
                    'longitude': None,
                    'timestamp': None
                },
                'location_history': [],  # Initialize empty
                'scheduled_time': row['scheduled_time'],
                'picked_up_at': row['picked_up_at'],
                'delivered_at': row['delivered_at'],
                'created_at': row['created_at']
            }

            if not self.dry_run:
                try:
                    self.delivery_service.create(delivery_data, doc_id=row['delivery_id'])
                    migrated += 1
                    print(f"  ✓ Migrated delivery: {row['delivery_id']}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate delivery {row['delivery_id']}: {e}")
            else:
                migrated += 1
                print(f"  [DRY-RUN] Would migrate delivery: {row['delivery_id']}")

        print(f"✓ Deliveries migrated: {migrated}/{len(deliveries)}")
        return {'migrated': migrated, 'total': len(deliveries)}

    def migrate_notifications(self) -> Dict[str, int]:
        """Migrate notifications"""
        print("\n🔔 Migrating notifications...")

        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM notifications")
        notifications = cursor.fetchall()

        migrated = 0
        for row in notifications:
            notification_data = {
                'notification_id': row['notification_id'],
                'user_id': row['user_id'],
                'title': row['title'],
                'message': row['message'],
                'type': row['type'],
                'read': bool(row['read']),
                'data': {},  # Can parse JSON if stored in SQLite
                'created_at': row['created_at']
            }

            if not self.dry_run:
                try:
                    self.notification_service.create(notification_data, doc_id=row['notification_id'])
                    migrated += 1
                    print(f"  ✓ Migrated notification: {row['notification_id']}")
                except Exception as e:
                    print(f"  ✗ Failed to migrate notification {row['notification_id']}: {e}")
            else:
                migrated += 1
                print(f"  [DRY-RUN] Would migrate notification: {row['notification_id']}")

        print(f"✓ Notifications migrated: {migrated}/{len(notifications)}")
        return {'migrated': migrated, 'total': len(notifications)}

    def migrate_all(self):
        """Migrate all supported tables"""
        print("🚀 Starting complete migration from SQLite to Firebase...\n")

        results = {}

        # Migrate in order (users first, then dependent tables)
        results['users'] = self.migrate_users()
        results['products'] = self.migrate_products()
        results['orders'] = self.migrate_orders()
        results['deliveries'] = self.migrate_deliveries()
        results['notifications'] = self.migrate_notifications()

        # Print summary
        print("\n" + "="*60)
        print("📊 MIGRATION SUMMARY")
        print("="*60)

        for table, stats in results.items():
            print(f"{table.upper():20} {stats['migrated']:>5}/{stats['total']:<5} migrated")

        total_migrated = sum(r['migrated'] for r in results.values())
        total_records = sum(r['total'] for r in results.values())

        print("="*60)
        print(f"{'TOTAL':20} {total_migrated:>5}/{total_records:<5} migrated")
        print("="*60)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No data was actually written to Firebase")
        else:
            print("\n✓ Migration complete!")

    def close(self):
        """Close database connections"""
        self.sqlite_conn.close()


def main():
    parser = argparse.ArgumentParser(description='Migrate SparzaFI data from SQLite to Firebase')
    parser.add_argument('--all', action='store_true', help='Migrate all tables')
    parser.add_argument('--tables', nargs='+', help='Specific tables to migrate (e.g., users products)')
    parser.add_argument('--dry-run', action='store_true', help='Test migration without writing to Firebase')
    parser.add_argument('--db', default='instance/sparzafi.db', help='SQLite database path')
    parser.add_argument('--service-account', help='Path to Firebase service account JSON')

    args = parser.parse_args()

    # Initialize Firebase
    try:
        print("🔥 Initializing Firebase...")
        initialize_firebase(args.service_account)
    except Exception as e:
        print(f"✗ Firebase initialization failed: {e}")
        print("\nMake sure to:")
        print("1. Download your Firebase service account JSON from Firebase Console")
        print("2. Set FIREBASE_SERVICE_ACCOUNT environment variable or use --service-account flag")
        sys.exit(1)

    # Create migration instance
    migration = SQLiteToFirebaseMigration(sqlite_db_path=args.db, dry_run=args.dry_run)

    try:
        if args.all:
            migration.migrate_all()
        elif args.tables:
            # Migrate specific tables
            for table in args.tables:
                if table == 'users':
                    migration.migrate_users()
                elif table == 'products':
                    migration.migrate_products()
                elif table == 'orders':
                    migration.migrate_orders()
                elif table == 'deliveries':
                    migration.migrate_deliveries()
                elif table == 'notifications':
                    migration.migrate_notifications()
                else:
                    print(f"⚠️  Unknown table: {table}")
        else:
            print("Error: Please specify --all or --tables")
            parser.print_help()
    finally:
        migration.close()


if __name__ == '__main__':
    main()
