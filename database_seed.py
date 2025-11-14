"""
SparzaFi Database Seeding System
Comprehensive seed data for marketplace, fintech, and delivery ecosystem
"""

import sqlite3
import secrets
import hashlib
import os
from datetime import datetime, timedelta
import random

# ==================== CONFIGURATION ====================
DATABASE = 'sparzafi.db'
PASSWORD_SALT = os.environ.get('PASSWORD_SALT', 'sparzafi_salt_2025')

# Token Configuration
TOKEN_NAME = "Sparza Token"
TOKEN_SYMBOL = "SPZ"
INITIAL_TOKEN_BALANCE = 1500.0  # Default SPZ for new users
SPZ_TO_RAND_RATE = 1.0  # 1 SPZ = R1.00

# Platform Rates
COMMISSION_RATE = 0.065  # 6.5%
DELIVERER_FEE_RATE = 0.10  # 10%
VAT_RATE = 0.15  # 15%

# ==================== UTILITY FUNCTIONS ====================

def hash_password(password):
    """Hash password with SHA256"""
    return hashlib.sha256((password + PASSWORD_SALT).encode('utf-8')).hexdigest()

def generate_reference_id(prefix='TXN'):
    """Generate unique transaction reference"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_hex = secrets.token_hex(6).upper()
    return f"{prefix}-{timestamp}-{random_hex}"

def random_date_between(start_days_ago, end_days_ago):
    """Generate random datetime between two dates"""
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

def get_db_connection(db_path=DATABASE):
    """Get database connection with Row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(app=None):
    """Initialize database with schema from config"""
    from config import DATABASE_SCHEMA
    import os

    db_path = app.config['DATABASE'] if app else DATABASE

    # Check if database already exists and has data
    db_exists = os.path.exists(db_path)

    if db_exists:
        # Check if tables are populated
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()

        if user_count > 0:
            print(f"✅ Database already initialized with {user_count} users")
            return

    print(f"🔧 Initializing SparzaFi database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.executescript(DATABASE_SCHEMA)
    conn.commit()
    conn.close()

    print("✅ Database schema created successfully")

    # Optionally seed data
    if not app or app.config.get('SEED_DATA', True):
        seed_database(db_path)

# ==================== SEED DATA DEFINITIONS ====================

SEED_USERS = [
    {
        'email': 'admin@sparzafi.com',
        'password': 'adminpass',
        'user_type': 'admin',
        'is_admin': True,
        'kyc_completed': True,
        'phone': '+27 11 234 5678',
        'address': 'SparzaFi HQ, Sandton, Johannesburg',
        'token_balance': 50000.0
    },
    # Sellers
    {
        'email': 'thandi@sparzafi.com',
        'password': 'sellerpass',
        'user_type': 'seller',
        'kyc_completed': True,
        'phone': '+27 71 234 5001',
        'address': '45 Main Road, Soweto',
        'token_balance': 3500.0
    },
    {
        'email': 'kabelo@sparzafi.com',
        'password': 'sellerpass',
        'user_type': 'seller',
        'kyc_completed': True,
        'phone': '+27 71 234 5002',
        'address': '12 Church Street, Pretoria',
        'token_balance': 2800.0
    },
    {
        'email': 'nomsa@sparzafi.com',
        'password': 'sellerpass',
        'user_type': 'seller',
        'kyc_completed': True,
        'phone': '+27 71 234 5003',
        'address': '89 Market Street, Alexandra',
        'token_balance': 4200.0
    },
    # Deliverers
    {
        'email': 'sipho.driver@sparzafi.com',
        'password': 'driverpass',
        'user_type': 'deliverer',
        'kyc_completed': True,
        'phone': '+27 72 345 6001',
        'address': '23 Transport Avenue, Soweto',
        'token_balance': 2100.0
    },
    {
        'email': 'thembi.driver@sparzafi.com',
        'password': 'driverpass',
        'user_type': 'deliverer',
        'kyc_completed': True,
        'phone': '+27 72 345 6002',
        'address': '56 Route Street, Alexandra',
        'token_balance': 1900.0
    },
    # Buyers
    {
        'email': 'buyer1@test.com',
        'password': 'buyerpass',
        'user_type': 'buyer',
        'kyc_completed': False,
        'phone': '+27 73 456 7001',
        'address': '123 Residential Road, Johannesburg',
        'token_balance': 2500.0
    },
    {
        'email': 'buyer2@test.com',
        'password': 'buyerpass',
        'user_type': 'buyer',
        'kyc_completed': True,
        'phone': '+27 73 456 7002',
        'address': '456 Suburb Lane, Pretoria',
        'token_balance': 3000.0
    },
    {
        'email': 'buyer3@test.com',
        'password': 'buyerpass',
        'user_type': 'buyer',
        'kyc_completed': True,
        'phone': '+27 73 456 7003',
        'address': '789 Township Street, Soweto',
        'token_balance': 1800.0
    },
    {
        'email': 'buyer4@test.com',
        'password': 'buyerpass',
        'user_type': 'buyer',
        'kyc_completed': False,
        'phone': '+27 73 456 7004',
        'address': '321 City Road, Johannesburg',
        'token_balance': 2200.0
    }
]

SEED_SELLERS = [
    {
        'name': "Thandi's Kitchen",
        'handle': 'thandiskitchen',
        'profile_initial': 'T',
        'location': 'Soweto, Johannesburg',
        'bio': 'Fresh home-cooked meals with authentic township flavors. Daily specials!',
        'is_subscribed': True,
        'verification_status': 'verified',
        'balance': 0.0,
        'user_email': 'thandi@sparzafi.com',
        'videos': [
            {'type': 'intro', 'title': 'Welcome to Thandi\'s Kitchen', 'caption': 'Fresh meals daily. Order now!', 'duration': 30},
            {'type': 'detailed', 'title': 'Today\'s Special: Pap & Vleis', 'caption': 'Limited stock available', 'duration': 90},
            {'type': 'conclusion', 'title': 'Customer Love Stories', 'caption': 'See what people say about us', 'duration': 25}
        ],
        'products': [
            {'name': 'Spicy Chicken Meal', 'price': 75.00, 'description': 'Juicy chicken with traditional spices & pap', 'stock': 15},
            {'name': 'Beef Stew & Pap', 'price': 90.00, 'description': 'Slow-cooked beef stew with maize pap', 'stock': 12},
            {'name': 'Veggie Curry Bowl', 'price': 60.00, 'description': 'Fresh vegetables in curry sauce', 'stock': 20},
            {'name': 'Mogodu (Tripe)', 'price': 85.00, 'description': 'Traditional tripe stew', 'stock': 8},
            {'name': 'Samp & Beans', 'price': 55.00, 'description': 'Hearty samp and beans combo', 'stock': 18}
        ]
    },
    {
        'name': "Kabelo's Crafts",
        'handle': 'kabelocrafts',
        'profile_initial': 'K',
        'location': 'Pretoria, Tshwane',
        'bio': 'Handcrafted leather goods, traditional sandals, and custom accessories',
        'is_subscribed': False,
        'verification_status': 'verified',
        'balance': 0.0,
        'user_email': 'kabelo@sparzafi.com',
        'videos': [
            {'type': 'intro', 'title': 'Handcrafted Zulu Sandals', 'caption': 'Premium leather, custom orders welcome', 'duration': 28},
            {'type': 'detailed', 'title': 'Behind the Craft', 'caption': 'Watch our artisan process', 'duration': 120},
            {'type': 'conclusion', 'title': 'New Collection 2025', 'caption': 'Summer styles now available', 'duration': 30}
        ],
        'products': [
            {'name': 'Zulu Sandal - Brown', 'price': 450.00, 'description': 'Traditional design, premium leather', 'stock': 10},
            {'name': 'Canvas Tote Bag', 'price': 200.00, 'description': 'Durable canvas with leather handles', 'stock': 25},
            {'name': 'Leather Wallet', 'price': 350.00, 'description': 'Handstitched bifold wallet', 'stock': 15},
            {'name': 'Beaded Bracelet Set', 'price': 120.00, 'description': 'Traditional Zulu beadwork', 'stock': 30}
        ]
    },
    {
        'name': "Nomsa's Beauty Corner",
        'handle': 'nomsabeauty',
        'profile_initial': 'N',
        'location': 'Alexandra, Johannesburg',
        'bio': 'Natural beauty products, braiding services, and African skincare essentials',
        'is_subscribed': True,
        'verification_status': 'verified',
        'balance': 0.0,
        'user_email': 'nomsa@sparzafi.com',
        'videos': [
            {'type': 'intro', 'title': 'Natural Hair Care Tips', 'caption': 'Transform your hair naturally', 'duration': 32},
            {'type': 'detailed', 'title': 'Product Showcase', 'caption': 'All-natural, locally made', 'duration': 105},
            {'type': 'conclusion', 'title': 'Before & After Magic', 'caption': 'Real customer results', 'duration': 28}
        ],
        'products': [
            {'name': 'Shea Butter Mix', 'price': 80.00, 'description': 'Pure shea butter with essential oils', 'stock': 40},
            {'name': 'African Black Soap', 'price': 45.00, 'description': 'Traditional recipe, handmade', 'stock': 50},
            {'name': 'Hair Growth Oil', 'price': 120.00, 'description': 'Natural oils for hair growth', 'stock': 35},
            {'name': 'Face Scrub', 'price': 65.00, 'description': 'Exfoliating natural scrub', 'stock': 30},
            {'name': 'Body Butter', 'price': 95.00, 'description': 'Moisturizing body butter', 'stock': 25}
        ]
    }
]

SEED_DELIVERERS = [
    {
        'user_email': 'sipho.driver@sparzafi.com',
        'license_number': 'DL789456',
        'vehicle_type': 'Minibus Taxi',
        'vehicle_registration': 'GP 54321',
        'route': 'Soweto - Johannesburg CBD - Sandton',
        'is_verified': True,
        'is_active': True,
        'rating': 4.8,
        'total_deliveries': 127,
        'balance': 0.0
    },
    {
        'user_email': 'thembi.driver@sparzafi.com',
        'license_number': 'DL321654',
        'vehicle_type': 'Motorcycle',
        'vehicle_registration': 'GP 12789',
        'route': 'Alexandra - Sandton - Rosebank',
        'is_verified': True,
        'is_active': True,
        'rating': 4.9,
        'total_deliveries': 93,
        'balance': 0.0
    }
]

PROMOTION_CODES = [
    {'code': 'SPARZA10', 'discount_percent': 10, 'valid_until': datetime.now() + timedelta(days=30), 'uses_remaining': 100},
    {'code': 'WELCOME15', 'discount_percent': 15, 'valid_until': datetime.now() + timedelta(days=60), 'uses_remaining': 50},
    {'code': 'FIRSTORDER', 'discount_percent': 20, 'valid_until': datetime.now() + timedelta(days=90), 'uses_remaining': None}
]

PICKUP_POINTS = [
    {'name': 'Soweto Central Hub', 'address': 'Main Taxi Rank, Soweto', 'coordinates': '-26.2692,27.8546'},
    {'name': 'Alexandra Community Center', 'address': '12th Avenue, Alexandra', 'coordinates': '-26.1023,28.1004'},
    {'name': 'Pretoria CBD Station', 'address': 'Pretoria Station, Church Street', 'coordinates': '-25.7479,28.1884'},
    {'name': 'Sandton City Mall', 'address': 'Sandton City Entrance B', 'coordinates': '-26.1065,28.0558'}
]

# ==================== DATABASE SEEDING FUNCTIONS ====================

def seed_users(conn):
    """Seed users and create initial token balances"""
    cursor = conn.cursor()
    user_map = {}  # Map email to user_id
    
    for user_data in SEED_USERS:
        password_hash = hash_password(user_data['password'])
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, user_type, kyc_completed, is_admin,
                              phone, address, token_balance, balance, email_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 1)
        """, (
            user_data['email'],
            password_hash,
            user_data['user_type'],
            user_data['kyc_completed'],
            user_data.get('is_admin', False),
            user_data['phone'],
            user_data['address'],
            user_data['token_balance']
        ))
        
        user_id = cursor.lastrowid
        user_map[user_data['email']] = user_id
        
        # Create initial token deposit transaction
        if user_data['token_balance'] > 0:
            ref_id = generate_reference_id('DEP')
            cursor.execute("""
                INSERT INTO token_transactions (to_user_id, amount, transaction_type, 
                                                reference_id, notes, status)
                VALUES (?, ?, 'deposit', ?, 'Initial account balance', 'completed')
            """, (user_id, user_data['token_balance'], ref_id))
            
            transaction_id = cursor.lastrowid
            
            # Record balance history
            cursor.execute("""
                INSERT INTO token_balances_history (user_id, previous_balance, new_balance, 
                                                   change_amount, transaction_id)
                VALUES (?, 0.0, ?, ?, ?)
            """, (user_id, user_data['token_balance'], user_data['token_balance'], transaction_id))
    
    conn.commit()
    print(f"✅ Seeded {len(SEED_USERS)} users")
    return user_map

def seed_sellers(conn, user_map):
    """Seed sellers with products and videos"""
    cursor = conn.cursor()
    seller_map = {}
    
    for seller_data in SEED_SELLERS:
        user_id = user_map[seller_data['user_email']]
        
        cursor.execute("""
            INSERT INTO sellers (name, handle, profile_initial, location, bio, 
                               is_subscribed, verification_status, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            seller_data['name'],
            seller_data['handle'],
            seller_data['profile_initial'],
            seller_data['location'],
            seller_data['bio'],
            seller_data['is_subscribed'],
            seller_data['verification_status'],
            seller_data['balance']
        ))
        
        seller_id = cursor.lastrowid
        seller_map[seller_data['user_email']] = seller_id
        
        # Seed videos
        for video in seller_data['videos']:
            cursor.execute("""
                INSERT INTO videos (seller_id, video_type, title, caption, video_url, duration, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                seller_id,
                video['type'],
                video['title'],
                video['caption'],
                f'https://placehold.co/400x700/667eea/ffffff?text={seller_data["handle"]}',
                video['duration']
            ))
        
        # Seed products
        for product in seller_data['products']:
            cursor.execute("""
                INSERT INTO products (seller_id, name, description, price, stock_count, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                seller_id,
                product['name'],
                product['description'],
                product['price'],
                product['stock']
            ))
    
    conn.commit()
    print(f"✅ Seeded {len(SEED_SELLERS)} sellers with products and videos")
    return seller_map

def seed_deliverers(conn, user_map):
    """Seed deliverers/drivers"""
    cursor = conn.cursor()
    deliverer_map = {}
    
    for deliverer_data in SEED_DELIVERERS:
        user_id = user_map[deliverer_data['user_email']]
        
        cursor.execute("""
            INSERT INTO deliverers (user_id, license_number, vehicle_type, vehicle_registration,
                                   route, is_verified, is_active, rating, total_deliveries, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            deliverer_data['license_number'],
            deliverer_data['vehicle_type'],
            deliverer_data['vehicle_registration'],
            deliverer_data['route'],
            deliverer_data['is_verified'],
            deliverer_data['is_active'],
            deliverer_data['rating'],
            deliverer_data['total_deliveries'],
            deliverer_data['balance']
        ))
        
        deliverer_id = cursor.lastrowid
        deliverer_map[deliverer_data['user_email']] = deliverer_id
    
    conn.commit()
    print(f"✅ Seeded {len(SEED_DELIVERERS)} deliverers")
    return deliverer_map

def seed_transactions(conn, user_map, seller_map, deliverer_map):
    """Seed sample transactions with various statuses"""
    cursor = conn.cursor()
    
    statuses = ['PENDING', 'CONFIRMED', 'READY_FOR_PICKUP', 'PICKED_UP', 
                'IN_TRANSIT', 'DELIVERED', 'COMPLETED']
    payment_methods = ['COD', 'EFT', 'SnapScan', 'SPZ']
    
    buyer_ids = [user_map['buyer1@test.com'], user_map['buyer2@test.com'], 
                 user_map['buyer3@test.com'], user_map['buyer4@test.com']]
    seller_ids = list(seller_map.values())
    deliverer_ids = list(deliverer_map.values())
    
    # Create 50 transactions with varied statuses and dates
    for i in range(50):
        buyer_id = random.choice(buyer_ids)
        seller_id = random.choice(seller_ids)
        deliverer_id = random.choice(deliverer_ids) if random.random() > 0.3 else None
        
        total_amount = round(random.uniform(50, 500), 2)
        driver_fee = round(total_amount * DELIVERER_FEE_RATE, 2) if deliverer_id else 0
        commission = round(total_amount * COMMISSION_RATE, 2)
        seller_amount = round(total_amount - driver_fee - commission, 2)
        
        status = random.choice(statuses)
        payment_method = random.choice(payment_methods)
        created_at = random_date_between(60, 0)
        
        cursor.execute("""
            INSERT INTO transactions (user_id, seller_id, deliverer_id, total_amount,
                                    seller_amount, deliverer_fee, platform_commission,
                                    status, payment_method, delivery_method,
                                    delivery_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'public_transport', 
                   'Sample Address', ?)
        """, (
            buyer_id, seller_id, deliverer_id, total_amount,
            seller_amount, driver_fee, commission, status,
            payment_method, created_at
        ))
        
        transaction_id = cursor.lastrowid
        
        # Add delivery tracking
        cursor.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (transaction_id, status, f'Transaction {status.lower()}', buyer_id, created_at))
    
    conn.commit()
    print(f"✅ Seeded 50 sample transactions")

def seed_promotions(conn):
    """Seed promotion codes"""
    cursor = conn.cursor()
    
    for promo in PROMOTION_CODES:
        cursor.execute("""
            INSERT INTO promotion_codes (code, discount_percent, valid_until, uses_remaining)
            VALUES (?, ?, ?, ?)
        """, (promo['code'], promo['discount_percent'], promo['valid_until'], promo['uses_remaining']))
    
    conn.commit()
    print(f"✅ Seeded {len(PROMOTION_CODES)} promotion codes")

def seed_pickup_points(conn):
    """Seed local pickup points"""
    cursor = conn.cursor()
    
    for point in PICKUP_POINTS:
        cursor.execute("""
            INSERT INTO pickup_points (name, address, coordinates, is_active)
            VALUES (?, ?, ?, 1)
        """, (point['name'], point['address'], point['coordinates']))
    
    conn.commit()
    print(f"✅ Seeded {len(PICKUP_POINTS)} pickup points")

def seed_reviews(conn, user_map, seller_map):
    """Seed product reviews"""
    cursor = conn.cursor()
    
    buyers = [user_map['buyer1@test.com'], user_map['buyer2@test.com'], 
              user_map['buyer3@test.com'], user_map['buyer4@test.com']]
    
    reviews = [
        "Great quality! Will order again.",
        "Fast delivery and excellent product.",
        "Exactly as described. Very satisfied.",
        "Good value for money.",
        "Amazing service! Highly recommended.",
        "Product exceeded expectations.",
        "Quick response from seller."
    ]
    
    # Get all products
    products = conn.execute("SELECT id, seller_id FROM products").fetchall()
    
    for product_id, seller_id in products[:20]:  # Review first 20 products
        reviewer_id = random.choice(buyers)
        rating = random.randint(4, 5)
        review_text = random.choice(reviews)
        
        cursor.execute("""
            INSERT INTO reviews (product_id, seller_id, user_id, rating, review_text)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, seller_id, reviewer_id, rating, review_text))
    
    conn.commit()
    print("✅ Seeded product reviews")

def seed_follows(conn, user_map, seller_map):
    """Seed seller follows"""
    cursor = conn.cursor()
    
    buyers = [user_map['buyer1@test.com'], user_map['buyer2@test.com'], 
              user_map['buyer3@test.com'], user_map['buyer4@test.com']]
    sellers = list(seller_map.values())
    
    for buyer_id in buyers:
        # Each buyer follows 1-2 sellers
        followed_sellers = random.sample(sellers, random.randint(1, 2))
        for seller_id in followed_sellers:
            try:
                cursor.execute("""
                    INSERT INTO follows (user_id, seller_id)
                    VALUES (?, ?)
                """, (buyer_id, seller_id))
            except sqlite3.IntegrityError:
                pass  # Already following
    
    conn.commit()
    print("✅ Seeded seller follows")

# ==================== MAIN SEED FUNCTION ====================

def seed_database(db_path=DATABASE):
    """Main function to seed entire database"""
    print(f"\n🌱 Starting SparzaFi database seeding...")
    print(f"📦 Database: {db_path}\n")

    # First, create the schema
    from config import DATABASE_SCHEMA
    conn = sqlite3.connect(db_path)
    print("🔧 Creating database schema...")
    conn.executescript(DATABASE_SCHEMA)
    conn.commit()
    print("✅ Schema created successfully\n")

    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    
    try:
        # Seed in order (respecting foreign key constraints)
        user_map = seed_users(conn)
        seller_map = seed_sellers(conn, user_map)
        deliverer_map = seed_deliverers(conn, user_map)
        seed_transactions(conn, user_map, seller_map, deliverer_map)
        seed_promotions(conn)
        seed_pickup_points(conn)
        seed_reviews(conn, user_map, seller_map)
        seed_follows(conn, user_map, seller_map)
        
        print("\n✨ Database seeding completed successfully!")
        print(f"\n📊 Summary:")
        print(f"   • {len(SEED_USERS)} users")
        print(f"   • {len(SEED_SELLERS)} sellers")
        print(f"   • {len(SEED_DELIVERERS)} deliverers")
        print(f"   • 50 transactions")
        print(f"   • {len(PROMOTION_CODES)} promotion codes")
        print(f"   • {len(PICKUP_POINTS)} pickup points")
        print(f"   • Product reviews and follows\n")
        
        print("🔐 Login Credentials:")
        print("   Admin:    admin@sparzafi.com / adminpass")
        print("   Seller:   thandi@sparzafi.com / sellerpass")
        print("   Deliverer: sipho.driver@sparzafi.com / driverpass")
        print("   Buyer:    buyer1@test.com / buyerpass\n")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    seed_database()