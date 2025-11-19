# Firebase Integration Guide for SparzaFI

Complete guide for integrating Firebase with your SparzaFI marketplace platform.

## 🔥 Table of Contents

1. [Setup Instructions](#setup-instructions)
2. [Configuration](#configuration)
3. [Using Firebase Services](#using-firebase-services)
4. [Data Migration](#data-migration)
5. [Example Usage](#example-usage)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## 📋 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `firebase-admin==6.4.0` - Firebase Admin SDK
- `google-cloud-firestore==2.14.0` - Firestore database
- `google-cloud-storage==2.14.0` - Firebase Storage

### Step 2: Get Firebase Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (or create a new one)
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Save the JSON file as `firebase-service-account.json` in your project root

**IMPORTANT**: Add this file to `.gitignore` - never commit credentials!

```bash
echo "firebase-service-account.json" >> .gitignore
```

### Step 3: Configure Environment Variables

Create or update `.env` file:

```bash
# Firebase Configuration
USE_FIREBASE=True
FIREBASE_SERVICE_ACCOUNT=/absolute/path/to/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
```

### Step 4: Verify Firebase Setup

```python
from firebase_config import initialize_firebase

initialize_firebase()
# Should print: ✓ Firebase initialized successfully (Project: your-project-id)
```

---

## ⚙️ Configuration

### Firebase Collections Structure

Your Firestore will use these collections:

```
📦 Firestore
├── 📁 users/
├── 📁 products/
├── 📁 orders/
├── 📁 deliveries/
├── 📁 notifications/
└── 📁 messages/
```

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `USE_FIREBASE` | Enable/disable Firebase | `True` or `False` |
| `FIREBASE_SERVICE_ACCOUNT` | Path to service account JSON | `/path/to/firebase-service-account.json` |
| `FIREBASE_STORAGE_BUCKET` | Storage bucket name | `sparzafi-prod.appspot.com` |

---

## 🚀 Using Firebase Services

### Product Service

```python
from firebase_service import product_service

# Create a product
product_id = product_service.create({
    'name': 'iPhone 15 Pro',
    'description': 'Latest iPhone',
    'price_zar': 15999.00,
    'price_spz': 15999.00,
    'category': 'Electronics',
    'seller_id': 'seller123',
    'seller': {
        'name': 'TechStore',
        'email': 'tech@example.com'
    },
    'stock_quantity': 10,
    'status': 'active'
})

# Get active products
products = product_service.get_active_products(category='Electronics', limit=20)

# Search products
results = product_service.search_products('iPhone', limit=10)

# Get seller's products
seller_products = product_service.get_seller_products('seller123')

# Increment view count (atomic operation)
product_service.increment_views('product123')

# Update product
product_service.update('product123', {
    'price_zar': 14999.00,
    'stock_quantity': 8
})

# Delete product
product_service.delete('product123')
```

### Order Service

```python
from firebase_service import order_service

# Create order with embedded items
order_id = order_service.create({
    'user_id': 'user123',
    'seller_id': 'seller123',
    'status': 'pending',
    'payment_method': 'SPZ',
    'payment_status': 'pending',
    'total_zar': 15999.00,
    'total_spz': 0.00,
    'delivery_fee': 150.00,
    'delivery_address': '123 Main St, Johannesburg',
    'delivery_type': 'courier',
    'items': [
        {
            'product_id': 'prod123',
            'product_name': 'iPhone 15 Pro',
            'quantity': 1,
            'price_zar': 15999.00,
            'price_spz': 0.00,
            'subtotal_zar': 15999.00,
            'subtotal_spz': 0.00
        }
    ]
})

# Get user's orders
user_orders = order_service.get_user_orders('user123')
pending_orders = order_service.get_user_orders('user123', status='pending')

# Get seller's orders
seller_orders = order_service.get_seller_orders('seller123')

# Update order status with history tracking
order_service.update_order_status(
    order_id='order123',
    new_status='confirmed',
    updated_by='seller123'
)
```

### User Service

```python
from firebase_service import user_service

# Create user
user_id = user_service.create({
    'email': 'user@example.com',
    'phone': '+27821234567',
    'password_hash': 'hashed_password_here',
    'full_name': 'John Doe',
    'user_type': 'buyer',
    'status': 'active',
    'spz_balance': 1500.00,
    'email_verified': False,
    'phone_verified': False,
    'kyc_status': 'pending'
})

# Get user by email
user = user_service.get_by_email('user@example.com')

# Get user by phone
user = user_service.get_by_phone('+27821234567')

# Update SPZ balance (atomic operation)
user_service.update_spz_balance(
    user_id='user123',
    amount=500.00,
    transaction_type='credit'  # or 'debit'
)
```

### Delivery Service (Real-time Tracking)

```python
from firebase_service import delivery_service

# Create delivery
delivery_id = delivery_service.create({
    'order_id': 'order123',
    'deliverer_id': 'driver123',
    'status': 'assigned',
    'pickup_address': 'Seller Location',
    'delivery_address': 'Buyer Location',
    'distance_km': 12.5,
    'delivery_fee': 150.00,
    'current_location': {
        'latitude': -26.2041,
        'longitude': 28.0473,
        'timestamp': None
    }
})

# Update location (real-time tracking)
delivery_service.update_location(
    delivery_id='delivery123',
    latitude=-26.2050,
    longitude=28.0480
)

# Get active deliveries
active = delivery_service.get_active_deliveries('driver123')

# Get location history
history = delivery_service.get_delivery_history('delivery123')
```

### Notification Service

```python
from firebase_service import notification_service

# Create notification
notif_id = notification_service.create_notification(
    user_id='user123',
    title='Order Confirmed',
    message='Your order #12345 has been confirmed',
    notification_type='order',
    data={'order_id': 'order123'}
)

# Get user notifications
all_notifs = notification_service.get_user_notifications('user123')
unread = notification_service.get_user_notifications('user123', unread_only=True)

# Mark as read
notification_service.mark_as_read('notif123')

# Mark all as read
notification_service.mark_all_read('user123')
```

### Storage Service

```python
from firebase_service import storage_service

# Upload product image
image_url = storage_service.upload_file(
    file_path='/tmp/product_image.jpg',
    destination_path='products/prod123/main.jpg',
    content_type='image/jpeg'
)
# Returns: https://storage.googleapis.com/your-bucket/products/prod123/main.jpg

# Upload from string
text_url = storage_service.upload_from_string(
    content='Product description...',
    destination_path='products/prod123/description.txt',
    content_type='text/plain'
)

# Delete file
storage_service.delete_file('products/prod123/old_image.jpg')

# Get file URL
url = storage_service.get_file_url('products/prod123/main.jpg')
```

---

## 📊 Data Migration

### Migrate All Data from SQLite to Firebase

```bash
# Dry run (test without writing)
python migrate_to_firebase.py --all --dry-run

# Actually migrate
python migrate_to_firebase.py --all

# Migrate specific tables
python migrate_to_firebase.py --tables users products orders

# Custom database path
python migrate_to_firebase.py --all --db /path/to/custom.db

# Custom service account
python migrate_to_firebase.py --all --service-account /path/to/key.json
```

### Migration Output

```
🚀 Starting complete migration from SQLite to Firebase...

📊 Migrating users...
  ✓ Migrated user: user1@example.com
  ✓ Migrated user: user2@example.com
✓ Users migrated: 2/2

📦 Migrating products...
  ✓ Migrated product: iPhone 15 Pro
  ✓ Migrated product: Samsung Galaxy S24
✓ Products migrated: 2/2

============================================================
📊 MIGRATION SUMMARY
============================================================
USERS                    2/2    migrated
PRODUCTS                 2/2    migrated
ORDERS                   5/5    migrated
DELIVERIES               3/3    migrated
NOTIFICATIONS           10/10   migrated
============================================================
TOTAL                   22/22   migrated
============================================================

✓ Migration complete!
```

---

## 💡 Example Usage in Flask Routes

### Product Listing Route

```python
from flask import Blueprint, render_template, request
from firebase_service import product_service

marketplace_bp = Blueprint('marketplace', __name__)

@marketplace_bp.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('search')

    if search:
        products = product_service.search_products(search)
    elif category:
        products = product_service.get_active_products(category=category)
    else:
        products = product_service.get_active_products(limit=50)

    return render_template('products.html', products=products)
```

### Order Creation Route

```python
from flask import Blueprint, session, request, redirect, flash
from firebase_service import order_service, user_service

@marketplace_bp.route('/checkout', methods=['POST'])
def checkout():
    user_id = session['user']['id']

    # Create order
    order_data = {
        'user_id': user_id,
        'seller_id': request.form['seller_id'],
        'status': 'pending',
        'payment_method': request.form['payment_method'],
        'total_zar': float(request.form['total']),
        'delivery_address': request.form['address'],
        'items': session.get('cart_items', [])
    }

    order_id = order_service.create(order_data)

    # Deduct SPZ balance if using tokens
    if request.form['payment_method'] == 'SPZ':
        user_service.update_spz_balance(
            user_id=user_id,
            amount=float(request.form['total']),
            transaction_type='debit'
        )

    flash('Order placed successfully!', 'success')
    return redirect(f'/orders/{order_id}')
```

### Real-time Delivery Tracking

```python
from flask import Blueprint, jsonify
from firebase_service import delivery_service

@marketplace_bp.route('/api/delivery/<delivery_id>/location')
def get_delivery_location(delivery_id):
    delivery = delivery_service.get(delivery_id)

    if delivery:
        return jsonify({
            'current_location': delivery['current_location'],
            'status': delivery['status']
        })

    return jsonify({'error': 'Delivery not found'}), 404
```

---

## ✅ Best Practices

### 1. Denormalize Data for Performance

```python
# ❌ BAD: Separate documents requiring multiple reads
order = order_service.get('order123')
for item in order['item_ids']:
    product = product_service.get(item)  # Multiple reads!

# ✅ GOOD: Embed item data in order
order_data = {
    'items': [
        {
            'product_id': 'prod123',
            'product_name': 'iPhone 15',  # Denormalized
            'quantity': 1,
            'price': 15999.00
        }
    ]
}
```

### 2. Use Transactions for Critical Operations

```python
from google.cloud import firestore

db = get_firestore_db()

@firestore.transactional
def transfer_spz(transaction, from_user_id, to_user_id, amount):
    # Read phase
    from_ref = db.collection('users').document(from_user_id)
    to_ref = db.collection('users').document(to_user_id)

    from_user = from_ref.get(transaction=transaction).to_dict()
    to_user = to_ref.get(transaction=transaction).to_dict()

    # Validate
    if from_user['spz_balance'] < amount:
        raise ValueError("Insufficient balance")

    # Write phase
    transaction.update(from_ref, {
        'spz_balance': from_user['spz_balance'] - amount
    })
    transaction.update(to_ref, {
        'spz_balance': to_user['spz_balance'] + amount
    })

# Use it
transaction = db.transaction()
transfer_spz(transaction, 'user1', 'user2', 100.00)
```

### 3. Implement Proper Indexing

In Firebase Console → Firestore → Indexes, create composite indexes for common queries:

```
Collection: products
Fields: [status: Ascending, category: Ascending, created_at: Descending]

Collection: orders
Fields: [user_id: Ascending, status: Ascending, created_at: Descending]
```

### 4. Use Batch Writes for Bulk Operations

```python
from firebase_config import get_firestore_db

db = get_firestore_db()
batch = db.batch()

# Add multiple operations
for product in products_to_update:
    doc_ref = db.collection('products').document(product['id'])
    batch.update(doc_ref, {'status': 'inactive'})

# Commit all at once
batch.commit()
```

### 5. Security Rules (Set in Firebase Console)

```javascript
// Firestore Security Rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
    }

    // Anyone can read active products
    match /products/{productId} {
      allow read: if resource.data.status == 'active';
      allow write: if request.auth.uid == resource.data.seller_id;
    }

    // Orders - user or seller can read
    match /orders/{orderId} {
      allow read: if request.auth.uid == resource.data.user_id ||
                     request.auth.uid == resource.data.seller_id;
    }
  }
}
```

---

## 🛠️ Troubleshooting

### Problem: "Firebase initialization failed"

**Solution**: Check that:
1. `FIREBASE_SERVICE_ACCOUNT` path is correct
2. The JSON file exists and is valid
3. Environment variable is set correctly

```bash
# Verify file exists
ls -la firebase-service-account.json

# Check environment variable
echo $FIREBASE_SERVICE_ACCOUNT
```

### Problem: "Permission denied" errors

**Solution**: Check Firestore Security Rules in Firebase Console

### Problem: "Quota exceeded" errors

**Solution**:
- Free tier: 50K reads/day, 20K writes/day
- Upgrade to Blaze (pay-as-you-go) plan
- Implement caching to reduce reads

### Problem: Slow queries

**Solution**:
1. Check Firebase Console for missing indexes
2. Create composite indexes for complex queries
3. Consider denormalizing data to reduce reads

### Problem: Migration fails midway

**Solution**:
```bash
# Use --dry-run first to test
python migrate_to_firebase.py --all --dry-run

# Migrate in batches
python migrate_to_firebase.py --tables users
python migrate_to_firebase.py --tables products
python migrate_to_firebase.py --tables orders
```

---

## 📚 Additional Resources

- [Firebase Admin SDK Documentation](https://firebase.google.com/docs/admin/setup)
- [Firestore Data Model](https://firebase.google.com/docs/firestore/data-model)
- [Firebase Storage Guide](https://firebase.google.com/docs/storage)
- [Security Rules Documentation](https://firebase.google.com/docs/firestore/security/get-started)

---

## 🎯 Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Download Firebase service account JSON
3. ✅ Configure environment variables
4. ✅ Test Firebase connection
5. ✅ Run migration (dry-run first)
6. ✅ Update routes to use Firebase services
7. ✅ Test application thoroughly
8. ✅ Set up Firestore security rules
9. ✅ Monitor usage in Firebase Console

---

**Need Help?** Check the [Firebase documentation](https://firebase.google.com/docs) or open an issue in the project repository.
