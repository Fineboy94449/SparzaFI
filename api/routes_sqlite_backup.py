"""
SparzaFi API Routes
RESTful API endpoints for fintech operations and mobile applications
"""

from flask import request, jsonify, session
from functools import wraps
import jwt
import secrets
from datetime import datetime, timedelta
from . import api_bp
from config import Config
from database_seed import get_db_connection


# ==================== API AUTHENTICATION ====================

def generate_jwt_token(user_id, email, user_type):
    """Generate JWT token for API authentication"""
    payload = {
        'user_id': user_id,
        'email': email,
        'user_type': user_type,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')


def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def api_login_required(f):
    """Decorator for API authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'No token provided', 'code': 'NO_TOKEN'}), 401

        # Remove "Bearer " prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token', 'code': 'INVALID_TOKEN'}), 401

        # Attach user info to request
        request.user_id = payload['user_id']
        request.user_email = payload['email']
        request.user_type = payload['user_type']

        return f(*args, **kwargs)
    return decorated_function


# ==================== API AUTHENTICATION ENDPOINTS ====================

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """API login endpoint - returns JWT token"""
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    email = data['email']
    password = data['password']

    # Import hash_password from database_seed
    from database_seed import hash_password
    password_hash = hash_password(password)

    db = get_db_connection()
    user = db.execute(
        'SELECT id, email, user_type, kyc_completed, is_verified FROM users WHERE email = ? AND password_hash = ?',
        (email, password_hash)
    ).fetchone()

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate JWT token
    token = generate_jwt_token(user['id'], user['email'], user['user_type'])

    # Update last login
    db.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user['id']))
    db.commit()

    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'user_type': user['user_type'],
            'kyc_completed': bool(user['kyc_completed']),
            'is_verified': bool(user['is_verified'])
        }
    }), 200


@api_bp.route('/auth/verify', methods=['GET'])
@api_login_required
def api_verify_token():
    """Verify if token is still valid"""
    return jsonify({
        'success': True,
        'user_id': request.user_id,
        'email': request.user_email,
        'user_type': request.user_type
    }), 200


# ==================== FINTECH API ENDPOINTS ====================

@api_bp.route('/fintech/balance', methods=['GET'])
@api_login_required
def get_token_balance():
    """Get user's SPZ token balance"""
    db = get_db_connection()
    user = db.execute(
        'SELECT token_balance, loyalty_points FROM users WHERE id = ?',
        (request.user_id,)
    ).fetchone()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'success': True,
        'balance': {
            'spz': float(user['token_balance']),
            'zar_equivalent': float(user['token_balance']) * Config.SPZ_TO_RAND_RATE,
            'loyalty_points': float(user['loyalty_points'])
        },
        'token_symbol': Config.TOKEN_SYMBOL,
        'token_name': Config.TOKEN_NAME,
        'exchange_rate': Config.SPZ_TO_RAND_RATE
    }), 200


@api_bp.route('/fintech/transfer', methods=['POST'])
@api_login_required
def transfer_tokens():
    """Transfer SPZ tokens to another user"""
    data = request.get_json()

    if not data or not data.get('recipient_email') or not data.get('amount'):
        return jsonify({'error': 'Recipient email and amount required'}), 400

    recipient_email = data['recipient_email']
    amount = float(data['amount'])
    notes = data.get('notes', '')

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    db = get_db_connection()

    # Get sender balance
    sender = db.execute(
        'SELECT token_balance FROM users WHERE id = ?',
        (request.user_id,)
    ).fetchone()

    if not sender or sender['token_balance'] < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    # Get recipient
    recipient = db.execute(
        'SELECT id, email FROM users WHERE email = ?',
        (recipient_email,)
    ).fetchone()

    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    if recipient['id'] == request.user_id:
        return jsonify({'error': 'Cannot transfer to yourself'}), 400

    # Generate transaction reference
    from database_seed import generate_reference_id
    reference_id = generate_reference_id('TRF')

    try:
        # Deduct from sender
        db.execute(
            'UPDATE users SET token_balance = token_balance - ? WHERE id = ?',
            (amount, request.user_id)
        )

        # Add to recipient
        db.execute(
            'UPDATE users SET token_balance = token_balance + ? WHERE id = ?',
            (amount, recipient['id'])
        )

        # Record transaction
        db.execute('''
            INSERT INTO token_transactions
            (from_user_id, to_user_id, amount, transaction_type, status, reference_id, notes, completed_at)
            VALUES (?, ?, ?, 'transfer', 'completed', ?, ?, ?)
        ''', (request.user_id, recipient['id'], amount, reference_id, notes, datetime.now()))

        transaction_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Record balance history for sender
        db.execute('''
            INSERT INTO token_balances_history
            (user_id, previous_balance, new_balance, change_amount, transaction_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (request.user_id, sender['token_balance'], sender['token_balance'] - amount, -amount, transaction_id))

        # Record balance history for recipient
        recipient_balance = db.execute('SELECT token_balance FROM users WHERE id = ?', (recipient['id'],)).fetchone()
        db.execute('''
            INSERT INTO token_balances_history
            (user_id, previous_balance, new_balance, change_amount, transaction_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (recipient['id'], recipient_balance['token_balance'] - amount, recipient_balance['token_balance'], amount, transaction_id))

        db.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully transferred {amount} {Config.TOKEN_SYMBOL} to {recipient_email}',
            'transaction': {
                'reference_id': reference_id,
                'amount': amount,
                'recipient': recipient_email,
                'timestamp': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': 'Transfer failed', 'details': str(e)}), 500


@api_bp.route('/fintech/deposit', methods=['POST'])
@api_login_required
def deposit_tokens():
    """Deposit SPZ tokens (mock EFT top-up)"""
    data = request.get_json()

    if not data or not data.get('amount'):
        return jsonify({'error': 'Amount required'}), 400

    amount = float(data['amount'])
    payment_reference = data.get('payment_reference', f'EFT-{secrets.token_hex(8).upper()}')

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    if amount > 10000:
        return jsonify({'error': 'Maximum deposit amount is 10,000 SPZ'}), 400

    db = get_db_connection()

    # Get current balance
    user = db.execute(
        'SELECT token_balance FROM users WHERE id = ?',
        (request.user_id,)
    ).fetchone()

    # Generate transaction reference
    from database_seed import generate_reference_id
    reference_id = generate_reference_id('DEP')

    try:
        # Add to user balance
        db.execute(
            'UPDATE users SET token_balance = token_balance + ? WHERE id = ?',
            (amount, request.user_id)
        )

        # Record transaction
        db.execute('''
            INSERT INTO token_transactions
            (to_user_id, amount, transaction_type, status, reference_id, payment_reference, completed_at)
            VALUES (?, ?, 'deposit', 'completed', ?, ?, ?)
        ''', (request.user_id, amount, reference_id, payment_reference, datetime.now()))

        transaction_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Record balance history
        db.execute('''
            INSERT INTO token_balances_history
            (user_id, previous_balance, new_balance, change_amount, transaction_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (request.user_id, user['token_balance'], user['token_balance'] + amount, amount, transaction_id))

        db.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully deposited {amount} {Config.TOKEN_SYMBOL}',
            'transaction': {
                'reference_id': reference_id,
                'payment_reference': payment_reference,
                'amount': amount,
                'timestamp': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': 'Deposit failed', 'details': str(e)}), 500


@api_bp.route('/fintech/withdraw', methods=['POST'])
@api_login_required
def withdraw_tokens():
    """Request withdrawal of SPZ tokens to bank account"""
    data = request.get_json()

    required_fields = ['amount', 'bank_name', 'account_number', 'account_holder']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    amount_spz = float(data['amount'])
    bank_name = data['bank_name']
    account_number = data['account_number']
    account_holder = data['account_holder']

    if amount_spz <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    if amount_spz < 100:
        return jsonify({'error': 'Minimum withdrawal amount is 100 SPZ'}), 400

    db = get_db_connection()

    # Check balance
    user = db.execute(
        'SELECT token_balance FROM users WHERE id = ?',
        (request.user_id,)
    ).fetchone()

    if not user or user['token_balance'] < amount_spz:
        return jsonify({'error': 'Insufficient balance'}), 400

    amount_zar = amount_spz * Config.SPZ_TO_RAND_RATE

    try:
        # Deduct from user balance (hold funds)
        db.execute(
            'UPDATE users SET token_balance = token_balance - ? WHERE id = ?',
            (amount_spz, request.user_id)
        )

        # Create withdrawal request
        db.execute('''
            INSERT INTO withdrawal_requests
            (user_id, amount_spz, amount_zar, bank_name, account_number, account_holder, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (request.user_id, amount_spz, amount_zar, bank_name, account_number, account_holder))

        request_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Record transaction
        from database_seed import generate_reference_id
        reference_id = generate_reference_id('WTH')

        db.execute('''
            INSERT INTO token_transactions
            (from_user_id, amount, transaction_type, status, reference_id, notes)
            VALUES (?, ?, 'withdrawal', 'pending', ?, ?)
        ''', (request.user_id, amount_spz, reference_id, f'Withdrawal to {bank_name} - {account_number}'))

        db.commit()

        return jsonify({
            'success': True,
            'message': 'Withdrawal request submitted successfully',
            'request': {
                'request_id': request_id,
                'reference_id': reference_id,
                'amount_spz': amount_spz,
                'amount_zar': amount_zar,
                'status': 'pending',
                'bank_name': bank_name,
                'processing_time': '1-3 business days'
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': 'Withdrawal request failed', 'details': str(e)}), 500


@api_bp.route('/fintech/transactions', methods=['GET'])
@api_login_required
def get_transactions():
    """Get user's transaction history"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    transaction_type = request.args.get('type', None)

    db = get_db_connection()

    # Build query
    query = '''
        SELECT
            id, from_user_id, to_user_id, amount, transaction_type, status,
            reference_id, payment_reference, notes, created_at, completed_at
        FROM token_transactions
        WHERE from_user_id = ? OR to_user_id = ?
    '''
    params = [request.user_id, request.user_id]

    if transaction_type:
        query += ' AND transaction_type = ?'
        params.append(transaction_type)

    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    transactions = db.execute(query, params).fetchall()

    # Format transactions
    result = []
    for txn in transactions:
        direction = 'outgoing' if txn['from_user_id'] == request.user_id else 'incoming'

        result.append({
            'id': txn['id'],
            'reference_id': txn['reference_id'],
            'amount': float(txn['amount']),
            'type': txn['transaction_type'],
            'status': txn['status'],
            'direction': direction,
            'payment_reference': txn['payment_reference'],
            'notes': txn['notes'],
            'created_at': txn['created_at'],
            'completed_at': txn['completed_at']
        })

    return jsonify({
        'success': True,
        'transactions': result,
        'count': len(result),
        'limit': limit,
        'offset': offset
    }), 200


# ==================== MARKETPLACE API ENDPOINTS ====================

@api_bp.route('/marketplace/products', methods=['GET'])
def get_products():
    """Get marketplace products (public endpoint)"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    category = request.args.get('category', None)
    search = request.args.get('search', None)

    db = get_db_connection()

    query = '''
        SELECT
            p.id, p.name, p.description, p.category, p.price, p.original_price,
            p.stock_count, p.images, p.avg_rating, p.total_reviews,
            s.id as seller_id, s.name as seller_name, s.handle as seller_handle,
            s.is_subscribed, s.verification_status
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.is_active = 1
    '''
    params = []

    if category:
        query += ' AND p.category = ?'
        params.append(category)

    if search:
        query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    query += ' ORDER BY p.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    products = db.execute(query, params).fetchall()

    # Format products
    result = []
    for p in products:
        result.append({
            'id': p['id'],
            'name': p['name'],
            'description': p['description'],
            'category': p['category'],
            'price': float(p['price']),
            'original_price': float(p['original_price']) if p['original_price'] else None,
            'stock_count': p['stock_count'],
            'images': eval(p['images']) if p['images'] else [],
            'rating': float(p['avg_rating']) if p['avg_rating'] else 0,
            'reviews_count': p['total_reviews'],
            'seller': {
                'id': p['seller_id'],
                'name': p['seller_name'],
                'handle': p['seller_handle'],
                'is_subscribed': bool(p['is_subscribed']),
                'is_verified': p['verification_status'] == 'verified'
            }
        })

    return jsonify({
        'success': True,
        'products': result,
        'count': len(result),
        'limit': limit,
        'offset': offset
    }), 200


@api_bp.route('/marketplace/product/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """Get detailed product information"""
    db = get_db_connection()

    product = db.execute('''
        SELECT
            p.*,
            s.id as seller_id, s.name as seller_name, s.handle as seller_handle,
            s.location as seller_location, s.avg_rating as seller_rating,
            s.verification_status
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.id = ? AND p.is_active = 1
    ''', (product_id,)).fetchone()

    if not product:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'success': True,
        'product': {
            'id': product['id'],
            'name': product['name'],
            'description': product['description'],
            'category': product['category'],
            'price': float(product['price']),
            'original_price': float(product['original_price']) if product['original_price'] else None,
            'stock_count': product['stock_count'],
            'sku': product['sku'],
            'images': eval(product['images']) if product['images'] else [],
            'rating': float(product['avg_rating']) if product['avg_rating'] else 0,
            'reviews_count': product['total_reviews'],
            'seller': {
                'id': product['seller_id'],
                'name': product['seller_name'],
                'handle': product['seller_handle'],
                'location': product['seller_location'],
                'rating': float(product['seller_rating']) if product['seller_rating'] else 0,
                'is_verified': product['verification_status'] == 'verified'
            }
        }
    }), 200


# ==================== ERROR HANDLERS ====================

@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint not found', 'code': 'NOT_FOUND'}), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
