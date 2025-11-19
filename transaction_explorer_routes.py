"""
SparzaFI Transaction Explorer Routes

Separate explorers for:
- Sellers (view own transactions with filters)
- Buyers (view own purchases with filters)
- Drivers/Deliverers (view assigned deliveries with filters)
- Admin (view ALL transactions with advanced search)
- Public (anonymized transaction data)
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from transaction_explorer_service import get_transaction_explorer_service
from firebase_db import seller_service, deliverer_service, get_user_service
from datetime import datetime


# Create blueprint
explorer_bp = Blueprint('explorer', __name__, url_prefix='/explorer')


# ==================== AUTHENTICATION DECORATORS ====================

def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def seller_required(f):
    """Require user to be a seller"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('user_type') != 'seller':
            flash('Seller access required', 'error')
            return redirect(url_for('marketplace.feed'))
        return f(*args, **kwargs)
    return decorated_function


def driver_required(f):
    """Require user to be a driver/deliverer"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('user_type') != 'deliverer':
            flash('Deliverer access required', 'error')
            return redirect(url_for('marketplace.feed'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Require user to be an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('is_admin') != 1:
            flash('Admin access required', 'error')
            return redirect(url_for('marketplace.feed'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== SELLER TRANSACTION EXPLORER ====================

@explorer_bp.route('/seller')
@login_required
@seller_required
def seller_explorer():
    """
    Seller Transaction Explorer

    Sellers can:
    - View their own transactions
    - Search by: transaction code, buyer address (partial), date range, status, payment method
    - See: buyer address (masked), items, amount, delivery partner, status, pickup code, timestamp
    """
    user = session.get('user')
    user_id = user['id']
    explorer_service = get_transaction_explorer_service()
    user_service = get_user_service()

    # Get seller record
    seller = seller_service.get_by_user_id(user_id)
    if not seller:
        flash('Seller profile not found', 'error')
        return redirect(url_for('marketplace.feed'))

    seller_id = seller['id']

    # Get filters from request
    filters = {
        'transaction_code': request.args.get('transaction_code', '').strip(),
        'buyer_address': request.args.get('buyer_address', '').strip(),
        'date_start': request.args.get('date_start', '').strip(),
        'date_end': request.args.get('date_end', '').strip(),
        'status': request.args.get('status', '').strip(),
        'payment_method': request.args.get('payment_method', '').strip(),
        'limit': int(request.args.get('limit', 50))
    }

    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}

    # Search transactions
    transactions = explorer_service.search_seller_transactions(seller_id, filters)

    # Enhance transactions with additional data
    for transaction in transactions:
        # Mask buyer address (show only partial)
        if transaction.get('delivery_address'):
            address = transaction['delivery_address']
            if len(address) > 20:
                transaction['delivery_address_masked'] = address[:10] + '...' + address[-10:]
            else:
                transaction['delivery_address_masked'] = address

        # Get buyer info (partial)
        if transaction.get('user_id'):
            buyer = user_service.get(transaction['user_id'])
            if buyer:
                # Mask buyer email
                email = buyer.get('email', '')
                if '@' in email:
                    parts = email.split('@')
                    transaction['buyer_email_masked'] = parts[0][:3] + '***@' + parts[1]
                else:
                    transaction['buyer_email_masked'] = 'hidden'

        # Format timestamp
        if transaction.get('immutable_timestamp'):
            transaction['display_timestamp'] = transaction['immutable_timestamp']
        elif transaction.get('timestamp'):
            transaction['display_timestamp'] = transaction['timestamp']

    # Get available statuses and payment methods for filters
    statuses = ['PENDING', 'CONFIRMED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED']
    payment_methods = ['COD', 'EFT', 'SnapScan', 'SPZ', 'Card']

    return render_template('explorer/seller_explorer.html',
                         transactions=transactions,
                         filters=filters,
                         statuses=statuses,
                         payment_methods=payment_methods,
                         seller=seller)


# ==================== BUYER TRANSACTION EXPLORER ====================

@explorer_bp.route('/buyer')
@login_required
def buyer_explorer():
    """
    Buyer Transaction Explorer

    Buyers can:
    - View their own purchases
    - Search by: transaction code, date range, status, delivery method, seller name
    - See: seller name, products, delivery method, driver details (partial), timestamp, transaction code, status, delivery code, payment
    """
    user = session.get('user')
    user_id = user['id']
    explorer_service = get_transaction_explorer_service()

    # Get filters from request
    filters = {
        'transaction_code': request.args.get('transaction_code', '').strip(),
        'date_start': request.args.get('date_start', '').strip(),
        'date_end': request.args.get('date_end', '').strip(),
        'status': request.args.get('status', '').strip(),
        'delivery_method': request.args.get('delivery_method', '').strip(),
        'seller_name': request.args.get('seller_name', '').strip(),
        'limit': int(request.args.get('limit', 50))
    }

    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}

    # Search transactions
    transactions = explorer_service.search_buyer_transactions(user_id, filters)

    # Enhance transactions with additional data
    for transaction in transactions:
        # Get seller info
        if transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller:
                transaction['seller_name'] = seller.get('name', '')
                transaction['seller_handle'] = seller.get('handle', '')

        # Get driver info (partial for privacy)
        if transaction.get('deliverer_id'):
            deliverer = deliverer_service.get(transaction['deliverer_id'])
            if deliverer:
                # Mask driver phone number
                phone = deliverer.get('phone', '')
                if len(phone) > 4:
                    transaction['driver_phone_masked'] = '***' + phone[-4:]
                else:
                    transaction['driver_phone_masked'] = 'hidden'
                transaction['driver_vehicle'] = deliverer.get('vehicle_type', 'unknown')

        # Format timestamp
        if transaction.get('immutable_timestamp'):
            transaction['display_timestamp'] = transaction['immutable_timestamp']
        elif transaction.get('timestamp'):
            transaction['display_timestamp'] = transaction['timestamp']

    # Get available options for filters
    statuses = ['PENDING', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED']
    delivery_methods = ['public_transport', 'buyer_collection']

    return render_template('explorer/buyer_explorer.html',
                         transactions=transactions,
                         filters=filters,
                         statuses=statuses,
                         delivery_methods=delivery_methods)


# ==================== DRIVER TRANSACTION EXPLORER ====================

@explorer_bp.route('/driver')
@login_required
@driver_required
def driver_explorer():
    """
    Driver/Deliverer Transaction Explorer

    Drivers can:
    - View transactions assigned to them
    - Search by: transaction code, date range, seller name, buyer location (masked), delivery status
    - See: pickup location, drop-off address (partial), pickup/delivery codes, timestamp, earnings, status, transaction code
    """
    user = session.get('user')
    user_id = user['id']
    explorer_service = get_transaction_explorer_service()

    # Get deliverer record
    deliverer = deliverer_service.get_by_user_id(user_id)
    if not deliverer:
        flash('Deliverer profile not found', 'error')
        return redirect(url_for('marketplace.feed'))

    deliverer_id = deliverer['id']

    # Get filters from request
    filters = {
        'transaction_code': request.args.get('transaction_code', '').strip(),
        'date_start': request.args.get('date_start', '').strip(),
        'date_end': request.args.get('date_end', '').strip(),
        'seller_name': request.args.get('seller_name', '').strip(),
        'status': request.args.get('status', '').strip(),
        'limit': int(request.args.get('limit', 50))
    }

    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}

    # Search transactions
    transactions = explorer_service.search_driver_transactions(deliverer_id, filters)

    # Enhance transactions with additional data
    for transaction in transactions:
        # Get seller info
        if transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller:
                transaction['seller_name'] = seller.get('name', '')
                transaction['pickup_location'] = seller.get('address', 'N/A')

        # Mask buyer drop-off address (for privacy)
        if transaction.get('delivery_address'):
            address = transaction['delivery_address']
            if len(address) > 20:
                transaction['dropoff_address_masked'] = address[:10] + '...' + address[-8:]
            else:
                transaction['dropoff_address_masked'] = address[:10] + '...'

        # Calculate driver earnings (example: 10% of total)
        transaction['driver_earnings'] = transaction.get('delivery_fee', 0)

        # Format timestamp
        if transaction.get('immutable_timestamp'):
            transaction['display_timestamp'] = transaction['immutable_timestamp']
        elif transaction.get('timestamp'):
            transaction['display_timestamp'] = transaction['timestamp']

    # Get available statuses for filters
    statuses = ['ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED']

    return render_template('explorer/driver_explorer.html',
                         transactions=transactions,
                         filters=filters,
                         statuses=statuses,
                         deliverer=deliverer)


# ==================== ADMIN TRANSACTION EXPLORER ====================

@explorer_bp.route('/admin')
@login_required
@admin_required
def admin_explorer():
    """
    Admin Transaction Explorer (Full Access)

    Admin can:
    - Search by: EVERYTHING (transaction code, IDs, timestamps, methods, statuses, names, emails)
    - See: COMPLETE details, all logs, all codes, settlements, fraud indicators
    - Perform deep audit-level searches
    - Query by ANY detail
    """
    user = session.get('user')
    explorer_service = get_transaction_explorer_service()
    user_service = get_user_service()

    # Get filters from request
    filters = {
        'transaction_code': request.args.get('transaction_code', '').strip(),
        'transaction_id': request.args.get('transaction_id', '').strip(),
        'driver_id': request.args.get('driver_id', '').strip(),
        'seller_id': request.args.get('seller_id', '').strip(),
        'buyer_id': request.args.get('buyer_id', '').strip(),
        'date_start': request.args.get('date_start', '').strip(),
        'date_end': request.args.get('date_end', '').strip(),
        'delivery_method': request.args.get('delivery_method', '').strip(),
        'payment_method': request.args.get('payment_method', '').strip(),
        'status': request.args.get('status', '').strip(),
        'limit': int(request.args.get('limit', 100))
    }

    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}

    # Search transactions (admin has full access)
    transactions = explorer_service.search_admin_transactions(filters)

    # Enhance transactions with FULL data (admin sees everything)
    for transaction in transactions:
        # Get buyer info (FULL)
        if transaction.get('user_id'):
            buyer = user_service.get(transaction['user_id'])
            if buyer:
                transaction['buyer_email'] = buyer.get('email', '')
                transaction['buyer_phone'] = buyer.get('phone', '')
                transaction['buyer_name'] = buyer.get('name', '')

        # Get seller info (FULL)
        if transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller:
                transaction['seller_name'] = seller.get('name', '')
                transaction['seller_handle'] = seller.get('handle', '')
                transaction['seller_email'] = seller.get('email', '')
                transaction['seller_phone'] = seller.get('phone', '')

        # Get driver info (FULL)
        if transaction.get('deliverer_id'):
            deliverer = deliverer_service.get(transaction['deliverer_id'])
            if deliverer:
                transaction['driver_phone'] = deliverer.get('phone', '')
                transaction['driver_vehicle'] = deliverer.get('vehicle_type', '')
                # Get driver user info
                if deliverer.get('user_id'):
                    driver_user = user_service.get(deliverer['user_id'])
                    if driver_user:
                        transaction['driver_email'] = driver_user.get('email', '')
                        transaction['driver_name'] = driver_user.get('name', '')

        # Get verification logs
        transaction['verification_log_count'] = len(transaction.get('verification_logs', []))

        # Format timestamp
        if transaction.get('immutable_timestamp'):
            transaction['display_timestamp'] = transaction['immutable_timestamp']
            transaction['timestamp_locked_display'] = '🔒 Locked'
        elif transaction.get('timestamp'):
            transaction['display_timestamp'] = transaction['timestamp']
            transaction['timestamp_locked_display'] = '🔓 Unlocked'

    # Get available options for filters
    statuses = ['PENDING', 'CONFIRMED', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'CANCELLED']
    payment_methods = ['COD', 'EFT', 'SnapScan', 'SPZ', 'Card']
    delivery_methods = ['public_transport', 'buyer_collection']

    return render_template('explorer/admin_explorer.html',
                         transactions=transactions,
                         filters=filters,
                         statuses=statuses,
                         payment_methods=payment_methods,
                         delivery_methods=delivery_methods)


# ==================== PUBLIC TRANSACTION EXPLORER ====================

@explorer_bp.route('/public')
def public_explorer():
    """
    Public Transaction Explorer (Anonymized)

    Shows:
    - Hashed buyer ID (e.g., Buyer-003)
    - Transaction hash
    - Timestamp
    - Amount
    - Delivery method
    - Status

    NOT visible:
    - Addresses
    - User details
    - Pickup or delivery codes
    """
    explorer_service = get_transaction_explorer_service()

    # Get limit from request (default 50)
    limit = int(request.args.get('limit', 50))

    # Get public transactions (anonymized)
    transactions = explorer_service.get_public_transactions(limit)

    # Calculate statistics
    total_volume = sum(t.get('amount', 0) for t in transactions)
    avg_amount = total_volume / len(transactions) if transactions else 0

    stats = {
        'total_transactions': len(transactions),
        'total_volume': total_volume,
        'avg_amount': avg_amount
    }

    return render_template('explorer/public_explorer.html',
                         transactions=transactions,
                         stats=stats)


# ==================== TRANSACTION DETAILS API ====================

@explorer_bp.route('/transaction/<transaction_id>')
@login_required
def transaction_details(transaction_id):
    """
    Get detailed transaction information (role-based access)
    """
    user = session.get('user')
    user_id = user['id']
    is_admin = user.get('is_admin') == 1
    explorer_service = get_transaction_explorer_service()

    # Get transaction by ID
    from firebase_config import get_firestore_db
    db = get_firestore_db()
    transaction_doc = db.collection('transactions').document(transaction_id).get()

    if not transaction_doc.exists:
        flash('Transaction not found', 'error')
        return redirect(url_for('marketplace.feed'))

    transaction = transaction_doc.to_dict()
    transaction['id'] = transaction_doc.id

    # Check access permissions
    has_access = False

    if is_admin:
        has_access = True
    elif user.get('user_type') == 'buyer' and transaction.get('user_id') == user_id:
        has_access = True
    elif user.get('user_type') == 'seller':
        seller = seller_service.get_by_user_id(user_id)
        if seller and transaction.get('seller_id') == seller['id']:
            has_access = True
    elif user.get('user_type') == 'deliverer':
        deliverer = deliverer_service.get_by_user_id(user_id)
        if deliverer and transaction.get('deliverer_id') == deliverer['id']:
            has_access = True

    if not has_access:
        flash('You do not have permission to view this transaction', 'error')
        return redirect(url_for('marketplace.feed'))

    # Get verification logs
    verification_logs = explorer_service.get_transaction_verification_logs(transaction_id)

    return render_template('explorer/transaction_details.html',
                         transaction=transaction,
                         verification_logs=verification_logs,
                         is_admin=is_admin)


# ==================== VERIFICATION CODE API ====================

@explorer_bp.route('/verify/pickup', methods=['POST'])
@login_required
@driver_required
def verify_pickup_code():
    """
    Verify pickup code (driver only)
    """
    user = session.get('user')
    user_id = user['id']
    explorer_service = get_transaction_explorer_service()

    transaction_id = request.form.get('transaction_id')
    code = request.form.get('code', '').strip()
    ip_address = request.remote_addr

    if not transaction_id or not code:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Verify code
    success, message = explorer_service.verify_pickup_code(
        transaction_id=transaction_id,
        code=code,
        user_id=user_id,
        ip_address=ip_address
    )

    return jsonify({'success': success, 'message': message})


@explorer_bp.route('/verify/delivery', methods=['POST'])
@login_required
def verify_delivery_code():
    """
    Verify delivery code (buyer only)
    """
    user = session.get('user')
    user_id = user['id']
    explorer_service = get_transaction_explorer_service()

    transaction_id = request.form.get('transaction_id')
    code = request.form.get('code', '').strip()
    ip_address = request.remote_addr

    if not transaction_id or not code:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Verify code
    success, message = explorer_service.verify_delivery_code(
        transaction_id=transaction_id,
        code=code,
        user_id=user_id,
        ip_address=ip_address
    )

    return jsonify({'success': success, 'message': message})
