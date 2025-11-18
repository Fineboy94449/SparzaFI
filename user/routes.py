"""
User Routes - Migrated to Firebase
Profile, wallet, orders, notifications, and reviews
"""

from flask import render_template, redirect, url_for, session, request, abort, jsonify
from flask import current_app as app
from shared.utils import login_required, submit_withdrawal_request, transfer_tokens
from . import user_bp

# Import buyer dashboard functions (these may need separate migration)
from .buyer_dashboard import (
    buyer_dashboard as buyer_dashboard_view,
    order_tracking as order_tracking_view,
    generate_delivery_code_endpoint,
    request_return,
    download_order_csv,
    purchase_history as purchase_history_view,
    manage_addresses as manage_addresses_view
)

# Firebase imports
from firebase_db import (
    get_user_service,
    seller_service,
    deliverer_service,
    get_product_service,
    get_notification_service,
    review_service,
    transaction_service
)
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


@user_bp.route('/profile')
@login_required
def user_profile():
    user = session.get('user')
    user_service = get_user_service()

    # Get user data
    user_data = user_service.get(user['id'])

    # Get additional data if user is a seller
    seller_data = None
    if user.get('user_type') == 'seller':
        seller_data = seller_service.get_by_user_id(user['id'])

    # Get additional data if user is a deliverer
    deliverer_data = None
    if user.get('user_type') == 'deliverer':
        deliverer_data = deliverer_service.get_by_user_id(user['id'])

    profile_data = {
        'user': user_data if user_data else user,
        'seller': seller_data,
        'deliverer': deliverer_data
    }

    return render_template('user_profile.html', profile=profile_data)


@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    user = session.get('user')
    user_service = get_user_service()

    if request.method == 'POST':
        # Handle theme change
        theme_preference = request.form.get('theme_preference')
        if theme_preference in ['dark', 'light']:
            user_service.update(user['id'], {'theme_preference': theme_preference})
            session['user']['theme_preference'] = theme_preference

    return render_template('user_settings.html')


@user_bp.route('/wallet')
@login_required
def wallet():
    """Peer-to-Peer Marketplace Wallet"""
    user = session.get('user')
    # Fetch balance and transaction history (omitted implementation)

    return render_template('wallet.html', token_symbol=app.config['TOKEN_SYMBOL'])


@user_bp.route('/wallet/transfer', methods=['POST'])
@login_required
def wallet_transfer():
    user = session.get('user')
    data = request.get_json()

    to_user_email = data.get('to_user_email')
    amount = data.get('amount')
    notes = data.get('notes', '')

    if not to_user_email or not amount:
        return jsonify({'success': False, 'message': 'Email and amount are required'}), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid amount'}), 400

    result = transfer_tokens(user['id'], to_user_email, amount, notes)

    if result['success']:
        return jsonify(result), 200
    return jsonify({'success': False, 'message': result.get('error', 'Transfer failed')}), 400


@user_bp.route('/wallet/withdraw', methods=['POST'])
@login_required
def wallet_withdraw():
    """Wallet-to-Cash Gateway"""
    user = session.get('user')
    data = request.get_json()

    try:
        rand_amount = float(data.get('rand_amount'))
        bank_details = data.get('bank_details')
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid amount'}), 400

    result = submit_withdrawal_request(user['id'], rand_amount, bank_details)

    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 400


@user_bp.route('/referrals')
@login_required
def referrals_page():
    """Referral Rewards"""
    user = session.get('user')
    db = get_firestore_db()

    # Get users who were referred by this user
    referred_query = db.collection('users').where(
        filter=FieldFilter('referred_by', '==', user['id'])
    ).stream()

    referred_users = []
    for doc in referred_query:
        user_data = {**doc.to_dict(), 'id': doc.id}
        referred_users.append({
            'email': user_data.get('email', ''),
            'created_at': user_data.get('created_at', ''),
            'token_balance': user_data.get('token_balance', 0)
        })

    # Sort by created_at
    referred_users.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Get referral rewards from loyalty_rewards collection
    rewards_query = db.collection('loyalty_rewards').where(
        filter=FieldFilter('user_id', '==', user['id'])
    ).where(
        filter=FieldFilter('reward_type', '==', 'referral')
    ).stream()

    referral_rewards = []
    for doc in rewards_query:
        reward = {**doc.to_dict(), 'id': doc.id}
        referral_rewards.append({
            'points_earned': reward.get('points_earned', 0),
            'created_at': reward.get('created_at', ''),
            'description': reward.get('description', '')
        })

    # Sort by created_at
    referral_rewards.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return render_template('referrals.html',
                         referral_code=user.get('referral_code', 'N/A'),
                         referred_users=referred_users,
                         referral_rewards=referral_rewards)


# ==================== VERIFICATION CODE ENDPOINTS ====================

@user_bp.route('/api/generate-delivery-code/<order_id>', methods=['POST'])
@login_required
def generate_delivery_code(order_id):
    """
    Buyer generates delivery code when ready to receive order
    """
    user = session.get('user')
    db = get_firestore_db()

    # Verify buyer owns this order
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    transaction = transaction_doc.to_dict()

    if transaction.get('user_id') != user['id']:
        return jsonify({'success': False, 'error': 'Access denied'}), 404

    # Import the utility function
    from deliverer.firebase_verification_codes import create_delivery_code

    result = create_delivery_code(order_id, user['id'])

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# ==================== BUYER DASHBOARD ROUTES ====================

@user_bp.route('/dashboard')
@login_required
def buyer_dashboard():
    """Main buyer dashboard with order overview"""
    return buyer_dashboard_view()


@user_bp.route('/order/<order_id>')
@login_required
def order_tracking(order_id):
    """Detailed order tracking with timeline"""
    return order_tracking_view(order_id)


@user_bp.route('/order/<order_id>/generate-code', methods=['POST'])
@login_required
def generate_code(order_id):
    """Generate delivery verification code"""
    return generate_delivery_code_endpoint(order_id)


@user_bp.route('/order/<order_id>/request-return', methods=['POST'])
@login_required
def submit_return(order_id):
    """Submit return request"""
    return request_return(order_id)


@user_bp.route('/order/<order_id>/download-csv')
@login_required
def order_csv(order_id):
    """Download order receipt as CSV"""
    return download_order_csv(order_id)


@user_bp.route('/orders/history')
@login_required
def purchase_history():
    """Full purchase history with pagination"""
    return purchase_history_view()


@user_bp.route('/addresses', methods=['GET', 'POST'])
@login_required
def manage_addresses():
    """Manage delivery addresses"""
    return manage_addresses_view()


@user_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications"""
    user = session.get('user')
    notification_service = get_notification_service()

    # Get all notifications
    notifications = notification_service.get_user_notifications(user['id'], unread_only=False)

    return render_template('buyer/notifications.html', notifications=notifications)


@user_bp.route('/notifications/mark-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    user = session.get('user')
    notification_service = get_notification_service()

    # Verify notification belongs to user
    notification = notification_service.get(notification_id)
    if notification and notification.get('user_id') == user['id']:
        notification_service.mark_as_read(notification_id)

    return jsonify({'success': True})


@user_bp.route('/order/<order_id>/rate-seller', methods=['POST'])
@login_required
def rate_seller(order_id):
    """Rate seller after delivery"""
    user = session.get('user')
    db = get_firestore_db()

    data = request.get_json()
    rating = data.get('rating')
    review_text = data.get('review_text', '')

    # Get order details
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    order = {**transaction_doc.to_dict(), 'id': transaction_doc.id}

    if order.get('user_id') != user['id']:
        return jsonify({'success': False, 'error': 'Access denied'}), 404

    seller_id = order.get('seller_id')
    if not seller_id:
        return jsonify({'success': False, 'error': 'Seller not found'}), 404

    # Check if review exists
    existing_reviews = db.collection('reviews').where(
        filter=FieldFilter('user_id', '==', user['id'])
    ).where(
        filter=FieldFilter('transaction_id', '==', order_id)
    ).limit(1).stream()

    existing_review = None
    for doc in existing_reviews:
        existing_review = {**doc.to_dict(), 'id': doc.id}
        break

    # Get product_id from order items
    product_id = None
    if order.get('items') and len(order['items']) > 0:
        product_id = order['items'][0].get('product_id')

    if existing_review:
        # Update existing review
        db.collection('reviews').document(existing_review['id']).update({
            'rating': rating,
            'review_text': review_text,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    else:
        # Create new review
        review_service.create({
            'seller_id': seller_id,
            'user_id': user['id'],
            'transaction_id': order_id,
            'rating': rating,
            'review_text': review_text,
            'is_verified_purchase': True,
            'product_id': product_id
        })

    return jsonify({'success': True, 'message': 'Review submitted'})


@user_bp.route('/order/<order_id>/rate-driver', methods=['POST'])
@login_required
def rate_driver(order_id):
    """Rate driver after delivery"""
    user = session.get('user')
    db = get_firestore_db()

    data = request.get_json()
    rating = data.get('rating')
    review_text = data.get('review_text', '')

    # Get order details
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    order = {**transaction_doc.to_dict(), 'id': transaction_doc.id}

    if order.get('user_id') != user['id']:
        return jsonify({'success': False, 'error': 'Access denied'}), 404

    deliverer_id = order.get('deliverer_id')
    if not deliverer_id:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Check if review exists
    existing_reviews = db.collection('deliverer_reviews').where(
        filter=FieldFilter('user_id', '==', user['id'])
    ).where(
        filter=FieldFilter('transaction_id', '==', order_id)
    ).limit(1).stream()

    for doc in existing_reviews:
        return jsonify({'success': False, 'error': 'Review already submitted'}), 400

    # Create review
    db.collection('deliverer_reviews').add({
        'deliverer_id': deliverer_id,
        'user_id': user['id'],
        'transaction_id': order_id,
        'rating': rating,
        'review_text': review_text,
        'created_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'success': True, 'message': 'Driver review submitted'})


@user_bp.route('/order/<order_id>/reorder', methods=['POST'])
@login_required
def reorder(order_id):
    """Quick re-order from purchase history"""
    user = session.get('user')
    db = get_firestore_db()
    product_service = get_product_service()

    # Get order
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    order = {**transaction_doc.to_dict(), 'id': transaction_doc.id}
    items = order.get('items', [])

    if not items:
        return jsonify({'success': False, 'error': 'Order has no items'}), 404

    # Add all items to cart
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    for item in items:
        product_id = item.get('product_id')
        quantity = item.get('quantity', 1)

        # Get product details
        product = product_service.get(product_id)

        if product and product.get('is_active', True):
            # Get seller info
            seller_id = product.get('seller_id')
            seller = seller_service.get(seller_id) if seller_id else None

            product['seller_name'] = seller.get('name', '') if seller else ''
            product['seller_id'] = seller_id

            product_id_str = str(product_id)

            if product_id_str in cart:
                cart[product_id_str]['quantity'] += quantity
            else:
                cart[product_id_str] = {
                    'product': product,
                    'quantity': quantity
                }

    session.modified = True
    return jsonify({'success': True, 'message': 'Items added to cart', 'cart_count': len(cart)})
