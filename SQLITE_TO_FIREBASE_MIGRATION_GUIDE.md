# SQLite to Firebase Migration Guide for SparzaFI

## 🎯 Overview

This guide provides a complete reference for migrating SparzaFI from SQLite to Firebase Firestore.

**Status**: Core infrastructure complete ✅
- `app.py` - Updated to use Firebase only ✅
- `config.py` - Firebase configuration ✅
- `firebase_db.py` - Backward-compatible database layer ✅
- `firebase_service.py` - Service layer implementations ✅

**Remaining**: Update individual modules to use Firebase services

---

## 📊 Migration Pattern

### Old SQLite Pattern
```python
from database_seed import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM products WHERE seller_id = ?", (seller_id,))
products = cursor.fetchall()
conn.close()
```

### New Firebase Pattern
```python
from firebase_db import get_product_service

product_service = get_product_service()
products = product_service.get_seller_products(seller_id)
```

---

## 🔄 Query Translation Reference

### SELECT Queries

| SQLite | Firebase Firestore |
|--------|-------------------|
| `SELECT * FROM users WHERE id = ?` | `user_service.get(user_id)` |
| `SELECT * FROM users WHERE email = ?` | `user_service.get_by_email(email)` |
| `SELECT * FROM products WHERE seller_id = ?` | `product_service.get_seller_products(seller_id)` |
| `SELECT * FROM products WHERE status = 'active'` | `product_service.get_active_products()` |
| `SELECT * FROM orders WHERE user_id = ?` | `order_service.get_user_orders(user_id)` |
| `SELECT * FROM reviews WHERE product_id = ?` | `review_service.get_product_reviews(product_id)` |

### INSERT Queries

| SQLite | Firebase Firestore |
|--------|-------------------|
| `INSERT INTO users (email, ...) VALUES (?, ...)` | `user_service.create({'email': ..., ...})` |
| `INSERT INTO products (...) VALUES (...)` | `product_service.create({...})` |
| `INSERT INTO orders (...) VALUES (...)` | `order_service.create({...})` |

### UPDATE Queries

| SQLite | Firebase Firestore |
|--------|-------------------|
| `UPDATE users SET email = ? WHERE id = ?` | `user_service.update(user_id, {'email': ...})` |
| `UPDATE products SET price = ? WHERE id = ?` | `product_service.update(product_id, {'price': ...})` |
| `UPDATE orders SET status = ? WHERE id = ?` | `order_service.update_order_status(order_id, 'status')` |

### DELETE Queries

| SQLite | Firebase Firestore |
|--------|-------------------|
| `DELETE FROM products WHERE id = ?` | `product_service.delete(product_id)` |
| `DELETE FROM reviews WHERE id = ?` | `review_service.delete(review_id)` |

### Complex Queries (JOINs)

**OLD (SQLite with JOIN):**
```python
cursor.execute("""
    SELECT p.*, s.name as seller_name, s.location
    FROM products p
    JOIN sellers s ON p.seller_id = s.id
    WHERE p.category = ?
""", (category,))
```

**NEW (Firebase - denormalized):**
```python
# Products already have seller data embedded
products = product_service.get_active_products(category=category)
# Each product has: {'seller': {'name': '...', 'email': '...'}, ...}
```

### Aggregations (COUNT, SUM, AVG)

**OLD (SQLite):**
```python
cursor.execute("SELECT COUNT(*) FROM products WHERE seller_id = ?", (seller_id,))
count = cursor.fetchone()[0]
```

**NEW (Firebase):**
```python
# Option 1: Get all and count in Python
products = product_service.get_seller_products(seller_id)
count = len(products)

# Option 2: Store aggregations in seller document
seller = seller_service.get(seller_id)
count = seller['product_count']  # Updated via Cloud Functions
```

---

## 📝 Module-by-Module Migration Checklist

### ✅ Core (COMPLETED)

- [x] `app.py` - Firebase initialization
- [x] `config.py` - Configuration
- [x] `firebase_db.py` - Database layer
- [x] `firebase_service.py` - Services

### 🔴 CRITICAL (Must Update First)

#### `shared/utils.py` (Blocks all modules)

**Functions to update:**

```python
# OLD
def get_db():
    conn = sqlite3.connect('sparzafi.db')
    return conn

# NEW
from firebase_db import get_db  # Already done in firebase_db.py

# OLD
def transfer_tokens(from_user_id, to_user_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Complex multi-step transaction
    cursor.execute("UPDATE users SET spz_balance = spz_balance - ? WHERE id = ?", ...)
    cursor.execute("UPDATE users SET spz_balance = spz_balance + ? WHERE id = ?", ...)
    cursor.execute("INSERT INTO token_transactions (...) VALUES (...)", ...)
    conn.commit()

# NEW
def transfer_tokens(from_user_id, to_user_id, amount):
    from firebase_db import get_user_service, transaction_service
    from google.cloud import firestore

    user_service = get_user_service()
    db = user_service.db

    @firestore.transactional
    def _transfer(transaction):
        # Read phase
        from_ref = db.collection('users').document(from_user_id)
        to_ref = db.collection('users').document(to_user_id)

        from_user = from_ref.get(transaction=transaction).to_dict()
        to_user = to_ref.get(transaction=transaction).to_dict()

        if from_user['spz_balance'] < amount:
            raise ValueError("Insufficient balance")

        # Write phase
        transaction.update(from_ref, {
            'spz_balance': from_user['spz_balance'] - amount
        })
        transaction.update(to_ref, {
            'spz_balance': to_user['spz_balance'] + amount
        })

    # Execute transaction
    transaction = db.transaction()
    _transfer(transaction)

    # Log transaction
    transaction_service.create({
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'amount': amount,
        'transaction_type': 'transfer'
    })
```

### 🟡 HIGH PRIORITY

#### `auth/routes.py` - Authentication

**Login route:**
```python
# OLD
@auth_bp.route('/login', methods=['POST'])
def login():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

# NEW
@auth_bp.route('/login', methods=['POST'])
def login():
    from firebase_db import get_user_service
    user_service = get_user_service()
    user = user_service.get_by_email(email)
```

**Register route:**
```python
# OLD
@auth_bp.route('/register', methods=['POST'])
def register():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, password, ...) VALUES (?, ?, ...)", ...)
    conn.commit()

# NEW
@auth_bp.route('/register', methods=['POST'])
def register():
    from firebase_db import get_user_service
    import uuid

    user_service = get_user_service()
    user_id = user_service.create({
        'email': email,
        'password_hash': hashed_password,
        'full_name': full_name,
        'user_type': 'buyer',
        'spz_balance': 1500.0
    }, doc_id=str(uuid.uuid4()))
```

#### `marketplace/routes.py` - Product Listings

**Product listing:**
```python
# OLD
@marketplace_bp.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, s.name as seller_name
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.status = 'active'
    """)
    products = cursor.fetchall()

# NEW
@marketplace_bp.route('/products')
def products():
    from firebase_db import get_product_service

    product_service = get_product_service()
    products = product_service.get_active_products(limit=50)
    # Products already have seller data embedded: product['seller']['name']
```

**Product details:**
```python
# OLD
@marketplace_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    cursor.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,))
    reviews = cursor.fetchall()

# NEW
@marketplace_bp.route('/product/<product_id>')
def product_detail(product_id):
    from firebase_db import get_product_service, review_service

    product_service = get_product_service()
    product = product_service.get(product_id)

    reviews = review_service.get_product_reviews(product_id)

    # Increment view count (atomic operation)
    product_service.increment_views(product_id)
```

#### `seller/routes.py` - Seller Dashboard

**Create product:**
```python
# OLD
@seller_bp.route('/add-product', methods=['POST'])
def add_product():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (...) VALUES (...)", ...)
    product_id = cursor.lastrowid
    conn.commit()

# NEW
@seller_bp.route('/add-product', methods=['POST'])
def add_product():
    from firebase_db import get_product_service
    import uuid

    product_service = get_product_service()
    product_id = product_service.create({
        'seller_id': session['user']['id'],
        'seller': {
            'name': session['user']['name'],
            'email': session['user']['email']
        },
        'name': request.form['name'],
        'price_zar': float(request.form['price']),
        'category': request.form['category'],
        'status': 'active'
    })
```

---

## 🔧 Common Patterns

### Pattern 1: Simple CRUD

```python
# Import services
from firebase_db import (
    get_user_service,
    get_product_service,
    get_order_service
)

# Create
user_service = get_user_service()
user_id = user_service.create({'email': 'test@example.com', ...})

# Read
user = user_service.get(user_id)
user_by_email = user_service.get_by_email('test@example.com')

# Update
user_service.update(user_id, {'phone': '+27821234567'})

# Delete
user_service.delete(user_id)
```

### Pattern 2: Filtered Queries

```python
# Get user's orders
order_service = get_order_service()
orders = order_service.get_user_orders(user_id)
pending_orders = order_service.get_user_orders(user_id, status='pending')

# Get seller's products
product_service = get_product_service()
products = product_service.get_seller_products(seller_id)

# Get active products by category
active_products = product_service.get_active_products(category='Electronics')
```

### Pattern 3: Transactions (ACID)

```python
from google.cloud import firestore
from firebase_db import get_db

db = get_db()

@firestore.transactional
def process_order(transaction, order_data):
    # Read phase
    product_ref = db.collection('products').document(order_data['product_id'])
    product = product_ref.get(transaction=transaction).to_dict()

    # Validate
    if product['stock_quantity'] < order_data['quantity']:
        raise ValueError("Insufficient stock")

    # Write phase - all updates are atomic
    transaction.update(product_ref, {
        'stock_quantity': product['stock_quantity'] - order_data['quantity']
    })

    order_ref = db.collection('orders').document()
    transaction.set(order_ref, order_data)

# Use it
transaction = db.transaction()
process_order(transaction, {...})
```

### Pattern 4: Batch Operations

```python
from firebase_db import get_db

db = get_db()
batch = db.batch()

# Update multiple documents
for product_id in product_ids:
    doc_ref = db.collection('products').document(product_id)
    batch.update(doc_ref, {'is_featured': True})

# Commit all at once
batch.commit()
```

---

## 📦 Complete Service Reference

### Available Services

```python
from firebase_db import (
    get_user_service,      # User operations
    get_product_service,   # Product operations
    get_order_service,     # Order operations
    get_delivery_service,  # Delivery tracking
    get_notification_service,  # Notifications
    get_storage_service,   # File uploads
    seller_service,        # Seller profiles
    review_service,        # Reviews
    transaction_service,   # SPZ transactions
    withdrawal_service     # Withdrawal requests
)
```

### Service Methods

**UserService:**
- `create(data, doc_id=None)` - Create user
- `get(user_id)` - Get user by ID
- `get_by_email(email)` - Get user by email
- `get_by_phone(phone)` - Get user by phone
- `update(user_id, data)` - Update user
- `delete(user_id)` - Delete user
- `update_spz_balance(user_id, amount, transaction_type)` - Update balance

**ProductService:**
- `create(data, doc_id=None)` - Create product
- `get(product_id)` - Get product
- `update(product_id, data)` - Update product
- `delete(product_id)` - Delete product
- `get_active_products(category=None, limit=50)` - Get active products
- `get_seller_products(seller_id)` - Get seller's products
- `search_products(search_term, limit=20)` - Search products
- `increment_views(product_id)` - Increment view count

**OrderService:**
- `create(data, doc_id=None)` - Create order
- `get(order_id)` - Get order
- `update(order_id, data)` - Update order
- `get_user_orders(user_id, status=None)` - Get user's orders
- `get_seller_orders(seller_id, status=None)` - Get seller's orders
- `update_order_status(order_id, new_status, updated_by)` - Update status with history

**DeliveryService:**
- `create(data, doc_id=None)` - Create delivery
- `get(delivery_id)` - Get delivery
- `update(delivery_id, data)` - Update delivery
- `get_active_deliveries(deliverer_id)` - Get active deliveries
- `update_location(delivery_id, lat, lng)` - Update location (real-time)

**NotificationService:**
- `create_notification(user_id, title, message, type, data=None)` - Create notification
- `get_user_notifications(user_id, unread_only=False)` - Get user notifications
- `mark_as_read(notification_id)` - Mark as read
- `mark_all_read(user_id)` - Mark all as read

**StorageService:**
- `upload_file(file_path, destination, content_type=None)` - Upload file
- `upload_from_string(content, destination, content_type)` - Upload from string
- `delete_file(file_path)` - Delete file
- `get_file_url(file_path)` - Get public URL

---

## ⚠️ Important Notes

### 1. Data Denormalization

Firebase requires denormalization. Embed related data instead of JOINs:

```python
# ✅ GOOD - Embedded seller data in product
product = {
    'name': 'iPhone 15',
    'seller_id': 'seller123',
    'seller': {
        'name': 'TechStore',
        'email': 'tech@example.com'
    }
}

# ❌ BAD - Separate documents requiring multiple reads
product = {'name': 'iPhone 15', 'seller_id': 'seller123'}
seller = seller_service.get('seller123')  # Extra read!
```

### 2. Aggregations

Store aggregates in documents, update via Cloud Functions or batch jobs:

```python
# Update seller stats when product is sold
seller_doc = {
    'total_sales': 150,  # Stored aggregate
    'avg_rating': 4.5,   # Stored aggregate
    'total_reviews': 45  # Stored aggregate
}
```

### 3. Transactions

Use transactions for critical operations (max 500 documents):

```python
@firestore.transactional
def atomic_operation(transaction):
    # All reads first
    # Then all writes
    pass
```

### 4. Indexes

Create composite indexes in Firebase Console for complex queries.

---

## 🎯 Next Steps

1. **Start with shared/utils.py** - This blocks all other modules
2. **Update auth/routes.py** - Core authentication
3. **Update one module at a time** - marketplace → seller → deliverer → user → admin → api → chat
4. **Test thoroughly** after each module
5. **Run migration script** to populate Firebase with existing data

---

## 📚 Additional Resources

- See `FIREBASE_INTEGRATION_GUIDE.md` for detailed Firebase usage
- See `firebase_service.py` for service implementations
- See `migrate_to_firebase.py` for data migration

---

**Migration Status Tracking:**

Update this checklist as you complete each module:

- [x] Core infrastructure
- [ ] shared/utils.py
- [ ] auth/routes.py
- [ ] marketplace/routes.py
- [ ] seller/routes.py
- [ ] deliverer/routes.py
- [ ] user/buyer_dashboard.py
- [ ] admin/routes.py
- [ ] api/routes.py
- [ ] chat/routes.py

---

**Need Help?** See FIREBASE_INTEGRATION_GUIDE.md or check Firebase documentation.
