"""
SparzaFi Shared Utilities
Common functions used across the application
Now using Firebase Firestore
"""

import hashlib
import secrets
import random
import string
import os
from functools import wraps
from flask import session, redirect, url_for, abort, current_app, g

# Firebase imports
from firebase_db import get_user_service, transaction_service, withdrawal_service
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


# ============================================================================
# DATABASE HELPERS (Now using Firebase)
# ============================================================================

def get_db():
    """Get Firebase Firestore client (replaces SQLite connection)"""
    return get_firestore_db()


def get_user_by_id(user_id):
    """Get user by ID from Firebase"""
    user_service = get_user_service()
    return user_service.get(user_id)


def get_user_by_email(email):
    """Get user by email from Firebase"""
    user_service = get_user_service()
    return user_service.get_by_email(email)


# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

def hash_password(password):
    """Hashes password using SHA256 with salt"""
    salt = current_app.config['PASSWORD_SALT']
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def check_password(hashed_password, provided_password):
    """Checks provided password against stored hash"""
    return hashed_password == hash_password(provided_password)


def generate_referral_code(length=8):
    """Generates a unique referral code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


def generate_verification_code(length=6):
    """Generates a numeric verification code"""
    return ''.join(random.choices(string.digits, k=length))


# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Handle AJAX/JSON requests differently
            from flask import request, jsonify
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Login required'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('is_admin') != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def seller_required(f):
    """Decorator to require seller access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('user_type') not in ['seller', 'admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def driver_required(f):
    """Decorator to require driver access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('user_type') not in ['driver', 'admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def kyc_required(f):
    """Decorator to require KYC completion"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or not user.get('kyc_verified'):
            return redirect(url_for('auth.kyc'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# CART MANAGEMENT
# ============================================================================

def get_cart_count():
    """Returns cart item count"""
    return sum(item['quantity'] for item in session.get('cart', {}).values())


def calculate_cart_summary():
    """Calculates subtotal, tax, fees, and total"""
    cart_items = session.get('cart', {})
    subtotal = 0.0
    
    for item_id, item_data in cart_items.items():
        price = item_data['product']['price']
        quantity = item_data['quantity']
        subtotal += price * quantity
    
    driver_fee = subtotal * current_app.config['DELIVERER_FEE_RATE']
    commission = subtotal * current_app.config['COMMISSION_RATE']
    tax = subtotal * current_app.config['VAT_RATE']
    
    # Apply discount if promo code exists
    discount = 0.0
    promo_code = session.get('promo_code')
    if promo_code:
        discount = calculate_discount(subtotal, promo_code)
    
    total = subtotal + driver_fee + tax - discount
    
    return {
        'subtotal': f"R{subtotal:.2f}",
        'driver_fee': f"R{driver_fee:.2f}",
        'commission': f"R{commission:.2f}",
        'tax': f"R{tax:.2f}",
        'discount': f"R{discount:.2f}",
        'total': f"R{total:.2f}",
        'raw_subtotal': subtotal,
        'raw_driver_fee': driver_fee,
        'raw_commission': commission,
        'raw_tax': tax,
        'raw_discount': discount,
        'raw_total': total
    }


# ============================================================================
# PROMO CODE & DISCOUNT
# ============================================================================

def calculate_discount(subtotal, promo_code):
    """Calculate discount amount based on promo code (Firebase)"""
    from datetime import datetime

    db = get_firestore_db()

    # Query for active promo code
    promo_query = db.collection('promotions').where(
        filter=FieldFilter('code', '==', promo_code)
    ).where(
        filter=FieldFilter('is_active', '==', True)
    ).where(
        filter=FieldFilter('min_purchase_amount', '<=', subtotal)
    ).limit(1).stream()

    promo = None
    for doc in promo_query:
        promo_data = doc.to_dict()
        promo_data['id'] = doc.id

        # Check expiry
        if promo_data.get('expires_at'):
            if promo_data['expires_at'] <= datetime.utcnow():
                continue

        # Check usage limit
        if promo_data.get('max_uses'):
            if promo_data.get('current_uses', 0) >= promo_data['max_uses']:
                continue

        promo = promo_data
        break

    if not promo:
        return 0.0

    if promo['discount_type'] == 'percentage':
        discount = subtotal * (promo['discount_value'] / 100)
    else:  # fixed
        discount = promo['discount_value']

    return min(discount, subtotal)  # Don't exceed subtotal


def apply_promo_code(promo_code, subtotal):
    """Apply promo code and update usage count (Firebase)"""
    discount = calculate_discount(subtotal, promo_code)

    if discount > 0:
        db = get_firestore_db()

        # Find and update promo code
        promo_query = db.collection('promotions').where(
            filter=FieldFilter('code', '==', promo_code)
        ).limit(1).stream()

        for doc in promo_query:
            doc.reference.update({
                'current_uses': firestore.Increment(1)
            })
            break

        session['promo_code'] = promo_code
        return {'success': True, 'discount': discount}

    return {'success': False, 'error': 'Invalid or expired promo code'}


# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

def generate_reference_id(transaction_type):
    """Generate unique reference ID for token transactions"""
    from datetime import datetime
    prefix = {
        'deposit': 'DEP',
        'withdrawal': 'WTH',
        'transfer': 'TRF',
        'purchase': 'PUR',
        'refund': 'REF',
        'reward': 'RWD'
    }.get(transaction_type, 'TXN')
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(6).upper()}"


def get_user_token_balance(user_id):
    """Get current token balance for user (Firebase)"""
    user_service = get_user_service()
    user = user_service.get(user_id)
    return user.get('spz_balance', 0.0) if user else 0.0


def update_user_token_balance(user_id, amount, transaction_type='deposit', notes=None):
    """Update user token balance and log transaction (Firebase with atomic transaction)"""
    user_service = get_user_service()
    user = user_service.get(user_id)

    if not user:
        return {'success': False, 'error': 'User not found'}

    previous_balance = user.get('spz_balance', 0.0)
    new_balance = previous_balance + amount

    if new_balance < 0:
        return {'success': False, 'error': 'Insufficient balance'}

    reference_id = generate_reference_id(transaction_type)

    try:
        # Update balance atomically
        user_service.update_spz_balance(
            user_id,
            abs(amount),
            'credit' if amount > 0 else 'debit'
        )

        # Log transaction
        transaction_data = {
            'amount': abs(amount),
            'transaction_type': transaction_type,
            'reference_id': reference_id,
            'notes': notes,
            'status': 'completed'
        }

        if amount > 0:
            transaction_data['to_user_id'] = user_id
        else:
            transaction_data['from_user_id'] = user_id

        transaction_service.create(transaction_data)

        return {
            'success': True,
            'reference_id': reference_id,
            'previous_balance': previous_balance,
            'new_balance': new_balance
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# LOYALTY & REWARDS
# ============================================================================

def award_loyalty_points(user_id, purchase_amount):
    """Award loyalty points based on purchase amount (Firebase)"""
    points = purchase_amount * current_app.config['LOYALTY_POINTS_PER_RAND']

    user_service = get_user_service()
    db = get_firestore_db()

    # Update loyalty points atomically
    user_ref = db.collection('users').document(user_id)
    user_ref.update({
        'loyalty_points': firestore.Increment(points),
        'updated_at': firestore.SERVER_TIMESTAMP
    })

    return points


def convert_loyalty_points_to_spz(user_id, points):
    """Convert loyalty points to SPZ tokens (Firebase with transaction)"""
    spz_amount = points / current_app.config.get('POINTS_TO_SPZ_CONVERSION', 100)

    user_service = get_user_service()
    user = user_service.get(user_id)

    if not user or user.get('loyalty_points', 0) < points:
        return {'success': False, 'error': 'Insufficient loyalty points'}

    try:
        db = get_firestore_db()

        # Deduct points atomically
        user_ref = db.collection('users').document(user_id)
        user_ref.update({
            'loyalty_points': firestore.Increment(-points)
        })

        # Add SPZ
        result = update_user_token_balance(
            user_id,
            spz_amount,
            'reward',
            f'Converted {points} loyalty points to SPZ'
        )

        if result['success']:
            return {
                'success': True,
                'points_converted': points,
                'spz_received': spz_amount
            }
        else:
            # Rollback points if SPZ update failed
            user_ref.update({
                'loyalty_points': firestore.Increment(points)
            })
            return result

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# REFERRAL SYSTEM
# ============================================================================

def process_referral(new_user_id, referral_code):
    """Process referral reward when new user signs up (Firebase)"""
    db = get_firestore_db()

    # Find referrer by referral code
    referrer_query = db.collection('users').where(
        filter=FieldFilter('referral_code', '==', referral_code)
    ).limit(1).stream()

    referrer_id = None
    for doc in referrer_query:
        referrer_id = doc.id
        break

    if not referrer_id:
        return {'success': False, 'error': 'Invalid referral code'}

    reward_amount = current_app.config.get('REFERRAL_BONUS_SPZ', 5.0)

    try:
        # Update new user's referred_by field
        user_service = get_user_service()
        user_service.update(new_user_id, {'referred_by': referrer_id})

        # Award SPZ to referrer
        result = update_user_token_balance(
            referrer_id,
            reward_amount,
            'reward',
            f'Referral reward for user {new_user_id}'
        )

        if result['success']:
            return {'success': True, 'reward_amount': reward_amount}
        else:
            return result

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# FILE UPLOAD
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file, folder='general'):
    """Save uploaded file and return the file path"""
    if file and allowed_file(file.filename):
        filename = secrets.token_hex(16) + '_' + file.filename
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return f'/static/uploads/{folder}/{filename}'
    return None


# ============================================================================
# TOKEN TRANSFERS
# ============================================================================

def transfer_tokens(from_user_id, to_user_email, amount, notes=''):
    """Transfer SPZ tokens between users (Firebase with atomic transaction)"""
    from datetime import datetime

    if amount <= 0:
        return {'success': False, 'error': 'Amount must be positive'}

    user_service = get_user_service()
    db = get_firestore_db()

    # Get sender
    sender = user_service.get(from_user_id)
    if not sender or sender.get('spz_balance', 0) < amount:
        return {'success': False, 'error': 'Insufficient balance'}

    # Get recipient by email
    recipient = user_service.get_by_email(to_user_email)
    if not recipient:
        return {'success': False, 'error': 'Recipient not found'}

    if recipient['id'] == from_user_id:
        return {'success': False, 'error': 'Cannot transfer to yourself'}

    # Generate transaction reference
    reference_id = generate_reference_id('transfer')

    try:
        # Perform atomic transfer using Firestore transaction
        @firestore.transactional
        def atomic_transfer(transaction):
            from_ref = db.collection('users').document(from_user_id)
            to_ref = db.collection('users').document(recipient['id'])

            # Read phase
            from_doc = from_ref.get(transaction=transaction)
            to_doc = to_ref.get(transaction=transaction)

            from_balance = from_doc.to_dict().get('spz_balance', 0)
            to_balance = to_doc.to_dict().get('spz_balance', 0)

            # Validate
            if from_balance < amount:
                raise ValueError("Insufficient balance")

            # Write phase - all updates are atomic
            transaction.update(from_ref, {
                'spz_balance': from_balance - amount,
                'updated_at': firestore.SERVER_TIMESTAMP
            })

            transaction.update(to_ref, {
                'spz_balance': to_balance + amount,
                'updated_at': firestore.SERVER_TIMESTAMP
            })

        # Execute atomic transaction
        transaction = db.transaction()
        atomic_transfer(transaction)

        # Record transaction (outside atomic transaction)
        transaction_service.create({
            'from_user_id': from_user_id,
            'to_user_id': recipient['id'],
            'amount': amount,
            'transaction_type': 'transfer',
            'status': 'completed',
            'reference_id': reference_id,
            'notes': notes,
            'completed_at': datetime.utcnow().isoformat()
        })

        return {
            'success': True,
            'reference_id': reference_id,
            'amount': amount,
            'recipient': to_user_email
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# EMAIL NOTIFICATIONS
# ============================================================================

def send_verification_email(email, verification_token):
    """Send email verification link (placeholder for future implementation)"""
    # TODO: Implement with Flask-Mail
    verification_link = f"http://localhost:5000/auth/verify-email?token={verification_token}"
    print(f"📧 Verification email for {email}: {verification_link}")
    return True


def send_password_reset_email(email, reset_token):
    """Send password reset email (placeholder for future implementation)"""
    # TODO: Implement with Flask-Mail
    reset_link = f"http://localhost:5000/auth/reset-password?token={reset_token}"
    print(f"🔐 Password reset email for {email}: {reset_link}")
    return True


# ============================================================================
# NOTIFICATIONS
# ============================================================================

def send_notification(user_id, title, message, notification_type='info'):
    """Send in-app notification to user (Firebase)"""
    from firebase_db import get_notification_service

    notification_service = get_notification_service()
    notification_service.create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )


# ============================================================================
# WITHDRAWAL REQUESTS
# ============================================================================

def submit_withdrawal_request(user_id, amount_spz, bank_name, account_number, account_holder):
    """Submit a withdrawal request to convert SPZ to ZAR (Firebase)"""
    from datetime import datetime
    import uuid

    if amount_spz < 100:
        return {'success': False, 'error': 'Minimum withdrawal amount is 100 SPZ'}

    user_service = get_user_service()
    user = user_service.get(user_id)

    if not user or user.get('spz_balance', 0) < amount_spz:
        return {'success': False, 'error': 'Insufficient balance'}

    amount_zar = amount_spz * current_app.config['SPZ_TO_RAND_RATE']

    try:
        # Deduct from user balance (hold funds) atomically
        user_service.update_spz_balance(user_id, amount_spz, 'debit')

        # Generate IDs
        request_id = str(uuid.uuid4())
        reference_id = generate_reference_id('withdrawal')

        # Create withdrawal request
        withdrawal_service.create({
            'user_id': user_id,
            'amount_spz': amount_spz,
            'amount_zar': amount_zar,
            'bank_name': bank_name,
            'account_number': account_number,
            'account_holder': account_holder,
            'status': 'pending'
        }, doc_id=request_id)

        # Record transaction
        transaction_service.create({
            'from_user_id': user_id,
            'amount': amount_spz,
            'transaction_type': 'withdrawal',
            'status': 'pending',
            'reference_id': reference_id,
            'notes': f'Withdrawal to {bank_name} - {account_number}'
        })

        return {
            'success': True,
            'request_id': request_id,
            'reference_id': reference_id,
            'amount_spz': amount_spz,
            'amount_zar': amount_zar
        }

    except Exception as e:
        # Attempt to rollback balance if withdrawal creation failed
        try:
            user_service.update_spz_balance(user_id, amount_spz, 'credit')
        except:
            pass  # Rollback failed - will need manual intervention

        return {'success': False, 'error': str(e)}


# ============================================================================
# ERROR LOGGING
# ============================================================================

def log_error(error_message, error_type='general', user_id=None):
    """Log error to console and optionally to database"""
    import traceback
    from datetime import datetime

    print(f"❌ ERROR [{error_type}] at {datetime.now()}: {error_message}")

    if traceback:
        print(traceback.format_exc())

    # TODO: Optionally log to database for admin review
    # db = get_db()
    # db.execute("""
    #     INSERT INTO error_logs (error_type, error_message, user_id, stack_trace, created_at)
    #     VALUES (?, ?, ?, ?, ?)
    # """, (error_type, error_message, user_id, traceback.format_exc(), datetime.now()))
    # db.commit()