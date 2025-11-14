"""
SparzaFi Marketplace Routes
Main feed, product browsing, cart, checkout, and order tracking
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, current_app
from . import marketplace_bp
from database_seed import get_db_connection
from shared.utils import (
    login_required,
    calculate_cart_summary,
    apply_promo_code,
    award_loyalty_points,
    update_user_token_balance
)
from datetime import datetime


@marketplace_bp.route('/')
def feed():
    """Main marketplace feed"""
    conn = get_db_connection()
    current_user = session.get('user')

    # Get all sellers with their products and videos
    sellers = conn.execute("""
        SELECT s.*
        FROM sellers s
        WHERE EXISTS (SELECT 1 FROM products WHERE seller_id = s.id AND is_active = 1)
        ORDER BY s.is_subscribed DESC, s.avg_rating DESC, s.created_at DESC
    """).fetchall()

    sellers_data = []
    for seller in sellers:
        seller_dict = dict(seller)

        # Get seller's videos ordered by type (intro, detailed, conclusion)
        videos = conn.execute("""
            SELECT * FROM videos
            WHERE seller_id = ? AND is_active = 1
            ORDER BY
                CASE video_type
                    WHEN 'intro' THEN 1
                    WHEN 'detailed' THEN 2
                    WHEN 'conclusion' THEN 3
                END
        """, (seller['id'],)).fetchall()
        seller_dict['videos'] = [dict(v) for v in videos]

        # Get seller's products
        products = conn.execute("""
            SELECT * FROM products
            WHERE seller_id = ? AND is_active = 1
            ORDER BY total_sales DESC, created_at DESC
            LIMIT 6
        """, (seller['id'],)).fetchall()
        seller_dict['products'] = [dict(p) for p in products]

        # Check if current user is following/liking this seller
        if current_user:
            is_following = conn.execute("""
                SELECT 1 FROM follows
                WHERE user_id = ? AND seller_id = ?
            """, (current_user['id'], seller['id'])).fetchone() is not None

            is_liked = conn.execute("""
                SELECT 1 FROM seller_likes
                WHERE user_id = ? AND seller_id = ?
            """, (current_user['id'], seller['id'])).fetchone() is not None

            seller_dict['is_following'] = is_following
            seller_dict['is_liked'] = is_liked

            # Check which videos user has liked
            for video in seller_dict['videos']:
                video_liked = conn.execute("""
                    SELECT 1 FROM video_likes
                    WHERE user_id = ? AND video_id = ?
                """, (current_user['id'], video['id'])).fetchone() is not None
                video['is_liked'] = video_liked
        else:
            seller_dict['is_following'] = False
            seller_dict['is_liked'] = False
            for video in seller_dict['videos']:
                video['is_liked'] = False

        sellers_data.append(seller_dict)

    return render_template('index.html', sellers=sellers_data)


@marketplace_bp.route('/search')
def search():
    """Smart product search with filters"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    verified_only = request.args.get('verified', type=bool, default=False)
    location = request.args.get('location', '').strip()
    
    conn = get_db_connection()
    
    # Build dynamic query
    sql = """
        SELECT p.*, s.name as seller_name, s.handle, s.location, s.verification_status
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.is_active = 1
    """
    params = []
    
    if query:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%'])
    
    if category:
        sql += " AND p.category = ?"
        params.append(category)
    
    if min_price is not None:
        sql += " AND p.price >= ?"
        params.append(min_price)
    
    if max_price is not None:
        sql += " AND p.price <= ?"
        params.append(max_price)
    
    if verified_only:
        sql += " AND s.verification_status = 'verified'"
    
    if location:
        sql += " AND s.location LIKE ?"
        params.append(f'%{location}%')
    
    sql += " ORDER BY p.rating DESC, p.sales_count DESC"
    
    products = conn.execute(sql, params).fetchall()
    products_list = [dict(p) for p in products]
    
    return render_template('search.html', 
                         products=products_list, 
                         query=query,
                         category=category,
                         min_price=min_price,
                         max_price=max_price,
                         location=location)


@marketplace_bp.route('/seller/<handle>')
def seller_detail(handle):
    """Seller detail page"""
    conn = get_db_connection()
    current_user = session.get('user')

    seller = conn.execute("""
        SELECT s.*, u.email,
               (SELECT AVG(rating) FROM reviews WHERE seller_id = s.id) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE seller_id = s.id) as review_count
        FROM sellers s
        JOIN users u ON s.user_id = u.id
        WHERE s.handle = ?
    """, (handle,)).fetchone()

    if not seller:
        flash('Seller not found', 'error')
        return redirect(url_for('marketplace.feed'))

    seller_dict = dict(seller)

    # Get videos ordered by type (intro, detailed, conclusion)
    videos = conn.execute("""
        SELECT * FROM videos
        WHERE seller_id = ? AND is_active = 1
        ORDER BY
            CASE video_type
                WHEN 'intro' THEN 1
                WHEN 'detailed' THEN 2
                WHEN 'conclusion' THEN 3
            END
    """, (seller['id'],)).fetchall()
    seller_dict['videos'] = [dict(v) for v in videos]

    # Get products
    products = conn.execute("""
        SELECT * FROM products
        WHERE seller_id = ? AND is_active = 1
        ORDER BY total_sales DESC, created_at DESC
    """, (seller['id'],)).fetchall()
    seller_dict['products'] = [dict(p) for p in products]

    # Get recent reviews
    reviews = conn.execute("""
        SELECT r.*, u.email
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.seller_id = ?
        ORDER BY r.created_at DESC
        LIMIT 10
    """, (seller['id'],)).fetchall()
    seller_dict['reviews'] = [dict(r) for r in reviews]

    # Check if current user is following/liking
    if current_user:
        is_following = conn.execute("""
            SELECT 1 FROM follows
            WHERE user_id = ? AND seller_id = ?
        """, (current_user['id'], seller['id'])).fetchone() is not None

        is_liked = conn.execute("""
            SELECT 1 FROM seller_likes
            WHERE user_id = ? AND seller_id = ?
        """, (current_user['id'], seller['id'])).fetchone() is not None

        seller_dict['is_following'] = is_following
        seller_dict['is_liked'] = is_liked

        # Check which videos user has liked
        for video in seller_dict['videos']:
            video_liked = conn.execute("""
                SELECT 1 FROM video_likes
                WHERE user_id = ? AND video_id = ?
            """, (current_user['id'], video['id'])).fetchone() is not None
            video['is_liked'] = video_liked
    else:
        seller_dict['is_following'] = False
        seller_dict['is_liked'] = False
        for video in seller_dict['videos']:
            video['is_liked'] = False

    return render_template('seller_detail.html', seller=seller_dict)


@marketplace_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page"""
    conn = get_db_connection()
    
    product = conn.execute("""
        SELECT p.*, s.name as seller_name, s.handle, s.verification_status
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.id = ? AND p.is_active = 1
    """, (product_id,)).fetchone()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('marketplace.feed'))
    
    # Increment view count
    conn.execute('UPDATE products SET views = views + 1 WHERE id = ?', (product_id,))
    conn.commit()
    
    product_dict = dict(product)
    
    # Get product reviews
    reviews = conn.execute("""
        SELECT r.*, u.email 
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.seller_id = ?
        ORDER BY r.created_at DESC
        LIMIT 5
    """, (product['seller_id'],)).fetchall()
    product_dict['reviews'] = [dict(r) for r in reviews]
    
    return render_template('product_detail.html', product=product_dict)


@marketplace_bp.route('/cart')
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', {})
    
    items_list = []
    for item_id, data in cart_items.items():
        item = {
            'id': item_id,
            'name': data['product']['name'],
            'seller': data['product']['seller_name'],
            'price': f"R{data['product']['price']:.2f}",
            'quantity': data['quantity'],
            'line_total': f"R{(data['product']['price'] * data['quantity']):.2f}",
            'product': data['product']
        }
        items_list.append(item)
    
    summary = calculate_cart_summary()
    
    return render_template('cart.html', cart_items=items_list, summary=summary)


@marketplace_bp.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    """Add product to cart"""
    conn = get_db_connection()
    
    product = conn.execute("""
        SELECT p.*, s.name as seller_name, s.id as seller_id
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.id = ? AND p.is_active = 1
    """, (product_id,)).fetchone()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('marketplace.feed'))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'product': dict(product),
            'quantity': 1
        }
    
    session.modified = True
    flash(f'{product["name"]} added to cart!', 'success')
    
    return redirect(request.referrer or url_for('marketplace.feed'))


@marketplace_bp.route('/remove-from-cart/<item_id>')
def remove_from_cart(item_id):
    """Remove item from cart"""
    if 'cart' in session and item_id in session['cart']:
        product_name = session['cart'][item_id]['product']['name']
        del session['cart'][item_id]
        session.modified = True
        flash(f'{product_name} removed from cart', 'info')
    
    return redirect(url_for('marketplace.cart'))


@marketplace_bp.route('/update-cart/<item_id>/<action>')
def update_cart(item_id, action):
    """Update cart item quantity"""
    if 'cart' in session and item_id in session['cart']:
        if action == 'increase':
            session['cart'][item_id]['quantity'] += 1
        elif action == 'decrease':
            if session['cart'][item_id]['quantity'] > 1:
                session['cart'][item_id]['quantity'] -= 1
            else:
                del session['cart'][item_id]
        
        session.modified = True
    
    return redirect(url_for('marketplace.cart'))


@marketplace_bp.route('/apply-promo', methods=['POST'])
def apply_promo():
    """Apply promo code to cart"""
    promo_code = request.form.get('promo_code', '').strip().upper()
    
    if not promo_code:
        flash('Please enter a promo code', 'error')
        return redirect(url_for('marketplace.cart'))
    
    summary = calculate_cart_summary()
    result = apply_promo_code(promo_code, summary['raw_subtotal'])
    
    if result['success']:
        flash(f'Promo code applied! You saved R{result["discount"]:.2f}', 'success')
    else:
        flash(result['error'], 'error')
    
    return redirect(url_for('marketplace.cart'))


@marketplace_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page"""
    user = session.get('user')
    cart_items = session.get('cart', {})
    
    if not cart_items:
        flash('Your cart is empty', 'info')
        return redirect(url_for('marketplace.cart'))
    
    if request.method == 'POST':
        payment_method = 'SPZ'  # Only SPZ tokens allowed
        delivery_method = request.form.get('delivery_method', 'public_transport')
        delivery_address = request.form.get('delivery_address', user.get('address', ''))

        summary = calculate_cart_summary()
        raw_total = summary['raw_total']

        conn = get_db_connection()

        try:
            # Check user's SPZ token balance
            user_balance = conn.execute("""
                SELECT token_balance FROM users WHERE id = ?
            """, (user['id'],)).fetchone()

            if not user_balance or user_balance['token_balance'] < raw_total:
                flash(f'Insufficient SPZ token balance. Required: {raw_total:.2f} SPZ, Available: {user_balance["token_balance"]:.2f} SPZ', 'error')
                return redirect(url_for('marketplace.cart'))

            # Get seller_id from first item
            first_item = list(cart_items.values())[0]
            seller_id = first_item['product']['seller_id']

            # Deduct SPZ tokens from buyer
            conn.execute("""
                UPDATE users
                SET token_balance = token_balance - ?
                WHERE id = ?
            """, (raw_total, user['id']))

            # Add SPZ tokens to seller (minus platform commission)
            seller_amount = summary['raw_subtotal'] - summary['raw_commission']
            conn.execute("""
                UPDATE users
                SET token_balance = token_balance + ?
                WHERE id = (SELECT user_id FROM sellers WHERE id = ?)
            """, (seller_amount, seller_id))

            # Create transaction
            cursor = conn.execute("""
                INSERT INTO transactions
                (user_id, seller_id, total_amount, status, payment_method, delivery_method,
                 delivery_address, seller_amount, deliverer_fee, platform_commission, tax_amount, discount_amount)
                VALUES (?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user['id'], seller_id, raw_total, payment_method, delivery_method,
                delivery_address,
                seller_amount,
                summary['raw_driver_fee'],
                summary['raw_commission'],
                summary['raw_tax'],
                summary['raw_discount']
            ))

            transaction_id = cursor.lastrowid

            # Update session with new token balance
            session['user']['token_balance'] = user_balance['token_balance'] - raw_total

            # Clear cart and promo code
            session.pop('cart', None)
            session.pop('promo_code', None)
            session['last_order_id'] = transaction_id

            conn.commit()

            flash(f'Order placed successfully! Paid {raw_total:.2f} SPZ tokens', 'success')
            return redirect(url_for('marketplace.order_tracking', order_id=transaction_id))

        except Exception as e:
            conn.rollback()
            flash(f'Checkout failed: {str(e)}', 'error')
            return redirect(url_for('marketplace.cart'))
    
    summary = calculate_cart_summary()
    return render_template('checkout.html', summary=summary, user=user)


@marketplace_bp.route('/order/<int:order_id>')
@login_required
def order_tracking(order_id):
    """Order tracking page"""
    user = session.get('user')
    conn = get_db_connection()
    
    transaction = conn.execute("""
        SELECT t.*, s.name as seller_name, s.handle
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        WHERE t.id = ?
    """, (order_id,)).fetchone()
    
    if not transaction:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))
    
    # Check authorization
    if transaction['user_id'] != user['id'] and user.get('is_admin') != 1:
        flash('Access denied', 'error')
        return redirect(url_for('marketplace.feed'))
    
    transaction_dict = dict(transaction)
    
    # Get tracking history
    tracking = conn.execute("""
        SELECT dt.*, u.email as created_by_email
        FROM delivery_tracking dt
        LEFT JOIN users u ON dt.created_by = u.id
        WHERE dt.transaction_id = ?
        ORDER BY dt.created_at ASC
    """, (order_id,)).fetchall()
    
    transaction_dict['tracking'] = [dict(t) for t in tracking]
    transaction_dict['status_description'] = current_app.config['DELIVERY_STATUSES'].get(
        transaction['status'], 'Unknown status'
    )
    
    return render_template('order_tracking.html', transaction=transaction_dict)


@marketplace_bp.route('/follow/<int:seller_id>', methods=['POST'])
@login_required
def follow_seller(seller_id):
    """Follow/unfollow a seller"""
    user = session.get('user')
    conn = get_db_connection()

    existing = conn.execute("""
        SELECT id FROM follows
        WHERE user_id = ? AND seller_id = ?
    """, (user['id'], seller_id)).fetchone()

    if existing:
        # Unfollow
        conn.execute('DELETE FROM follows WHERE user_id = ? AND seller_id = ?',
                    (user['id'], seller_id))
        conn.execute('UPDATE sellers SET follower_count = follower_count - 1 WHERE id = ?',
                    (seller_id,))
        following = False
    else:
        # Follow
        conn.execute('INSERT INTO follows (user_id, seller_id) VALUES (?, ?)',
                    (user['id'], seller_id))
        conn.execute('UPDATE sellers SET follower_count = follower_count + 1 WHERE id = ?',
                    (seller_id,))
        following = True

    conn.commit()

    return jsonify({'success': True, 'following': following})


@marketplace_bp.route('/like/seller/<int:seller_id>', methods=['POST'])
@login_required
def like_seller(seller_id):
    """Like/unlike a seller"""
    user = session.get('user')
    conn = get_db_connection()

    # Check if seller exists
    seller = conn.execute('SELECT id FROM sellers WHERE id = ?', (seller_id,)).fetchone()
    if not seller:
        return jsonify({'success': False, 'error': 'Seller not found'}), 404

    existing = conn.execute("""
        SELECT id FROM seller_likes
        WHERE user_id = ? AND seller_id = ?
    """, (user['id'], seller_id)).fetchone()

    if existing:
        # Unlike
        conn.execute('DELETE FROM seller_likes WHERE user_id = ? AND seller_id = ?',
                    (user['id'], seller_id))
        conn.execute('UPDATE sellers SET likes_count = likes_count - 1 WHERE id = ?',
                    (seller_id,))
        liked = False
    else:
        # Like
        conn.execute('INSERT INTO seller_likes (user_id, seller_id) VALUES (?, ?)',
                    (user['id'], seller_id))
        conn.execute('UPDATE sellers SET likes_count = likes_count + 1 WHERE id = ?',
                    (seller_id,))
        liked = True

    conn.commit()

    # Get updated likes count
    seller_updated = conn.execute('SELECT likes_count FROM sellers WHERE id = ?', (seller_id,)).fetchone()

    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': seller_updated['likes_count']
    })


@marketplace_bp.route('/like/video/<int:video_id>', methods=['POST'])
@login_required
def like_video(video_id):
    """Like/unlike a video"""
    user = session.get('user')
    conn = get_db_connection()

    # Check if video exists
    video = conn.execute('SELECT id FROM videos WHERE id = ?', (video_id,)).fetchone()
    if not video:
        return jsonify({'success': False, 'error': 'Video not found'}), 404

    existing = conn.execute("""
        SELECT id FROM video_likes
        WHERE user_id = ? AND video_id = ?
    """, (user['id'], video_id)).fetchone()

    if existing:
        # Unlike
        conn.execute('DELETE FROM video_likes WHERE user_id = ? AND video_id = ?',
                    (user['id'], video_id))
        conn.execute('UPDATE videos SET likes_count = likes_count - 1 WHERE id = ?',
                    (video_id,))
        liked = False
    else:
        # Like
        conn.execute('INSERT INTO video_likes (user_id, video_id) VALUES (?, ?)',
                    (user['id'], video_id))
        conn.execute('UPDATE videos SET likes_count = likes_count + 1 WHERE id = ?',
                    (video_id,))
        liked = True

    conn.commit()

    # Get updated likes count
    video_updated = conn.execute('SELECT likes_count FROM videos WHERE id = ?', (video_id,)).fetchone()

    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': video_updated['likes_count']
    })


@marketplace_bp.route('/transactions')
def transactions_explorer():
    """Transaction explorer with role-based access"""
    from flask import request, session
    conn = get_db_connection()

    # Get current user info
    current_user = session.get('user')
    is_admin = current_user and current_user.get('is_admin') == 1
    user_id = current_user.get('id') if current_user else None
    user_type = current_user.get('user_type', 'buyer') if current_user else 'buyer'

    # Get search query
    search_query = request.args.get('search', '').strip()

    # Validate search query for non-admin users
    if search_query and not is_admin and current_user:
        # Generate user's own identifier to validate against
        if user_type == 'buyer':
            allowed_id = f"buyer{user_id:06d}"
        elif user_type == 'seller':
            seller_record = conn.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,)).fetchone()
            allowed_id = f"seller{seller_record['id']:06d}" if seller_record else ""
        elif user_type == 'deliverer':
            deliverer_record = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user_id,)).fetchone()
            allowed_id = f"deliverer{deliverer_record['id']:06d}" if deliverer_record else ""
        else:
            allowed_id = ""

        # If search query doesn't match their own ID, clear it
        if search_query.lower() not in allowed_id.lower():
            search_query = ""  # Clear invalid search

    # Build query based on user role
    if is_admin:
        # Admins see all transactions
        query = """
            SELECT t.id, t.user_id, t.seller_id, t.deliverer_id, t.total_amount,
                   t.status, t.timestamp, t.payment_method, t.delivery_method,
                   u.email as buyer_email, u.user_type as buyer_type,
                   s.name as seller_name, s.handle as seller_handle,
                   d.id as deliverer_user_id
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.id
            LEFT JOIN sellers s ON t.seller_id = s.id
            LEFT JOIN deliverers d ON t.deliverer_id = d.id
            ORDER BY t.timestamp DESC
            LIMIT 100
        """
        transactions = conn.execute(query).fetchall()
    elif current_user:
        # Buyers see their own transactions
        if user_type == 'buyer':
            query = """
                SELECT t.id, t.user_id, t.seller_id, t.deliverer_id, t.total_amount,
                       t.status, t.timestamp, t.payment_method, t.delivery_method,
                       u.email as buyer_email, u.user_type as buyer_type,
                       s.name as seller_name, s.handle as seller_handle
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN sellers s ON t.seller_id = s.id
                WHERE t.user_id = ?
                ORDER BY t.timestamp DESC
                LIMIT 50
            """
            transactions = conn.execute(query, (user_id,)).fetchall()
        # Sellers see transactions where they are the seller
        elif user_type == 'seller':
            seller_record = conn.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,)).fetchone()
            seller_id = seller_record['id'] if seller_record else None
            query = """
                SELECT t.id, t.user_id, t.seller_id, t.deliverer_id, t.total_amount,
                       t.status, t.timestamp, t.payment_method, t.delivery_method,
                       u.email as buyer_email, u.user_type as buyer_type,
                       s.name as seller_name, s.handle as seller_handle
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN sellers s ON t.seller_id = s.id
                WHERE t.seller_id = ?
                ORDER BY t.timestamp DESC
                LIMIT 50
            """
            transactions = conn.execute(query, (seller_id,)).fetchall() if seller_id else []
        # Deliverers see transactions where they are the deliverer
        elif user_type == 'deliverer':
            deliverer_record = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user_id,)).fetchone()
            deliverer_id = deliverer_record['id'] if deliverer_record else None
            query = """
                SELECT t.id, t.user_id, t.seller_id, t.deliverer_id, t.total_amount,
                       t.status, t.timestamp, t.payment_method, t.delivery_method,
                       u.email as buyer_email, u.user_type as buyer_type,
                       s.name as seller_name, s.handle as seller_handle
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                LEFT JOIN sellers s ON t.seller_id = s.id
                WHERE t.deliverer_id = ?
                ORDER BY t.timestamp DESC
                LIMIT 50
            """
            transactions = conn.execute(query, (deliverer_id,)).fetchall() if deliverer_id else []
        else:
            transactions = []
    else:
        # Not logged in - show nothing
        transactions = []

    # Process transactions
    transactions_list = []
    for t in transactions:
        transaction = dict(t)

        # Generate user identifiers
        transaction['buyer_identifier'] = f"buyer{transaction['user_id']:06d}" if transaction.get('user_id') else "unknown"
        transaction['seller_identifier'] = f"seller{transaction['seller_id']:06d}" if transaction.get('seller_id') else "none"
        transaction['deliverer_identifier'] = f"deliverer{transaction['deliverer_id']:06d}" if transaction.get('deliverer_id') else "none"

        # Generate transaction hash
        import hashlib
        timestamp_hash = hashlib.sha1(str(transaction['timestamp']).encode()).hexdigest()[:8]
        transaction['tx_hash'] = f"0x{transaction['id']:06}{timestamp_hash}"
        transaction['display_amount'] = f"R{transaction['total_amount']:.2f}"
        transaction['delivery_label'] = 'Public Transport' if transaction.get('delivery_method') == 'public_transport' else 'Buyer Collection'

        # Apply search filter if search query exists
        if search_query:
            search_lower = search_query.lower()
            if (search_lower in transaction['buyer_identifier'].lower() or
                search_lower in transaction['seller_identifier'].lower() or
                search_lower in transaction['deliverer_identifier'].lower() or
                search_lower in transaction['tx_hash'].lower()):
                transactions_list.append(transaction)
        else:
            transactions_list.append(transaction)

    # Generate current user's identifier for display
    user_identifier = None
    if current_user and not is_admin:
        if user_type == 'buyer':
            user_identifier = f"buyer{user_id:06d}"
        elif user_type == 'seller':
            seller_record = conn.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,)).fetchone()
            if seller_record:
                user_identifier = f"seller{seller_record['id']:06d}"
        elif user_type == 'deliverer':
            deliverer_record = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user_id,)).fetchone()
            if deliverer_record:
                user_identifier = f"deliverer{deliverer_record['id']:06d}"

    return render_template('transactions_explorer.html',
                         transactions=transactions_list,
                         is_admin=is_admin,
                         user_identifier=user_identifier,
                         search_query=search_query)


# ============================================================================
# ORDER CHAT ROUTES
# ============================================================================

@marketplace_bp.route('/order/<int:order_id>/chat')
@login_required
def order_chat(order_id):
    """Order chat page"""
    from shared.chat_utils import can_user_access_chat, get_chat_messages, get_unread_count, mark_messages_as_read
    
    user = session.get('user')
    
    # Check access
    has_access, role = can_user_access_chat(user['id'], order_id)
    if not has_access:
        flash('You do not have access to this chat', 'error')
        return redirect(url_for('marketplace.feed'))
    
    conn = get_db_connection()
    
    # Get order details
    transaction = conn.execute("""
        SELECT t.*,
               s.name as seller_name,
               u_buyer.email as buyer_email,
               d.user_id as driver_user_id,
               u_driver.email as driver_email
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        LEFT JOIN users u_buyer ON t.user_id = u_buyer.id
        LEFT JOIN drivers d ON t.driver_id = d.id
        LEFT JOIN users u_driver ON d.user_id = u_driver.id
        WHERE t.id = ?
    """, (order_id,)).fetchone()
    
    if not transaction:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))
    
    transaction_dict = dict(transaction)
    transaction_dict['user_role'] = role
    
    # Get chat messages
    messages = get_chat_messages(order_id)
    
    # Mark messages as read
    mark_messages_as_read(order_id, user['id'])
    
    # Determine other party
    if role == 'buyer':
        other_user_id = transaction['driver_user_id']
        other_user_name = transaction['driver_email'] or 'Deliverer'
    else:  # deliverer
        other_user_id = transaction['user_id']
        other_user_name = transaction['buyer_email'] or 'Buyer'
    
    transaction_dict['other_user_id'] = other_user_id
    transaction_dict['other_user_name'] = other_user_name
    transaction_dict['messages'] = messages
    
    return render_template('order_chat.html', 
                         transaction=transaction_dict,
                         current_user_id=user['id'])


@marketplace_bp.route('/order/<int:order_id>/chat/send', methods=['POST'])
@login_required
def send_chat_message(order_id):
    """Send a chat message"""
    from shared.chat_utils import send_chat_message as send_message, can_user_access_chat
    
    user = session.get('user')
    
    # Check access
    has_access, role = can_user_access_chat(user['id'], order_id)
    if not has_access:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    message = request.json.get('message', '').strip() if request.is_json else request.form.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
    
    # Get recipient
    conn = get_db_connection()
    transaction = conn.execute("""
        SELECT t.user_id as buyer_id, d.user_id as driver_user_id
        FROM transactions t
        LEFT JOIN drivers d ON t.driver_id = d.id
        WHERE t.id = ?
    """, (order_id,)).fetchone()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    # Determine recipient
    if role == 'buyer':
        to_user_id = transaction['driver_user_id']
    else:  # deliverer
        to_user_id = transaction['buyer_id']
    
    if not to_user_id:
        return jsonify({'success': False, 'error': 'Recipient not available'}), 400
    
    # Send message
    result = send_message(order_id, user['id'], to_user_id, message)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@marketplace_bp.route('/order/<int:order_id>/chat/messages')
@login_required
def get_chat_messages_api(order_id):
    """API endpoint to get chat messages (for live updates)"""
    from shared.chat_utils import can_user_access_chat, get_chat_messages
    
    user = session.get('user')
    
    # Check access
    has_access, _ = can_user_access_chat(user['id'], order_id)
    if not has_access:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    since_id = request.args.get('since_id', type=int, default=0)
    
    # Get messages
    messages = get_chat_messages(order_id)
    
    # Filter messages after since_id
    if since_id > 0:
        messages = [m for m in messages if m['id'] > since_id]
    
    return jsonify({
        'success': True,
        'messages': messages,
        'count': len(messages)
    })


@marketplace_bp.route('/order/<int:order_id>/chat/flag/<int:message_id>', methods=['POST'])
@login_required
def flag_chat_message(order_id, message_id):
    """Flag a message for admin review"""
    from shared.chat_utils import can_user_access_chat, flag_message
    
    user = session.get('user')
    
    # Check access
    has_access, _ = can_user_access_chat(user['id'], order_id)
    if not has_access:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    reason = request.json.get('reason', 'Inappropriate content') if request.is_json else request.form.get('reason', 'Inappropriate content')
    
    try:
        flag_message(message_id, reason, user['id'])
        return jsonify({'success': True, 'message': 'Message flagged for review'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@marketplace_bp.route('/chats')
@login_required
def all_chats():
    """View all active chats for user"""
    from shared.chat_utils import get_user_active_chats

    user = session.get('user')
    chats = get_user_active_chats(user['id'])

    return render_template('all_chats.html', chats=chats)


# ============================================================================
# API ROUTES FOR FLOATING SHOP MODAL
# ============================================================================

@marketplace_bp.route('/seller/<int:seller_id>/products')
def get_seller_products(seller_id):
    """API endpoint to fetch products for a specific seller"""
    import json
    conn = get_db_connection()

    try:
        # Get all active products for this seller
        products = conn.execute("""
            SELECT id, name, description, price, images, category, stock_count, is_active
            FROM products
            WHERE seller_id = ? AND is_active = 1
            ORDER BY total_sales DESC, created_at DESC
        """, (seller_id,)).fetchall()

        products_list = []
        for p in products:
            product_dict = dict(p)

            # Parse images JSON array and get first image
            try:
                images_array = json.loads(product_dict['images']) if product_dict['images'] else []
                product_dict['image_url'] = images_array[0] if images_array else None
            except (json.JSONDecodeError, IndexError, TypeError):
                product_dict['image_url'] = None

            # Rename stock_count to stock_quantity for frontend compatibility
            product_dict['stock_quantity'] = product_dict.pop('stock_count', 0)

            # Remove images field from response (we only need image_url)
            product_dict.pop('images', None)

            products_list.append(product_dict)

        return jsonify({
            'success': True,
            'products': products_list,
            'count': len(products_list)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'products': []
        }), 500


@marketplace_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart_api():
    """API endpoint to add product to cart"""
    user = session.get('user')

    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id:
            return jsonify({
                'success': False,
                'message': 'Product ID is required'
            }), 400

        conn = get_db_connection()

        # Get product details
        product = conn.execute("""
            SELECT p.*, s.name as seller_name, s.id as seller_id
            FROM products p
            JOIN sellers s ON p.seller_id = s.id
            WHERE p.id = ? AND p.is_active = 1
        """, (product_id,)).fetchone()

        if not product:
            return jsonify({
                'success': False,
                'message': 'Product not found'
            }), 404

        # Convert Row object to dict early
        product_dict = dict(product)

        # Check stock (using stock_count from database)
        stock = product_dict.get('stock_count') or product_dict.get('stock_quantity', 0)
        if stock is not None and stock < quantity:
            return jsonify({
                'success': False,
                'message': 'Insufficient stock'
            }), 400

        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = {}

        cart = session['cart']
        product_id_str = str(product_id)

        # Add or update cart
        if product_id_str in cart:
            cart[product_id_str]['quantity'] += quantity
        else:
            cart[product_id_str] = {
                'product': product_dict,
                'quantity': quantity
            }

        session.modified = True

        return jsonify({
            'success': True,
            'message': f'{product_dict["name"]} added to cart',
            'cart_count': len(cart)
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Cart add failed: {str(e)}")
        print(f"[ERROR] Traceback: {error_details}")
        return jsonify({
            'success': False,
            'message': f'Failed to add to cart: {str(e)}'
        }), 500

@marketplace_bp.route('/submit-review', methods=['POST'])
@login_required
def submit_review():
    """Submit a review for a seller"""
    try:
        user = session.get('user')
        conn = get_db_connection()
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        rating = int(data.get('rating', 5))
        review_text = data.get('review_text', '').strip()
        
        # Validation
        if not seller_id:
            return jsonify({'success': False, 'error': 'Seller ID is required'}), 400
            
        if not review_text or len(review_text) < 10:
            return jsonify({'success': False, 'error': 'Review must be at least 10 characters'}), 400
            
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
        
        # Check if seller exists
        seller = conn.execute('SELECT id FROM sellers WHERE id = ?', (seller_id,)).fetchone()
        if not seller:
            return jsonify({'success': False, 'error': 'Seller not found'}), 404
        
        # Check if user has already reviewed this seller
        existing_review = conn.execute("""
            SELECT id FROM reviews
            WHERE user_id = ? AND seller_id = ?
        """, (user['id'], seller_id)).fetchone()
        
        if existing_review:
            # Update existing review
            conn.execute("""
                UPDATE reviews
                SET rating = ?,
                    review_text = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, review_text, existing_review['id']))
            
            message = 'Review updated successfully!'
        else:
            # Create new review (seller-level review, not product-specific)
            conn.execute("""
                INSERT INTO reviews (seller_id, user_id, rating, review_text, product_id)
                VALUES (?, ?, ?, ?, NULL)
            """, (seller_id, user['id'], rating, review_text))
            
            message = 'Review submitted successfully!'
        
        # Update seller's average rating
        avg_rating = conn.execute("""
            SELECT AVG(rating) as avg_rating
            FROM reviews
            WHERE seller_id = ? AND is_visible = 1
        """, (seller_id,)).fetchone()['avg_rating']
        
        conn.execute("""
            UPDATE sellers
            SET avg_rating = ?
            WHERE id = ?
        """, (avg_rating, seller_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'new_avg_rating': round(avg_rating, 1) if avg_rating else 5.0
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to submit review: {str(e)}'
        }), 500
