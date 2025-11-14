from flask import render_template, redirect, url_for, session, request, abort, jsonify
from flask import current_app as app, g
from shared.utils import login_required, get_db, submit_withdrawal_request, transfer_tokens
from . import user_bp
# Import all required fintech functions from shared.utils
from .buyer_dashboard import (
    buyer_dashboard as buyer_dashboard_view,
    order_tracking as order_tracking_view,
    generate_delivery_code_endpoint,
    request_return,
    download_order_csv,
    purchase_history as purchase_history_view,
    manage_addresses as manage_addresses_view
)

@user_bp.route('/profile')
@login_required
def user_profile():
    user = session.get('user')
    db = get_db()

    # Get user data with profile picture from users table
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()

    # Get additional data if user is a seller
    seller_data = None
    if user.get('user_type') == 'seller':
        seller_data = db.execute('SELECT * FROM sellers WHERE user_id = ?', (user['id'],)).fetchone()

    # Get additional data if user is a deliverer
    deliverer_data = None
    if user.get('user_type') == 'deliverer':
        deliverer_data = db.execute('SELECT * FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()

    profile_data = {
        'user': dict(user_data) if user_data else user,
        'seller': dict(seller_data) if seller_data else None,
        'deliverer': dict(deliverer_data) if deliverer_data else None
    }

    return render_template('user_profile.html', profile=profile_data)

@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    user = session.get('user')
    db = get_db()
    
    if request.method == 'POST':
        # 3. Profile Customization - Handle image uploads
        # 25. Dark/Light Mode - Handle theme change
        theme_preference = request.form.get('theme_preference')
        if theme_preference in ['dark', 'light']:
             db.execute('UPDATE users SET theme_preference = ? WHERE id = ?', (theme_preference, user['id']))
             db.commit()
             session['user']['theme_preference'] = theme_preference

    return render_template('user_settings.html')


@user_bp.route('/wallet')
@login_required
def wallet():
    # 12. Peer-to-Peer Marketplace Wallet
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
    """2. Wallet-to-Cash Gateway"""
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
    """13. Referral Rewards"""
    user = session.get('user')
    db = get_db()

    # Get users who were referred by this user
    referred_users = db.execute("""
        SELECT email, created_at, token_balance
        FROM users
        WHERE referred_by = ?
        ORDER BY created_at DESC
    """, (user['id'],)).fetchall()

    # Get referral rewards from loyalty_rewards table
    referral_rewards = db.execute("""
        SELECT points_earned, created_at, description
        FROM loyalty_rewards
        WHERE user_id = ? AND reward_type = 'referral'
        ORDER BY created_at DESC
    """, (user['id'],)).fetchall()

    return render_template('referrals.html',
                         referral_code=user.get('referral_code', 'N/A'),
                         referred_users=[dict(r) for r in referred_users],
                         referral_rewards=[dict(r) for r in referral_rewards])


# ==================== VERIFICATION CODE ENDPOINTS ====================

@user_bp.route('/api/generate-delivery-code/<int:order_id>', methods=['POST'])
@login_required
def generate_delivery_code(order_id):
    """
    Buyer generates delivery code when ready to receive order
    """
    user = session.get('user')
    db = get_db()

    # Verify buyer owns this order
    transaction = db.execute("""
        SELECT id FROM transactions
        WHERE id = ? AND user_id = ?
    """, (order_id, user['id'])).fetchone()

    if not transaction:
        return jsonify({'success': False, 'error': 'Order not found or access denied'}), 404

    # Import the utility function
    from deliverer.utils import create_delivery_code

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

@user_bp.route('/order/<int:order_id>')
@login_required
def order_tracking(order_id):
    """Detailed order tracking with timeline"""
    return order_tracking_view(order_id)

@user_bp.route('/order/<int:order_id>/generate-code', methods=['POST'])
@login_required
def generate_code(order_id):
    """Generate delivery verification code"""
    return generate_delivery_code_endpoint(order_id)

@user_bp.route('/order/<int:order_id>/request-return', methods=['POST'])
@login_required
def submit_return(order_id):
    """Submit return request"""
    return request_return(order_id)

@user_bp.route('/order/<int:order_id>/download-csv')
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
    db = get_db()
    
    # Get all notifications
    notifications = db.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (user['id'],)).fetchall()
    
    return render_template('buyer/notifications.html', notifications=[dict(n) for n in notifications])

@user_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    user = session.get('user')
    db = get_db()
    
    db.execute("""
        UPDATE notifications
        SET is_read = 1, read_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    """, (notification_id, user['id']))
    db.commit()
    
    return jsonify({'success': True})

@user_bp.route('/order/<int:order_id>/rate-seller', methods=['POST'])
@login_required
def rate_seller(order_id):
    """Rate seller after delivery"""
    user = session.get('user')
    db = get_db()
    
    data = request.get_json()
    rating = data.get('rating')
    review_text = data.get('review_text', '')
    
    # Get order details
    order = db.execute("""
        SELECT seller_id FROM transactions
        WHERE id = ? AND user_id = ?
    """, (order_id, user['id'])).fetchone()
    
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    # Check if review exists
    existing = db.execute("""
        SELECT id FROM reviews
        WHERE user_id = ? AND transaction_id = ?
    """, (user['id'], order_id)).fetchone()
    
    if existing:
        # Update existing review
        db.execute("""
            UPDATE reviews
            SET rating = ?, review_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (rating, review_text, existing['id']))
    else:
        # Create new review
        db.execute("""
            INSERT INTO reviews
            (seller_id, user_id, transaction_id, rating, review_text, is_verified_purchase, product_id)
            VALUES (?, ?, ?, ?, ?, 1, 
                (SELECT product_id FROM transaction_items WHERE transaction_id = ? LIMIT 1))
        """, (order['seller_id'], user['id'], order_id, rating, review_text, order_id))
    
    db.commit()
    return jsonify({'success': True, 'message': 'Review submitted'})

@user_bp.route('/order/<int:order_id>/rate-driver', methods=['POST'])
@login_required
def rate_driver(order_id):
    """Rate driver after delivery"""
    user = session.get('user')
    db = get_db()
    
    data = request.get_json()
    rating = data.get('rating')
    review_text = data.get('review_text', '')
    
    # Get order details
    order = db.execute("""
        SELECT deliverer_id FROM transactions
        WHERE id = ? AND user_id = ?
    """, (order_id, user['id'])).fetchone()
    
    if not order or not order['deliverer_id']:
        return jsonify({'success': False, 'error': 'Order or deliverer not found'}), 404
    
    # Check if review exists
    existing = db.execute("""
        SELECT id FROM deliverer_reviews
        WHERE user_id = ? AND transaction_id = ?
    """, (user['id'], order_id)).fetchone()
    
    if existing:
        return jsonify({'success': False, 'error': 'Review already submitted'}), 400
    
    # Create review
    db.execute("""
        INSERT INTO deliverer_reviews
        (deliverer_id, user_id, transaction_id, rating, review_text)
        VALUES (?, ?, ?, ?, ?)
    """, (order['deliverer_id'], user['id'], order_id, rating, review_text))
    
    db.commit()
    return jsonify({'success': True, 'message': 'Driver review submitted'})

@user_bp.route('/order/<int:order_id>/reorder', methods=['POST'])
@login_required
def reorder(order_id):
    """Quick re-order from purchase history"""
    user = session.get('user')
    db = get_db()
    
    # Get order items
    items = db.execute("""
        SELECT product_id, quantity
        FROM transaction_items
        WHERE transaction_id = ?
    """, (order_id,)).fetchall()
    
    if not items:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    # Add all items to cart
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    for item in items:
        product_id_str = str(item['product_id'])
        
        # Get product details
        product = db.execute("""
            SELECT p.*, s.name as seller_name, s.id as seller_id
            FROM products p
            JOIN sellers s ON p.seller_id = s.id
            WHERE p.id = ? AND p.is_active = 1
        """, (item['product_id'],)).fetchone()
        
        if product:
            if product_id_str in cart:
                cart[product_id_str]['quantity'] += item['quantity']
            else:
                cart[product_id_str] = {
                    'product': dict(product),
                    'quantity': item['quantity']
                }
    
    session.modified = True
    return jsonify({'success': True, 'message': 'Items added to cart', 'cart_count': len(cart)})
