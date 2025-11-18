"""
Migration Verification Script
Checks all data in Firebase to verify migration status
"""

import sys
import os

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
    transaction_service,
    withdrawal_service
)
from google.cloud.firestore_v1.base_query import FieldFilter


def count_collection(db, collection_name):
    """Count documents in a collection"""
    try:
        docs = db.collection(collection_name).stream()
        count = sum(1 for _ in docs)
        return count
    except Exception as e:
        return f"Error: {e}"


def verify_firebase_data():
    """Verify all data in Firebase"""
    print("=" * 70)
    print("🔍 FIREBASE DATA VERIFICATION REPORT")
    print("=" * 70)

    # Initialize Firebase
    try:
        service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        initialize_firebase(service_account_path)
        db = get_firestore_db()
        print("\n✓ Firebase connected successfully")
    except Exception as e:
        print(f"\n✗ Firebase connection failed: {e}")
        return

    # Collections to check
    collections = [
        'users',
        'sellers',
        'products',
        'reviews',
        'orders',
        'transactions',
        'deliverers',
        'delivery_routes',
        'conversations',
        'messages',
        'notifications',
        'withdrawal_requests',
        'seller_badges',
        'addresses',
        'videos',
        'follows',
        'seller_likes',
        'video_likes',
        'delivery_tracking',
        'verification_submissions',
        'moderation_queue',
        'token_transactions',
        'token_balances_history',
        'loyalty_rewards',
        'return_requests',
        'deliverer_reviews'
    ]

    print("\n" + "=" * 70)
    print("📊 FIREBASE COLLECTIONS STATUS")
    print("=" * 70)

    total_documents = 0
    non_empty_collections = []

    for collection_name in sorted(collections):
        count = count_collection(db, collection_name)
        if isinstance(count, int):
            total_documents += count
            status = "✓" if count > 0 else "○"
            if count > 0:
                non_empty_collections.append((collection_name, count))
            print(f"{status} {collection_name:30} {count:>5} documents")
        else:
            print(f"✗ {collection_name:30} {count}")

    print("=" * 70)
    print(f"\n📈 SUMMARY:")
    print(f"  Total Collections Checked: {len(collections)}")
    print(f"  Non-Empty Collections: {len(non_empty_collections)}")
    print(f"  Total Documents: {total_documents}")

    if non_empty_collections:
        print(f"\n📦 COLLECTIONS WITH DATA:")
        for name, count in non_empty_collections:
            print(f"  • {name}: {count} documents")

    # Detailed verification for key collections
    print("\n" + "=" * 70)
    print("🔎 DETAILED DATA VERIFICATION")
    print("=" * 70)

    # Users
    print("\n👥 USERS:")
    try:
        user_service = get_user_service()
        users_query = db.collection('users').stream()
        users = [{'id': doc.id, **doc.to_dict()} for doc in users_query]

        if users:
            print(f"  Total: {len(users)}")
            user_types = {}
            for user in users:
                utype = user.get('user_type', 'unknown')
                user_types[utype] = user_types.get(utype, 0) + 1

            for utype, count in user_types.items():
                print(f"    • {utype}: {count}")

            print(f"  Sample users:")
            for user in users[:5]:
                email = user.get('email', 'N/A')
                utype = user.get('user_type', 'N/A')
                verified = '✓' if user.get('is_verified') else '○'
                print(f"    {verified} {email:30} ({utype})")
        else:
            print("  ⚠️  No users found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Sellers
    print("\n🏪 SELLERS:")
    try:
        sellers = seller_service.get_all_sellers()
        if sellers:
            print(f"  Total: {len(sellers)}")
            for seller in sellers[:5]:
                name = seller.get('name', 'N/A')
                verified = '✓' if seller.get('is_verified') else '○'
                sales = seller.get('total_sales', 0)
                print(f"    {verified} {name:30} ({sales} sales)")
        else:
            print("  ⚠️  No sellers found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Products
    print("\n📦 PRODUCTS:")
    try:
        product_service = get_product_service()
        products = product_service.get_all(limit=100)
        if products:
            print(f"  Total: {len(products)}")
            active = sum(1 for p in products if p.get('is_active', True))
            print(f"    • Active: {active}")
            print(f"    • Inactive: {len(products) - active}")

            print(f"  Sample products:")
            for product in products[:5]:
                name = product.get('name', 'N/A')
                price = product.get('price', 0)
                stock = product.get('stock_count', 0)
                active_status = '✓' if product.get('is_active', True) else '○'
                print(f"    {active_status} {name:35} R{price:>6.2f} (Stock: {stock})")
        else:
            print("  ⚠️  No products found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Reviews
    print("\n⭐ REVIEWS:")
    try:
        reviews_query = db.collection('reviews').stream()
        reviews = list(reviews_query)
        if reviews:
            print(f"  Total: {len(reviews)}")
            total_rating = sum(r.to_dict().get('rating', 0) for r in reviews)
            avg_rating = total_rating / len(reviews) if reviews else 0
            print(f"    • Average Rating: {avg_rating:.1f}/5.0")
        else:
            print("  ⚠️  No reviews found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Deliverers
    print("\n🚗 DELIVERERS:")
    try:
        deliverers = deliverer_service.get_all_deliverers()
        if deliverers:
            print(f"  Total: {len(deliverers)}")
            verified = sum(1 for d in deliverers if d.get('is_verified'))
            active = sum(1 for d in deliverers if d.get('is_active'))
            available = sum(1 for d in deliverers if d.get('is_available'))
            print(f"    • Verified: {verified}")
            print(f"    • Active: {active}")
            print(f"    • Available: {available}")

            for deliverer in deliverers[:3]:
                user_id = deliverer.get('user_id', 'N/A')
                vehicle = deliverer.get('vehicle_type', 'N/A')
                rating = deliverer.get('rating', 0)
                print(f"    • {user_id}: {vehicle} (Rating: {rating:.1f})")
        else:
            print("  ⚠️  No deliverers found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Delivery Routes
    print("\n🛣️  DELIVERY ROUTES:")
    try:
        routes_query = db.collection('delivery_routes').stream()
        routes = list(routes_query)
        if routes:
            print(f"  Total: {len(routes)}")
            active = sum(1 for r in routes if r.to_dict().get('is_active'))
            print(f"    • Active: {active}")

            for route in routes[:3]:
                route_data = route.to_dict()
                route_no = route_data.get('route_no', 'N/A')
                name = route_data.get('route_name', 'N/A')
                base_fee = route_data.get('base_fee', 0)
                print(f"    • {route_no}: {name} (R{base_fee:.2f} base)")
        else:
            print("  ⚠️  No delivery routes found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Conversations & Messages
    print("\n💬 CHAT:")
    try:
        conversations_query = db.collection('conversations').stream()
        conversations = list(conversations_query)
        messages_query = db.collection('messages').stream()
        messages = list(messages_query)

        print(f"  Conversations: {len(conversations)}")
        print(f"  Messages: {len(messages)}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print("\n" + "=" * 70)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 70)

    # Final status
    if total_documents > 0:
        print(f"\n✓ Firebase database is populated with {total_documents} documents")
        print(f"✓ {len(non_empty_collections)} collections have data")
        print("\n🎉 Your data is in Firebase and ready to use!")
    else:
        print("\n⚠️  Firebase database is empty")
        print("   Run: python seed_firebase.py to populate with sample data")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    verify_firebase_data()
