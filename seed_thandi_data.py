"""
Seed additional data for Thandi's Kitchen to showcase the seller dashboard
"""
import sqlite3
from datetime import datetime, timedelta
import random

def seed_thandi_data():
    conn = sqlite3.connect('sparzafi.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get Thandi's seller ID
    thandi_seller = cursor.execute("SELECT id FROM sellers WHERE handle = 'thandiskitchen'").fetchone()
    if not thandi_seller:
        print("❌ Thandi's Kitchen not found!")
        return

    seller_id = thandi_seller['id']
    print(f"✅ Found Thandi's Kitchen (ID: {seller_id})")

    # Get some buyer IDs
    buyers = cursor.execute("SELECT id, email FROM users WHERE user_type = 'buyer' LIMIT 4").fetchall()
    buyer_ids = [b['id'] for b in buyers]

    # Get Thandi's product IDs
    products = cursor.execute("SELECT id, name, price FROM products WHERE seller_id = ?", (seller_id,)).fetchall()
    product_list = [dict(p) for p in products]

    if not products:
        print("❌ No products found for Thandi's Kitchen!")
        return

    print(f"✅ Found {len(products)} products")

    # ==================== CREATE PENDING ORDERS ====================
    print("\n📦 Creating pending orders...")

    pending_orders = [
        {
            'buyer_id': buyer_ids[0],
            'status': 'PENDING',
            'payment_method': 'COD',
            'items': [
                {'product_id': product_list[0]['id'], 'quantity': 2},
                {'product_id': product_list[1]['id'], 'quantity': 1}
            ]
        },
        {
            'buyer_id': buyer_ids[1],
            'status': 'PENDING',
            'payment_method': 'EFT',
            'items': [
                {'product_id': product_list[2]['id'], 'quantity': 3}
            ]
        },
        {
            'buyer_id': buyer_ids[2],
            'status': 'CONFIRMED',
            'payment_method': 'COD',
            'items': [
                {'product_id': product_list[0]['id'], 'quantity': 1},
                {'product_id': product_list[3]['id'], 'quantity': 2}
            ]
        },
        {
            'buyer_id': buyer_ids[3],
            'status': 'READY_FOR_PICKUP',
            'payment_method': 'SnapScan',
            'pickup_code': '123456',
            'items': [
                {'product_id': product_list[1]['id'], 'quantity': 4}
            ]
        }
    ]

    for order_data in pending_orders:
        # Calculate totals
        total = 0
        for item in order_data['items']:
            product = next(p for p in product_list if p['id'] == item['product_id'])
            total += product['price'] * item['quantity']

        seller_amount = total * 0.935  # After 6.5% commission
        platform_commission = total * 0.065

        # Create transaction
        cursor.execute("""
            INSERT INTO transactions (user_id, seller_id, total_amount, seller_amount,
                                     platform_commission, status, payment_method, pickup_code, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (order_data['buyer_id'], seller_id, total, seller_amount,
              platform_commission, order_data['status'], order_data['payment_method'],
              order_data.get('pickup_code')))

        transaction_id = cursor.lastrowid

        # Add transaction items
        for item in order_data['items']:
            product = next(p for p in product_list if p['id'] == item['product_id'])
            item_total = product['price'] * item['quantity']

            cursor.execute("""
                INSERT INTO transaction_items (transaction_id, product_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, (transaction_id, item['product_id'], item['quantity'], product['price'], item_total))

        print(f"  ✓ Created {order_data['status']} order: R{total:.2f}")

    # ==================== CREATE COMPLETED SALES ====================
    print("\n💰 Creating completed sales (last 7 days)...")

    completed_sales = []
    for i in range(15):
        days_ago = random.randint(0, 6)
        timestamp = datetime.now() - timedelta(days=days_ago)

        buyer_id = random.choice(buyer_ids)
        num_items = random.randint(1, 3)
        selected_products = random.sample(product_list, min(num_items, len(product_list)))

        total = 0
        items = []
        for product in selected_products:
            quantity = random.randint(1, 3)
            total += product['price'] * quantity
            items.append({'product_id': product['id'], 'quantity': quantity, 'price': product['price']})

        seller_amount = total * 0.935
        platform_commission = total * 0.065

        # Create completed transaction
        cursor.execute("""
            INSERT INTO transactions (user_id, seller_id, total_amount, seller_amount,
                                     platform_commission, status, payment_method, timestamp, delivered_at)
            VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)
        """, (buyer_id, seller_id, total, seller_amount, platform_commission,
              random.choice(['COD', 'EFT', 'SnapScan']),
              timestamp.strftime('%Y-%m-%d %H:%M:%S'),
              timestamp.strftime('%Y-%m-%d %H:%M:%S')))

        transaction_id = cursor.lastrowid

        # Add items
        for item in items:
            cursor.execute("""
                INSERT INTO transaction_items (transaction_id, product_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, (transaction_id, item['product_id'], item['quantity'],
                  item['price'], item['price'] * item['quantity']))

        completed_sales.append({'total': total, 'date': timestamp.date()})
        print(f"  ✓ Sale on {timestamp.date()}: R{total:.2f}")

    # ==================== UPDATE SELLER BALANCE ====================
    total_earned = sum(s['total'] for s in completed_sales) * 0.935

    cursor.execute("""
        UPDATE sellers SET balance = ? WHERE id = ?
    """, (total_earned, seller_id))

    print(f"\n💵 Updated wallet balance: R{total_earned:.2f}")

    # ==================== ADD REVIEWS ====================
    print("\n⭐ Adding customer reviews...")

    reviews_data = [
        {
            'rating': 5,
            'text': "Amazing food! The Spicy Chicken Meal was perfectly seasoned. Will definitely order again!",
            'buyer_id': buyer_ids[0],
            'product_id': product_list[0]['id']
        },
        {
            'rating': 5,
            'text': "Best Beef Stew I've had in a long time. Thandi's Kitchen is a gem!",
            'buyer_id': buyer_ids[1],
            'product_id': product_list[1]['id']
        },
        {
            'rating': 4,
            'text': "Very good veggie curry. Fresh ingredients and generous portions.",
            'buyer_id': buyer_ids[2],
            'product_id': product_list[2]['id']
        },
        {
            'rating': 5,
            'text': "The Samp & Beans reminded me of home! Authentic township cooking.",
            'buyer_id': buyer_ids[3],
            'product_id': product_list[4]['id']
        },
        {
            'rating': 5,
            'text': "Quick delivery and hot food. Customer service is excellent too!",
            'buyer_id': buyer_ids[0],
            'product_id': product_list[0]['id']
        }
    ]

    for review in reviews_data:
        cursor.execute("""
            INSERT INTO reviews (product_id, seller_id, user_id, rating, review_text, is_verified_purchase)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (review['product_id'], seller_id, review['buyer_id'],
              review['rating'], review['text']))

        print(f"  ✓ Added {review['rating']}-star review")

    # Update seller average rating
    avg_rating = sum(r['rating'] for r in reviews_data) / len(reviews_data)
    cursor.execute("""
        UPDATE sellers SET avg_rating = ?, total_reviews = ? WHERE id = ?
    """, (avg_rating, len(reviews_data), seller_id))

    # ==================== ADD FOLLOWERS AND LIKES ====================
    print("\n👥 Adding followers and likes...")

    # Add 15 random followers
    for i in range(15):
        try:
            cursor.execute("""
                INSERT INTO follows (user_id, seller_id)
                VALUES (?, ?)
            """, (buyer_ids[i % len(buyer_ids)], seller_id))
        except:
            pass  # Skip if already following

    # Count followers
    follower_count = cursor.execute("""
        SELECT COUNT(*) as count FROM follows WHERE seller_id = ?
    """, (seller_id,)).fetchone()['count']

    # Add likes
    for i in range(12):
        try:
            cursor.execute("""
                INSERT INTO seller_likes (user_id, seller_id)
                VALUES (?, ?)
            """, (buyer_ids[i % len(buyer_ids)], seller_id))
        except:
            pass

    likes_count = cursor.execute("""
        SELECT COUNT(*) as count FROM seller_likes WHERE seller_id = ?
    """, (seller_id,)).fetchone()['count']

    cursor.execute("""
        UPDATE sellers SET follower_count = ?, likes_count = ? WHERE id = ?
    """, (follower_count, likes_count, seller_id))

    print(f"  ✓ Followers: {follower_count}")
    print(f"  ✓ Likes: {likes_count}")

    # ==================== UPDATE PRODUCT STATS ====================
    print("\n📊 Updating product statistics...")

    for product in product_list:
        # Count sales for this product
        sales = cursor.execute("""
            SELECT SUM(ti.quantity) as total_sold
            FROM transaction_items ti
            JOIN transactions t ON ti.transaction_id = t.id
            WHERE ti.product_id = ? AND t.status = 'COMPLETED'
        """, (product['id'],)).fetchone()

        total_sold = sales['total_sold'] if sales['total_sold'] else 0

        # Count reviews
        review_count = cursor.execute("""
            SELECT COUNT(*) as count, AVG(rating) as avg_rating
            FROM reviews WHERE product_id = ?
        """, (product['id'],)).fetchone()

        cursor.execute("""
            UPDATE products
            SET total_sales = ?, total_reviews = ?, avg_rating = ?
            WHERE id = ?
        """, (total_sold, review_count['count'],
              review_count['avg_rating'] or 0, product['id']))

        print(f"  ✓ {product['name']}: {total_sold} sold, {review_count['count']} reviews")

    conn.commit()
    conn.close()

    print("\n✨ Data seeding completed successfully!")
    print("\n🎯 Summary:")
    print(f"   • Pending Orders: 4")
    print(f"   • Completed Sales: 15")
    print(f"   • Total Revenue: R{sum(s['total'] for s in completed_sales):.2f}")
    print(f"   • Wallet Balance: R{total_earned:.2f}")
    print(f"   • Reviews: 5")
    print(f"   • Followers: {follower_count}")
    print(f"   • Likes: {likes_count}")
    print("\n🔐 Login as Thandi:")
    print("   Email: thandi@sparzafi.com")
    print("   Password: sellerpass")

if __name__ == '__main__':
    seed_thandi_data()
