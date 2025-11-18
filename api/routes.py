"""
SparzaFi API Routes - Migrated to Firebase
RESTful API endpoints for fintech operations and mobile applications
"""

from flask import request, jsonify
from functools import wraps
import jwt
import secrets
from datetime import datetime, timedelta
from . import api_bp
from config import Config

# Firebase imports
from firebase_db import (
    get_user_service,
    transaction_service,
    get_product_service,
    seller_service
)
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


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

    # Import hash_password from shared utils
    from shared.utils import hash_password
    password_hash = hash_password(password)

    user_service = get_user_service()

    # Get user by email
    user = user_service.get_by_email(email)

    if not user or user.get('password_hash') != password_hash:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate JWT token
    token = generate_jwt_token(user['id'], user['email'], user.get('user_type', 'buyer'))

    # Update last login
    user_service.update(user['id'], {'last_login': firestore.SERVER_TIMESTAMP})

    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'user_type': user.get('user_type', 'buyer'),
            'kyc_completed': bool(user.get('kyc_completed', False)),
            'is_verified': bool(user.get('is_verified', False))
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
    user_service = get_user_service()
    user = user_service.get(request.user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'success': True,
        'balance': {
            'spz': float(user.get('token_balance', 0)),
            'zar_equivalent': float(user.get('token_balance', 0)) * Config.SPZ_TO_RAND_RATE,
            'loyalty_points': float(user.get('loyalty_points', 0))
        },
        'token_symbol': Config.TOKEN_SYMBOL,
        'token_name': Config.TOKEN_NAME,
        'exchange_rate': Config.SPZ_TO_RAND_RATE
    }), 200


@api_bp.route('/fintech/transfer', methods=['POST'])
@api_login_required
def transfer_tokens_api():
    """Transfer SPZ tokens to another user"""
    data = request.get_json()

    if not data or not data.get('recipient_email') or not data.get('amount'):
        return jsonify({'error': 'Recipient email and amount required'}), 400

    recipient_email = data['recipient_email']
    amount = float(data['amount'])
    notes = data.get('notes', '')

    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    user_service = get_user_service()
    db = get_firestore_db()

    # Get sender balance
    sender = user_service.get(request.user_id)

    if not sender or sender.get('token_balance', 0) < amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    # Get recipient
    recipient = user_service.get_by_email(recipient_email)

    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    if recipient['id'] == request.user_id:
        return jsonify({'error': 'Cannot transfer to yourself'}), 400

    # Generate transaction reference
    from shared.utils import generate_reference_id
    reference_id = generate_reference_id('TRF')

    try:
        # Deduct from sender
        new_sender_balance = sender['token_balance'] - amount
        user_service.update(request.user_id, {'token_balance': new_sender_balance})

        # Add to recipient
        new_recipient_balance = recipient.get('token_balance', 0) + amount
        user_service.update(recipient['id'], {'token_balance': new_recipient_balance})

        # Record transaction
        transaction_data = {
            'from_user_id': request.user_id,
            'to_user_id': recipient['id'],
            'amount': amount,
            'transaction_type': 'transfer',
            'status': 'completed',
            'reference_id': reference_id,
            'notes': notes,
            'completed_at': firestore.SERVER_TIMESTAMP
        }

        trans_ref = db.collection('token_transactions').add(transaction_data)
        transaction_id = trans_ref[1].id

        # Record balance history for sender
        db.collection('token_balances_history').add({
            'user_id': request.user_id,
            'previous_balance': sender['token_balance'],
            'new_balance': new_sender_balance,
            'change_amount': -amount,
            'transaction_id': transaction_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })

        # Record balance history for recipient
        db.collection('token_balances_history').add({
            'user_id': recipient['id'],
            'previous_balance': recipient.get('token_balance', 0),
            'new_balance': new_recipient_balance,
            'change_amount': amount,
            'transaction_id': transaction_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })

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

    user_service = get_user_service()
    db = get_firestore_db()

    # Get current balance
    user = user_service.get(request.user_id)

    # Generate transaction reference
    from shared.utils import generate_reference_id
    reference_id = generate_reference_id('DEP')

    try:
        # Add to user balance
        new_balance = user.get('token_balance', 0) + amount
        user_service.update(request.user_id, {'token_balance': new_balance})

        # Record transaction
        transaction_data = {
            'to_user_id': request.user_id,
            'amount': amount,
            'transaction_type': 'deposit',
            'status': 'completed',
            'reference_id': reference_id,
            'payment_reference': payment_reference,
            'completed_at': firestore.SERVER_TIMESTAMP
        }

        trans_ref = db.collection('token_transactions').add(transaction_data)
        transaction_id = trans_ref[1].id

        # Record balance history
        db.collection('token_balances_history').add({
            'user_id': request.user_id,
            'previous_balance': user.get('token_balance', 0),
            'new_balance': new_balance,
            'change_amount': amount,
            'transaction_id': transaction_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })

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

    user_service = get_user_service()
    db = get_firestore_db()

    # Check balance
    user = user_service.get(request.user_id)

    if not user or user.get('token_balance', 0) < amount_spz:
        return jsonify({'error': 'Insufficient balance'}), 400

    amount_zar = amount_spz * Config.SPZ_TO_RAND_RATE

    try:
        # Deduct from user balance (hold funds)
        new_balance = user['token_balance'] - amount_spz
        user_service.update(request.user_id, {'token_balance': new_balance})

        # Create withdrawal request
        withdrawal_data = {
            'user_id': request.user_id,
            'amount_spz': amount_spz,
            'amount_zar': amount_zar,
            'bank_name': bank_name,
            'account_number': account_number,
            'account_holder': account_holder,
            'status': 'pending',
            'created_at': firestore.SERVER_TIMESTAMP
        }

        withdrawal_ref = db.collection('withdrawal_requests').add(withdrawal_data)
        request_id = withdrawal_ref[1].id

        # Record transaction
        from shared.utils import generate_reference_id
        reference_id = generate_reference_id('WTH')

        db.collection('token_transactions').add({
            'from_user_id': request.user_id,
            'amount': amount_spz,
            'transaction_type': 'withdrawal',
            'status': 'pending',
            'reference_id': reference_id,
            'notes': f'Withdrawal to {bank_name} - {account_number}',
            'created_at': firestore.SERVER_TIMESTAMP
        })

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
        return jsonify({'error': 'Withdrawal request failed', 'details': str(e)}), 500


@api_bp.route('/fintech/transactions', methods=['GET'])
@api_login_required
def get_transactions():
    """Get user's transaction history"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    transaction_type = request.args.get('type', None)

    db = get_firestore_db()

    # Query transactions where user is sender or recipient
    query1 = db.collection('token_transactions').where(
        filter=FieldFilter('from_user_id', '==', request.user_id)
    )

    query2 = db.collection('token_transactions').where(
        filter=FieldFilter('to_user_id', '==', request.user_id)
    )

    # Apply type filter if provided
    if transaction_type:
        query1 = query1.where(filter=FieldFilter('transaction_type', '==', transaction_type))
        query2 = query2.where(filter=FieldFilter('transaction_type', '==', transaction_type))

    # Get results
    transactions = []
    for doc in query1.stream():
        transactions.append({**doc.to_dict(), 'id': doc.id})
    for doc in query2.stream():
        transactions.append({**doc.to_dict(), 'id': doc.id})

    # Sort by created_at
    transactions.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Apply pagination
    paginated = transactions[offset:offset + limit]

    # Format transactions
    result = []
    for txn in paginated:
        direction = 'outgoing' if txn.get('from_user_id') == request.user_id else 'incoming'

        result.append({
            'id': txn.get('id'),
            'reference_id': txn.get('reference_id'),
            'amount': float(txn.get('amount', 0)),
            'type': txn.get('transaction_type'),
            'status': txn.get('status'),
            'direction': direction,
            'payment_reference': txn.get('payment_reference'),
            'notes': txn.get('notes'),
            'created_at': txn.get('created_at'),
            'completed_at': txn.get('completed_at')
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

    product_service = get_product_service()

    # Get all active products
    all_products = product_service.get_all()
    active_products = [p for p in all_products if p.get('is_active', True)]

    # Filter by category
    if category:
        active_products = [p for p in active_products if p.get('category') == category]

    # Filter by search
    if search:
        search_lower = search.lower()
        active_products = [
            p for p in active_products
            if search_lower in p.get('name', '').lower() or search_lower in p.get('description', '').lower()
        ]

    # Sort by created_at
    active_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Apply pagination
    paginated = active_products[offset:offset + limit]

    # Format products with seller info
    result = []
    for p in paginated:
        seller = seller_service.get(p.get('seller_id')) if p.get('seller_id') else None

        result.append({
            'id': p.get('id'),
            'name': p.get('name'),
            'description': p.get('description'),
            'category': p.get('category'),
            'price': float(p.get('price', 0)),
            'original_price': float(p.get('original_price')) if p.get('original_price') else None,
            'stock_count': p.get('stock_count'),
            'images': p.get('images', []),
            'rating': float(p.get('avg_rating', 0)),
            'reviews_count': p.get('total_reviews', 0),
            'seller': {
                'id': seller.get('id') if seller else None,
                'name': seller.get('name') if seller else '',
                'handle': seller.get('handle') if seller else '',
                'is_subscribed': bool(seller.get('is_subscribed')) if seller else False,
                'is_verified': seller.get('verification_status') == 'verified' if seller else False
            } if seller else None
        })

    return jsonify({
        'success': True,
        'products': result,
        'count': len(result),
        'limit': limit,
        'offset': offset
    }), 200


@api_bp.route('/marketplace/product/<product_id>', methods=['GET'])
def get_product_detail(product_id):
    """Get detailed product information"""
    product_service = get_product_service()

    product = product_service.get(product_id)

    if not product or not product.get('is_active', True):
        return jsonify({'error': 'Product not found'}), 404

    # Get seller info
    seller = seller_service.get(product.get('seller_id')) if product.get('seller_id') else None

    return jsonify({
        'success': True,
        'product': {
            'id': product.get('id'),
            'name': product.get('name'),
            'description': product.get('description'),
            'category': product.get('category'),
            'price': float(product.get('price', 0)),
            'original_price': float(product.get('original_price')) if product.get('original_price') else None,
            'stock_count': product.get('stock_count'),
            'sku': product.get('sku'),
            'images': product.get('images', []),
            'rating': float(product.get('avg_rating', 0)),
            'reviews_count': product.get('total_reviews', 0),
            'seller': {
                'id': seller.get('id') if seller else None,
                'name': seller.get('name') if seller else '',
                'handle': seller.get('handle') if seller else '',
                'location': seller.get('location') if seller else '',
                'rating': float(seller.get('avg_rating', 0)) if seller else 0,
                'is_verified': seller.get('verification_status') == 'verified' if seller else False
            } if seller else None
        }
    }), 200


# ==================== ERROR HANDLERS ====================

@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint not found', 'code': 'NOT_FOUND'}), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error', 'code': 'SERVER_ERROR'}), 500
