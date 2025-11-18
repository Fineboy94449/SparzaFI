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
    # Use a default salt for seeding (in production, use config)
    salt = "sparzafi_default_salt_2024"
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
            'password': 'admin123',
            'user_type': 'admin',
            'is_admin': True,
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 10000.0,
            'loyalty_points': 500,
            'referral_code': 'ADMIN2024'
        },
        {
            'email': 'thandi@example.com',
            'password': 'seller123',
            'user_type': 'seller',
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 5000.0,
            'loyalty_points': 250,
            'referral_code': 'THANDI001'
        },
        {
            'email': 'sipho@example.com',
            'password': 'seller123',
            'user_type': 'seller',
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 3500.0,
            'loyalty_points': 180,
            'referral_code': 'SIPHO002'
        },
        {
            'email': 'nomsa@example.com',
            'password': 'buyer123',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 2000.0,
            'loyalty_points': 120,
            'referral_code': 'NOMSA003'
        },
        {
            'email': 'john@example.com',
            'password': 'buyer123',
            'user_type': 'buyer',
            'kyc_completed': True,
            'is_verified': False,
            'token_balance': 1500.0,
            'loyalty_points': 80,
            'referral_code': 'JOHN004'
        },
        {
            'email': 'driver1@example.com',
            'password': 'driver123',
            'user_type': 'deliverer',
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 800.0,
            'loyalty_points': 50,
            'referral_code': 'DRIVER005'
        },
        {
            'email': 'driver2@example.com',
            'password': 'driver123',
            'user_type': 'deliverer',
            'kyc_completed': True,
            'is_verified': True,
            'token_balance': 600.0,
            'loyalty_points': 40,
            'referral_code': 'DRIVER006'
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
            print(f"  ✓ Created user: {user_data['email']} (password: {password if password == 'admin123' else '***'})")
        except Exception as e:
            print(f"  ✗ Failed to create {user_data['email']}: {e}")

    return created_users


def seed_sellers(users):
    """Create seller profiles"""
    print("\n🏪 Creating sellers...")

    seller_users = [u for u in users if u.get('user_type') == 'seller']

    sellers_data = [
        {
            'user_id': 'thandi',
            'name': "Thandi's Kitchen",
            'handle': 'thandis_kitchen',
            'profile_initial': 'T',
            'location': 'Soweto, Johannesburg',
            'bio': 'Authentic South African dishes and catering services. Family recipes passed down for generations.',
            'is_verified': True,
            'verification_status': 'verified',
            'avg_rating': 4.8,
            'total_reviews': 45,
            'total_sales': 120
        },
        {
            'user_id': 'sipho',
            'name': "Sipho's Crafts",
            'handle': 'siphos_crafts',
            'profile_initial': 'S',
            'location': 'Durban, KZN',
            'bio': 'Handmade traditional Zulu crafts, beadwork, and home decor. Supporting local artisans.',
            'is_verified': True,
            'verification_status': 'verified',
            'avg_rating': 4.6,
            'total_reviews': 32,
            'total_sales': 85
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
    sipho_seller = next((s for s in sellers if s['handle'] == 'siphos_crafts'), None)

    products_data = [
        # Thandi's Kitchen Products
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Traditional Bunny Chow',
            'description': 'Authentic Durban bunny chow with lamb curry. Includes bread loaf filled with delicious curry.',
            'category': 'Food',
            'price': 65.00,
            'original_price': 75.00,
            'stock_count': 15,
            'sku': 'TK-BC-001',
            'images': ['https://via.placeholder.com/400x300?text=Bunny+Chow'],
            'avg_rating': 4.9,
            'total_reviews': 23,
            'is_active': True
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Pap and Wors Combo',
            'description': 'Classic South African meal - pap, boerewors, and chakalaka relish.',
            'category': 'Food',
            'price': 55.00,
            'stock_count': 20,
            'sku': 'TK-PW-002',
            'images': ['https://via.placeholder.com/400x300?text=Pap+and+Wors'],
            'avg_rating': 4.7,
            'total_reviews': 18,
            'is_active': True
        },
        {
            'seller_id': thandi_seller['id'] if thandi_seller else None,
            'name': 'Vetkoek (6 Pack)',
            'description': 'Freshly made vetkoek - perfect for breakfast or snack. Served with mince filling.',
            'category': 'Food',
            'price': 45.00,
            'stock_count': 30,
            'sku': 'TK-VK-003',
            'images': ['https://via.placeholder.com/400x300?text=Vetkoek'],
            'avg_rating': 4.8,
            'total_reviews': 31,
            'is_active': True
        },
        # Sipho's Crafts Products
        {
            'seller_id': sipho_seller['id'] if sipho_seller else None,
            'name': 'Zulu Beaded Necklace',
            'description': 'Handcrafted traditional Zulu beaded necklace. Each piece is unique.',
            'category': 'Crafts',
            'price': 120.00,
            'original_price': 150.00,
            'stock_count': 12,
            'sku': 'SC-ZBN-001',
            'images': ['https://via.placeholder.com/400x300?text=Beaded+Necklace'],
            'avg_rating': 4.6,
            'total_reviews': 15,
            'is_active': True
        },
        {
            'seller_id': sipho_seller['id'] if sipho_seller else None,
            'name': 'Wire Art Sculpture',
            'description': 'Beautiful wire art sculpture of African wildlife. Perfect home decor.',
            'category': 'Crafts',
            'price': 250.00,
            'stock_count': 8,
            'sku': 'SC-WAS-002',
            'images': ['https://via.placeholder.com/400x300?text=Wire+Art'],
            'avg_rating': 4.9,
            'total_reviews': 12,
            'is_active': True
        },
        {
            'seller_id': sipho_seller['id'] if sipho_seller else None,
            'name': 'Woven Basket Set (3 Sizes)',
            'description': 'Traditional woven baskets - set of 3 in different sizes. Great for storage.',
            'category': 'Crafts',
            'price': 180.00,
            'stock_count': 10,
            'sku': 'SC-WBS-003',
            'images': ['https://via.placeholder.com/400x300?text=Woven+Baskets'],
            'avg_rating': 4.5,
            'total_reviews': 9,
            'is_active': True
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
    """Create sample reviews"""
    print("\n⭐ Creating reviews...")

    buyers = [u for u in users if u.get('user_type') == 'buyer']

    reviews_data = [
        {
            'product_id': products[0]['id'],
            'seller_id': products[0]['seller_id'],
            'user_id': buyers[0]['id'],
            'rating': 5,
            'review_text': 'Amazing bunny chow! Just like my grandmother used to make. Will definitely order again!',
            'is_verified_purchase': True
        },
        {
            'product_id': products[0]['id'],
            'seller_id': products[0]['seller_id'],
            'user_id': buyers[1]['id'],
            'rating': 5,
            'review_text': 'Best bunny chow in Joburg! Authentic and delicious.',
            'is_verified_purchase': True
        },
        {
            'product_id': products[1]['id'],
            'seller_id': products[1]['seller_id'],
            'user_id': buyers[0]['id'],
            'rating': 4,
            'review_text': 'Great meal, good portion size. The chakalaka was perfect!',
            'is_verified_purchase': True
        },
        {
            'product_id': products[3]['id'],
            'seller_id': products[3]['seller_id'],
            'user_id': buyers[1]['id'],
            'rating': 5,
            'review_text': 'Beautiful craftsmanship! The beadwork is stunning.',
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
            'user_id': 'driver1',
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
            'user_id': 'driver2',
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
    buyer = next((u for u in users if u['email'] == 'nomsa@example.com'), None)
    seller = next((u for u in users if u['email'] == 'thandi@example.com'), None)

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

    buyer = next((u for u in users if u['email'] == 'nomsa@example.com'), None)

    if buyer:
        notifications = [
            {
                'user_id': buyer['id'],
                'title': 'Welcome to SparzaFI!',
                'message': 'Thank you for joining our community marketplace. Start exploring!',
                'notification_type': 'system',
                'is_read': False
            },
            {
                'user_id': buyer['id'],
                'title': 'New Product Available',
                'message': 'Thandi\'s Kitchen added a new item: Traditional Bunny Chow',
                'notification_type': 'product',
                'is_read': True
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
        print("  Admin:    admin@sparzafi.com / admin123")
        print("  Seller:   thandi@example.com / seller123")
        print("  Buyer:    nomsa@example.com / buyer123")
        print("  Deliverer: driver1@example.com / driver123")

        print("\n🚀 You can now start testing your application!")

    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
