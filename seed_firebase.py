"""
Firebase Database Seeding Script for SparzaFI
Creates sample data for testing all features
"""

import sys
import os
from datetime import datetime, timedelta
import random
import hashlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from firebase_config import initialize_firebase, get_firestore_db
from firebase_db import (
    get_user_service,
    seller_service,
    get_product_service,
    review_service,
    conversation_service,
    message_service,
    deliverer_service,
    delivery_route_service,
    get_notification_service
)
from google.cloud import firestore


def hash_password(password):
    """Hash password using SHA256 with salt (standalone version)"""
    # Use the same salt as in config.py
    salt = "sparzafi_salt_2025"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def clear_firebase_data(db):
    """Clear all existing data (optional - for fresh start)"""
    print("\n🗑️  Clearing existing Firebase data...")

    collections = [
        'users', 'sellers', 'products', 'reviews',
        'conversations', 'messages', 'deliverers', 'delivery_routes',
        'transactions', 'notifications'
    ]

    deleted_count = 0
    for collection_name in collections:
        docs = db.collection(collection_name).stream()
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1

    print(f"✓ Deleted {deleted_count} documents")


def seed_users():
    """Create sample users"""
    print("\n👥 Creating users...")
    user_service = get_user_service()

    users_data = [
        {
            'email': 'admin@sparzafi.com',
            'password': 'adminpass',
            'user_type': 'admin',
            'is_admin': True,
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 10000.0,
            'token_balance': 10000.0,
            'loyalty_points': 500,
            'referral_code': 'ADMIN2024',
            'full_name': 'SparzaFI Admin',
            'phone': '+27 11 000 0000',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'thandi@sparzafi.com',
            'password': 'sellerpass',
            'user_type': 'seller',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 4263.60,
            'token_balance': 4263.60,
            'loyalty_points': 250,
            'referral_code': 'THANDI001',
            'full_name': 'Thandi Nkosi',
            'phone': '+27 71 234 5678',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'buyer1@test.com',
            'password': 'buyerpass',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 2000.0,
            'token_balance': 2000.0,
            'loyalty_points': 120,
            'referral_code': 'BUYER001',
            'full_name': 'Test Buyer One',
            'phone': '+27 82 111 2222',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'buyer2@test.com',
            'password': 'buyerpass',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 1500.0,
            'token_balance': 1500.0,
            'loyalty_points': 80,
            'referral_code': 'BUYER002',
            'full_name': 'Test Buyer Two',
            'phone': '+27 82 333 4444',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'buyer3@test.com',
            'password': 'buyerpass',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 1200.0,
            'token_balance': 1200.0,
            'loyalty_points': 60,
            'referral_code': 'BUYER003',
            'full_name': 'Test Buyer Three',
            'phone': '+27 82 555 6666',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'buyer4@test.com',
            'password': 'buyerpass',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 1000.0,
            'token_balance': 1000.0,
            'loyalty_points': 40,
            'referral_code': 'BUYER004',
            'full_name': 'Test Buyer Four',
            'phone': '+27 82 777 8888',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'sipho.driver@sparzafi.com',
            'password': 'driverpass',
            'user_type': 'deliverer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 800.0,
            'token_balance': 800.0,
            'loyalty_points': 50,
            'referral_code': 'DRIVER001',
            'full_name': 'Sipho Dlamini',
            'phone': '+27 83 100 2000',
            'status': 'active',
            'kyc_status': 'verified'
        },
        {
            'email': 'thembi.driver@sparzafi.com',
            'password': 'driverpass',
            'user_type': 'deliverer',
            'kyc_completed': True,
            'is_verified': True,
            'email_verified': True,
            'phone_verified': True,
            'spz_balance': 600.0,
            'token_balance': 600.0,
            'loyalty_points': 40,
            'referral_code': 'DRIVER002',
            'full_name': 'Thembi Mbatha',
            'phone': '+27 83 300 4000',
            'status': 'active',
            'kyc_status': 'verified'
        }
    ]

    created_users = []
    for user_data in users_data:
        password = user_data.pop('password')
        user_data['password_hash'] = hash_password(password)
        user_data['created_at'] = firestore.SERVER_TIMESTAMP
        user_data['updated_at'] = firestore.SERVER_TIMESTAMP

        # Create user with custom ID (email-based)
        user_id = user_data['email'].split('@')[0]

        try:
            user_service.create(user_data, doc_id=user_id)
            created_users.append({'id': user_id, **user_data})
            print(f"  ✓ Created user: {user_data['email']} (password: {password if password == 'adminpass' else '***'})")
        except Exception as e:
            print(f"  ✗ Failed to create {user_data['email']}: {e}")

    return created_users


def seed_sellers(users):
    """Create seller profiles"""
    print("\n🏪 Creating sellers...")

    seller_users = [u for u in users if u.get('user_type') == 'seller']

    sellers_data = [
        {
            'user_id': 'thandi',  # Still using 'thandi' as the document ID (from email split)
            'name': "Thandi's Kitchen",
            'handle': 'thandis_kitchen',
            'profile_initial': 'T',
            'location': 'Soweto, Johannesburg',
            'bio': 'Authentic South African dishes and catering services. Family recipes passed down for generations.',
            'is_verified': True,
            'verification_status': 'verified',
            'avg_rating': 4.7,
            'total_reviews': 5,
            'total_sales': 63,
            'total_followers': 4,
            'total_likes': 4
        }
    ]

    created_sellers = []
    for seller_data in sellers_data:
        try:
            seller_id = seller_service.create(seller_data)
            created_sellers.append({'id': seller_id, **seller_data})
            print(f"  ✓ Created seller: {seller_data['name']}")
        except Exception as e:
            print(f"  ✗ Failed to create {seller_data['name']}: {e}")

    return created_sellers


def seed_products(sellers):
    """Create sample products"""
    print("\n📦 Creating products...")
    product_service = get_product_service()

    thandi_seller = next((s for s in sellers if s['handle'] == 'thandis_kitchen'), None)

    products_data = [
        # Thandi's Kitchen Products (matching SHARE_WITH_TESTERS.md)
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Spicy Chicken',
            'description': 'Tender chicken pieces marinated in authentic South African spices. Served with a side of your choice.',
            'category': 'Food',
            'price': 65.00,
            'original_price': 75.00,
            'stock_count': 15,
            'sku': 'TK-SC-001',
            'images': ['https://via.placeholder.com/400x300?text=Spicy+Chicken'],
            'avg_rating': 4.8,
            'total_reviews': 12,
            'is_active': True,
            'status': 'active'
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Beef Stew',
            'description': 'Hearty beef stew slow-cooked with vegetables and traditional spices. Perfect comfort food.',
            'category': 'Food',
            'price': 55.00,
            'stock_count': 20,
            'sku': 'TK-BS-002',
            'images': ['https://via.placeholder.com/400x300?text=Beef+Stew'],
            'avg_rating': 4.6,
            'total_reviews': 18,
            'is_active': True,
            'status': 'active'
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Veggie Curry',
            'description': 'Delicious vegetarian curry with mixed vegetables in a rich, flavorful sauce.',
            'category': 'Food',
            'price': 45.00,
            'stock_count': 30,
            'sku': 'TK-VC-003',
            'images': ['https://via.placeholder.com/400x300?text=Veggie+Curry'],
            'avg_rating': 4.7,
            'total_reviews': 15,
            'is_active': True,
            'status': 'active'
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Mogodu',
            'description': 'Traditional tripe stew, slow-cooked to perfection. A true South African delicacy.',
            'category': 'Food',
            'price': 50.00,
            'stock_count': 25,
            'sku': 'TK-MG-004',
            'images': ['https://via.placeholder.com/400x300?text=Mogodu'],
            'avg_rating': 4.5,
            'total_reviews': 10,
            'is_active': True,
            'status': 'active'
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Samp & Beans',
            'description': 'Traditional samp and beans with beef. Comfort food at its best.',
            'category': 'Food',
            'price': 50.00,
            'stock_count': 18,
            'sku': 'TK-SB-005',
            'images': ['https://via.placeholder.com/400x300?text=Samp+and+Beans'],
            'avg_rating': 4.8,
            'total_reviews': 8,
            'is_active': True,
            'status': 'active'
        }
    ]

    created_products = []
    for product_data in products_data:
        if product_data['seller_id']:
            try:
                product_id = product_service.create(product_data)
                created_products.append({'id': product_id, **product_data})
                print(f"  ✓ Created product: {product_data['name']} (R{product_data['price']})")
            except Exception as e:
                print(f"  ✗ Failed to create {product_data['name']}: {e}")

    return created_products


def seed_reviews(products, users):
    """Create sample reviews (5 reviews matching SHARE_WITH_TESTERS.md)"""
    print("\n⭐ Creating reviews...")

    buyers = [u for u in users if u.get('user_type') == 'buyer']

    # 5 reviews averaging 4.7★ (5+5+5+4+4 = 23, 23/5 = 4.6, close to 4.7)
    reviews_data = [
        {
            'product_id': products[0]['id'],
            'seller_id': products[0]['seller_id'],
            'user_id': buyers[0]['id'],
            'rating': 5,
            'review_text': 'Amazing spicy chicken! Perfectly cooked and seasoned. Will definitely order again!',
            'is_verified_purchase': True
        },
        {
            'product_id': products[0]['id'],
            'seller_id': products[0]['seller_id'],
            'user_id': buyers[1]['id'],
            'rating': 5,
            'review_text': 'Best food in Joburg! Authentic and delicious. Highly recommend!',
            'is_verified_purchase': True
        },
        {
            'product_id': products[1]['id'],
            'seller_id': products[1]['seller_id'],
            'user_id': buyers[0]['id'],
            'rating': 5,
            'review_text': 'The beef stew is incredible! Rich flavor and tender meat.',
            'is_verified_purchase': True
        },
        {
            'product_id': products[2]['id'],
            'seller_id': products[2]['seller_id'],
            'user_id': buyers[1]['id'],
            'rating': 4,
            'review_text': 'Great veggie curry! Good portion size and very tasty.',
            'is_verified_purchase': True
        },
        {
            'product_id': products[4]['id'],
            'seller_id': products[4]['seller_id'],
            'user_id': buyers[2]['id'],
            'rating': 4,
            'review_text': 'Traditional samp & beans, just like home. Good quality!',
            'is_verified_purchase': True
        }
    ]

    created_count = 0
    for review_data in reviews_data:
        try:
            review_service.create(review_data)
            created_count += 1
        except Exception as e:
            print(f"  ✗ Failed to create review: {e}")

    print(f"  ✓ Created {created_count} reviews")


def seed_deliverers(users):
    """Create deliverer profiles"""
    print("\n🚗 Creating deliverers...")

    deliverer_users = [u for u in users if u.get('user_type') == 'deliverer']

    deliverers_data = [
        {
            'user_id': 'sipho',  # From sipho.driver@sparzafi.com
            'license_number': 'DL123456789',
            'vehicle_type': 'motorcycle',
            'vehicle_registration': 'ABC 123 GP',
            'is_verified': True,
            'is_active': True,
            'is_available': True,
            'rating': 4.7,
            'total_deliveries': 156,
            'price_per_km': 8.0,
            'base_fee': 15.0,
            'max_delivery_distance_km': 25.0,
            'service_areas': 'Soweto, Johannesburg CBD, Sandton'
        },
        {
            'user_id': 'thembi',  # From thembi.driver@sparzafi.com
            'license_number': 'DL987654321',
            'vehicle_type': 'car',
            'vehicle_registration': 'XYZ 789 GP',
            'is_verified': True,
            'is_active': True,
            'is_available': True,
            'rating': 4.9,
            'total_deliveries': 203,
            'price_per_km': 7.5,
            'base_fee': 20.0,
            'max_delivery_distance_km': 50.0,
            'service_areas': 'Johannesburg, Pretoria, Midrand'
        }
    ]

    created_deliverers = []
    for deliverer_data in deliverers_data:
        try:
            deliverer_id = deliverer_service.create(deliverer_data)
            created_deliverers.append({'id': deliverer_id, **deliverer_data})
            print(f"  ✓ Created deliverer: {deliverer_data['vehicle_type']} driver ({deliverer_data['user_id']})")
        except Exception as e:
            print(f"  ✗ Failed to create deliverer: {e}")

    return created_deliverers


def seed_delivery_routes(deliverers):
    """Create delivery routes"""
    print("\n🛣️  Creating delivery routes...")

    routes_data = [
        {
            'deliverer_id': deliverers[0]['id'],
            'route_no': 'JHB-001',
            'route_name': 'Soweto Express',
            'service_area': 'Soweto & Surrounds',
            'description': 'Fast delivery within Soweto area',
            'base_fee': 15.0,
            'price_per_km': 8.0,
            'max_distance_km': 20.0,
            'is_active': True
        },
        {
            'deliverer_id': deliverers[0]['id'],
            'route_no': 'JHB-002',
            'route_name': 'CBD Route',
            'service_area': 'Johannesburg CBD',
            'description': 'Quick deliveries in city center',
            'base_fee': 20.0,
            'price_per_km': 10.0,
            'max_distance_km': 15.0,
            'is_active': True
        },
        {
            'deliverer_id': deliverers[1]['id'],
            'route_no': 'GP-001',
            'route_name': 'Gauteng Wide',
            'service_area': 'Johannesburg, Pretoria, Midrand',
            'description': 'Long-distance deliveries across Gauteng',
            'base_fee': 25.0,
            'price_per_km': 7.5,
            'max_distance_km': 80.0,
            'is_active': True
        }
    ]

    created_count = 0
    for route_data in routes_data:
        try:
            delivery_route_service.create(route_data)
            created_count += 1
        except Exception as e:
            print(f"  ✗ Failed to create route: {e}")

    print(f"  ✓ Created {created_count} delivery routes")


def seed_conversations(users):
    """Create sample conversations and messages"""
    print("\n💬 Creating conversations and messages...")

    # Create a conversation between buyer and seller
    buyer = next((u for u in users if u['email'] == 'buyer1@test.com'), None)
    seller = next((u for u in users if u['email'] == 'thandi@sparzafi.com'), None)

    if buyer and seller:
        try:
            # Create conversation
            conv_data = {
                'user1_id': buyer['id'],
                'user2_id': seller['id']
            }
            conv_id = conversation_service.create(conv_data)

            # Create messages
            messages = [
                {
                    'conversation_id': conv_id,
                    'sender_id': buyer['id'],
                    'recipient_id': seller['id'],
                    'message_text': 'Hi! Is the bunny chow still available?',
                    'is_read': True
                },
                {
                    'conversation_id': conv_id,
                    'sender_id': seller['id'],
                    'recipient_id': buyer['id'],
                    'message_text': 'Yes, we have fresh bunny chow ready! When would you like to order?',
                    'is_read': True
                },
                {
                    'conversation_id': conv_id,
                    'sender_id': buyer['id'],
                    'recipient_id': seller['id'],
                    'message_text': 'Perfect! I\'ll order 2 for delivery today.',
                    'is_read': False
                }
            ]

            for msg in messages:
                message_service.create(msg)

            print(f"  ✓ Created conversation with {len(messages)} messages")
        except Exception as e:
            print(f"  ✗ Failed to create conversation: {e}")


def seed_notifications(users):
    """Create sample notifications"""
    print("\n🔔 Creating notifications...")
    notification_service = get_notification_service()

    buyer = next((u for u in users if u['email'] == 'buyer1@test.com'), None)

    if buyer:
        notifications = [
            {
                'user_id': buyer['id'],
                'title': 'Welcome to SparzaFI!',
                'message': 'Thank you for joining our community marketplace. Start exploring!',
                'notification_type': 'system'
            },
            {
                'user_id': buyer['id'],
                'title': 'New Product Available',
                'message': 'Thandi\'s Kitchen added new items: Spicy Chicken, Beef Stew, and more!',
                'notification_type': 'product'
            }
        ]

        created_count = 0
        for notif in notifications:
            try:
                notification_service.create_notification(**notif)
                created_count += 1
            except Exception as e:
                print(f"  ✗ Failed to create notification: {e}")

        print(f"  ✓ Created {created_count} notifications")


def main():
    """Run all seeding operations"""
    print("=" * 60)
    print("🌱 SparzaFI Firebase Database Seeding Script")
    print("=" * 60)

    # Initialize Firebase
    print("\n🔥 Initializing Firebase...")
    try:
        service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        initialize_firebase(service_account_path)
        db = get_firestore_db()
        print("✓ Firebase initialized successfully")
    except Exception as e:
        print(f"✗ Firebase initialization failed: {e}")
        return

    # Ask user if they want to clear existing data
    clear_data = os.environ.get('CLEAR_DATA', '').lower()
    if clear_data == 'yes':
        clear_firebase_data(db)
    elif clear_data == 'no':
        print("\n✓ Keeping existing data, adding new records...")
    else:
        # Interactive mode
        response = input("\n⚠️  Clear existing Firebase data? (yes/no): ").strip().lower()
        if response == 'yes':
            clear_firebase_data(db)

    # Seed data in order
    try:
        users = seed_users()
        sellers = seed_sellers(users)
        products = seed_products(sellers)
        seed_reviews(products, users)
        deliverers = seed_deliverers(users)
        seed_delivery_routes(deliverers)
        seed_conversations(users)
        seed_notifications(users)

        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)

        print("\n📊 Summary:")
        print(f"  • Users: {len(users)}")
        print(f"  • Sellers: {len(sellers)}")
        print(f"  • Products: {len(products)}")
        print(f"  • Deliverers: {len(deliverers)}")

        print("\n🔐 Test Credentials:")
        print("  Admin:     admin@sparzafi.com / adminpass")
        print("  Seller:    thandi@sparzafi.com / sellerpass")
        print("  Buyer:     buyer1@test.com / buyerpass")
        print("  Deliverer: sipho.driver@sparzafi.com / driverpass")

        print("\n🚀 You can now start testing your application!")

    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
