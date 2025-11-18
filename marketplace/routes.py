"""
SparzaFi Marketplace Routes
Main feed, product browsing, cart, checkout, and order tracking
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, current_app
from . import marketplace_bp
from firebase_db import (
    get_db,
    get_user_service,
    get_product_service,
    get_order_service,
    seller_service,
    review_service,
    transaction_service,
    video_service,
    follow_service,
    like_service,
    delivery_tracking_service
)
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from shared.utils import (
    login_required,
    calculate_cart_summary,
    apply_promo_code,
    award_loyalty_points,
    update_user_token_balance
)
from datetime import datetime
import uuid


@marketplace_bp.route('/')
def feed():
    """Main marketplace feed"""
    db = get_db()
    product_service = get_product_service()
    current_user = session.get('user')

    # Get all sellers with active products
    sellers = seller_service.get_all_sellers(order_by='created_at')

    sellers_data = []
    for seller in sellers:
        # Check if seller has active products
        seller_products = product_service.get_seller_products(seller['id'])
        active_products = [p for p in seller_products if p.get('is_active', True)]

        if not active_products:
            continue

        seller_dict = seller.copy()

        # Get seller's videos ordered by type
        videos = video_service.get_seller_videos(seller['id'])
        seller_dict['videos'] = videos

        # Get seller's products (limit 6, sorted by total_sales)
        products = sorted(active_products, key=lambda x: (x.get('total_sales', 0), x.get('created_at', '')), reverse=True)[:6]
        seller_dict['products'] = products

        # Check if current user is following/liking this seller
        if current_user:
            seller_dict['is_following'] = follow_service.is_following(current_user['id'], seller['id'])
            seller_dict['is_liked'] = like_service.is_seller_liked(current_user['id'], seller['id'])

            # Check which videos user has liked
            for video in seller_dict['videos']:
                video['is_liked'] = like_service.is_video_liked(current_user['id'], video['id'])
        else:
            seller_dict['is_following'] = False
            seller_dict['is_liked'] = False
            for video in seller_dict['videos']:
                video['is_liked'] = False

        sellers_data.append(seller_dict)

    # Sort sellers by subscription status, rating, and creation date
    sellers_data.sort(
        key=lambda s: (
            s.get('is_subscribed', False),
            s.get('avg_rating', 0),
            s.get('created_at', '')
        ),
        reverse=True
    )

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

    product_service = get_product_service()

    # Get active products
    filters = [('is_active', '==', True)]
    if category:
        filters.append(('category', '==', category))

    products = product_service.query(filters)

    # Apply text search filter (name or description contains query)
    if query:
        query_lower = query.lower()
        products = [
            p for p in products
            if query_lower in p.get('name', '').lower() or query_lower in p.get('description', '').lower()
        ]

    # Apply price filters
    if min_price is not None:
        products = [p for p in products if p.get('price', 0) >= min_price]

    if max_price is not None:
        products = [p for p in products if p.get('price', 0) <= max_price]

    # Get seller information for each product
    products_list = []
    for p in products:
        product_dict = p.copy()

        # Get seller details
        seller = seller_service.get(p.get('seller_id'))
        if seller:
            product_dict['seller_name'] = seller.get('name', '')
            product_dict['handle'] = seller.get('handle', '')
            product_dict['location'] = seller.get('location', '')
            product_dict['verification_status'] = seller.get('verification_status', '')

            # Apply verified filter
            if verified_only and seller.get('verification_status') != 'verified':
                continue

            # Apply location filter
            if location and location.lower() not in seller.get('location', '').lower():
                continue

        products_list.append(product_dict)

    # Sort by rating and sales count
    products_list.sort(key=lambda p: (p.get('rating', 0), p.get('sales_count', 0)), reverse=True)

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
    user_service = get_user_service()
    product_service = get_product_service()
    current_user = session.get('user')

    # Get seller by handle
    seller = seller_service.get_by_handle(handle)

    if not seller:
        flash('Seller not found', 'error')
        return redirect(url_for('marketplace.feed'))

    seller_dict = seller.copy()

    # Get user email
    user = user_service.get(seller.get('user_id'))
    if user:
        seller_dict['email'] = user.get('email', '')

    # Get reviews for seller
    reviews = review_service.get_seller_reviews(seller['id'], limit=10)

    # Calculate avg rating and review count
    if reviews:
        avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews)
        seller_dict['avg_rating'] = avg_rating
    else:
        seller_dict['avg_rating'] = seller.get('avg_rating', 0)

    seller_dict['review_count'] = len(reviews)

    # Add user emails to reviews
    for review in reviews:
        user = user_service.get(review.get('user_id'))
        if user:
            review['email'] = user.get('email', '')

    seller_dict['reviews'] = reviews

    # Get videos ordered by type
    videos = video_service.get_seller_videos(seller['id'])
    seller_dict['videos'] = videos

    # Get products
    all_products = product_service.get_seller_products(seller['id'])
    active_products = [p for p in all_products if p.get('is_active', True)]

    # Sort by total_sales and created_at
    active_products.sort(key=lambda p: (p.get('total_sales', 0), p.get('created_at', '')), reverse=True)
    seller_dict['products'] = active_products

    # Check if current user is following/liking
    if current_user:
        seller_dict['is_following'] = follow_service.is_following(current_user['id'], seller['id'])
        seller_dict['is_liked'] = like_service.is_seller_liked(current_user['id'], seller['id'])

        # Check which videos user has liked
        for video in seller_dict['videos']:
            video['is_liked'] = like_service.is_video_liked(current_user['id'], video['id'])
    else:
        seller_dict['is_following'] = False
        seller_dict['is_liked'] = False
        for video in seller_dict['videos']:
            video['is_liked'] = False

    return render_template('seller_detail.html', seller=seller_dict)


@marketplace_bp.route('/product/<product_id>')
def product_detail(product_id):
    """Product detail page"""
    product_service = get_product_service()
    user_service = get_user_service()

    # Get product
    product = product_service.get(product_id)

    if not product or not product.get('is_active', True):
        flash('Product not found', 'error')
        return redirect(url_for('marketplace.feed'))

    product_dict = product.copy()

    # Get seller information
    seller = seller_service.get(product.get('seller_id'))
    if seller:
        product_dict['seller_name'] = seller.get('name', '')
        product_dict['handle'] = seller.get('handle', '')
        product_dict['verification_status'] = seller.get('verification_status', '')

    # Increment view count
    product_service.increment_views(product_id)

    # Get reviews for seller
    reviews = review_service.get_seller_reviews(product['seller_id'], limit=5)

    # Add user emails to reviews
    for review in reviews:
        user = user_service.get(review.get('user_id'))
        if user:
            review['email'] = user.get('email', '')

    product_dict['reviews'] = reviews

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


@marketplace_bp.route('/add-to-cart/<product_id>')
def add_to_cart(product_id):
    """Add product to cart"""
    product_service = get_product_service()

    # Get product
    product = product_service.get(product_id)

    if not product or not product.get('is_active', True):
        flash('Product not found', 'error')
        return redirect(url_for('marketplace.feed'))

    product_dict = product.copy()

    # Get seller information
    seller = seller_service.get(product.get('seller_id'))
    if seller:
        product_dict['seller_name'] = seller.get('name', '')
        product_dict['seller_id'] = seller.get('id')

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'product': product_dict,
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
    db = get_db()
    user_service = get_user_service()
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

        try:
            # Check user's SPZ token balance
            user_doc = user_service.get(user['id'])

            if not user_doc or user_doc.get('token_balance', 0) < raw_total:
                flash(f'Insufficient SPZ token balance. Required: {raw_total:.2f} SPZ, Available: {user_doc.get("token_balance", 0):.2f} SPZ', 'error')
                return redirect(url_for('marketplace.cart'))

            # Get seller_id from first item
            first_item = list(cart_items.values())[0]
            seller_id = first_item['product']['seller_id']

            # Get seller's user_id
            seller_doc = seller_service.get(seller_id)
            if not seller_doc:
                flash('Seller not found', 'error')
                return redirect(url_for('marketplace.cart'))

            seller_user_id = seller_doc.get('user_id')

            # Calculate amounts
            seller_amount = summary['raw_subtotal'] - summary['raw_commission']

            # Use Firestore transaction for atomic operations
            @firestore.transactional
            def checkout_transaction(transaction):
                # Read phase
                buyer_ref = db.collection('users').document(user['id'])
                seller_ref = db.collection('users').document(seller_user_id)

                buyer_doc = buyer_ref.get(transaction=transaction)
                seller_doc = seller_ref.get(transaction=transaction)

                if not buyer_doc.exists or not seller_doc.exists:
                    raise ValueError("User or seller not found")

                buyer_data = buyer_doc.to_dict()
                current_balance = buyer_data.get('token_balance', 0)

                if current_balance < raw_total:
                    raise ValueError("Insufficient balance")

                # Write phase
                # Deduct from buyer
                transaction.update(buyer_ref, {
                    'token_balance': current_balance - raw_total,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })

                # Add to seller
                transaction.update(seller_ref, {
                    'token_balance': firestore.Increment(seller_amount),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })

                # Create transaction record
                transaction_id = str(uuid.uuid4())
                transaction_ref = db.collection('transactions').document(transaction_id)
                transaction.set(transaction_ref, {
                    'user_id': user['id'],
                    'seller_id': seller_id,
                    'total_amount': raw_total,
                    'status': 'CONFIRMED',
                    'payment_method': payment_method,
                    'delivery_method': delivery_method,
                    'delivery_address': delivery_address,
                    'seller_amount': seller_amount,
                    'deliverer_fee': summary['raw_driver_fee'],
                    'platform_commission': summary['raw_commission'],
                    'tax_amount': summary['raw_tax'],
                    'discount_amount': summary['raw_discount'],
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'created_at': firestore.SERVER_TIMESTAMP
                })

                return transaction_id, current_balance - raw_total

            # Execute transaction
            trans = db.transaction()
            transaction_id, new_balance = checkout_transaction(trans)

            # Update session with new token balance
            session['user']['token_balance'] = new_balance

            # Clear cart and promo code
            session.pop('cart', None)
            session.pop('promo_code', None)
            session['last_order_id'] = transaction_id

            flash(f'Order placed successfully! Paid {raw_total:.2f} SPZ tokens', 'success')
            return redirect(url_for('marketplace.order_tracking', order_id=transaction_id))

        except Exception as e:
            flash(f'Checkout failed: {str(e)}', 'error')
            return redirect(url_for('marketplace.cart'))

    summary = calculate_cart_summary()
    return render_template('checkout.html', summary=summary, user=user)


@marketplace_bp.route('/order/<order_id>')
@login_required
def order_tracking(order_id):
    """Order tracking page"""
    db = get_db()
    user_service = get_user_service()
    user = session.get('user')

    # Get transaction
    transaction_ref = db.collection('transactions').document(order_id)
    transaction_doc = transaction_ref.get()

    if not transaction_doc.exists:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))

    transaction = transaction_doc.to_dict()
    transaction['id'] = transaction_doc.id

    # Check authorization
    if transaction.get('user_id') != user['id'] and user.get('is_admin') != 1:
        flash('Access denied', 'error')
        return redirect(url_for('marketplace.feed'))

    transaction_dict = transaction.copy()

    # Get seller information
    seller = seller_service.get(transaction.get('seller_id'))
    if seller:
        transaction_dict['seller_name'] = seller.get('name', '')
        transaction_dict['handle'] = seller.get('handle', '')

    # Get tracking history
    tracking = delivery_tracking_service.get_transaction_tracking(order_id)

    # Add user emails to tracking
    for track in tracking:
        if track.get('created_by'):
            creator = user_service.get(track['created_by'])
            if creator:
                track['created_by_email'] = creator.get('email', '')

    transaction_dict['tracking'] = tracking
    transaction_dict['status_description'] = current_app.config['DELIVERY_STATUSES'].get(
        transaction.get('status'), 'Unknown status'
    )

    return render_template('order_tracking.html', transaction=transaction_dict)


@marketplace_bp.route('/follow/<seller_id>', methods=['POST'])
@login_required
def follow_seller(seller_id):
    """Follow/unfollow a seller"""
    db = get_db()
    user = session.get('user')

    is_following = follow_service.is_following(user['id'], seller_id)

    if is_following:
        # Unfollow
        follow_service.unfollow(user['id'], seller_id)

        # Decrement follower count
        seller_ref = db.collection('sellers').document(seller_id)
        seller_ref.update({
            'follower_count': firestore.Increment(-1)
        })
        following = False
    else:
        # Follow
        follow_service.follow(user['id'], seller_id)

        # Increment follower count
        seller_ref = db.collection('sellers').document(seller_id)
        seller_ref.update({
            'follower_count': firestore.Increment(1)
        })
        following = True

    return jsonify({'success': True, 'following': following})


@marketplace_bp.route('/like/seller/<seller_id>', methods=['POST'])
@login_required
def like_seller(seller_id):
    """Like/unlike a seller"""
    db = get_db()
    user = session.get('user')

    # Check if seller exists
    seller = seller_service.get(seller_id)
    if not seller:
        return jsonify({'success': False, 'error': 'Seller not found'}), 404

    is_liked = like_service.is_seller_liked(user['id'], seller_id)

    if is_liked:
        # Unlike
        like_service.unlike_seller(user['id'], seller_id)

        # Decrement likes count
        seller_ref = db.collection('sellers').document(seller_id)
        seller_ref.update({
            'likes_count': firestore.Increment(-1)
        })
        liked = False
    else:
        # Like
        like_service.like_seller(user['id'], seller_id)

        # Increment likes count
        seller_ref = db.collection('sellers').document(seller_id)
        seller_ref.update({
            'likes_count': firestore.Increment(1)
        })
        liked = True

    # Get updated likes count
    seller_updated = seller_service.get(seller_id)

    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': seller_updated.get('likes_count', 0)
    })


@marketplace_bp.route('/like/video/<video_id>', methods=['POST'])
@login_required
def like_video(video_id):
    """Like/unlike a video"""
    user = session.get('user')

    # Check if video exists
    video = video_service.get(video_id)
    if not video:
        return jsonify({'success': False, 'error': 'Video not found'}), 404

    is_liked = like_service.is_video_liked(user['id'], video_id)

    if is_liked:
        # Unlike
        like_service.unlike_video(user['id'], video_id)
        video_service.decrement_likes(video_id)
        liked = False
    else:
        # Like
        like_service.like_video(user['id'], video_id)
        video_service.increment_likes(video_id)
        liked = True

    # Get updated likes count
    video_updated = video_service.get(video_id)

    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': video_updated.get('likes_count', 0)
    })


@marketplace_bp.route('/transactions')
def transactions_explorer():
    """Transaction explorer with role-based access"""
    from flask import request, session
    db = get_db()
    user_service = get_user_service()

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
            try:
                allowed_id = f"buyer{int(user_id.replace('user_', '')):06d}"
            except:
                allowed_id = f"buyer_{user_id}"
        elif user_type == 'seller':
            seller_record = seller_service.get_by_user_id(user_id)
            allowed_id = f"seller_{seller_record['id']}" if seller_record else ""
        elif user_type == 'deliverer':
            # Get deliverer by user_id
            deliverer_docs = db.collection('deliverers').where(filter=FieldFilter('user_id', '==', user_id)).limit(1).stream()
            deliverer_record = None
            for doc in deliverer_docs:
                deliverer_record = {**doc.to_dict(), 'id': doc.id}
                break
            allowed_id = f"deliverer_{deliverer_record['id']}" if deliverer_record else ""
        else:
            allowed_id = ""

        # If search query doesn't match their own ID, clear it
        if search_query.lower() not in allowed_id.lower():
            search_query = ""  # Clear invalid search

    # Build query based on user role
    transactions = []
    if is_admin:
        # Admins see all transactions (limit 100)
        trans_docs = db.collection('transactions').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(100).stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in trans_docs]
    elif current_user:
        # Buyers see their own transactions
        if user_type == 'buyer':
            trans_docs = db.collection('transactions').where(filter=FieldFilter('user_id', '==', user_id)).limit(50).stream()
            transactions = [{**doc.to_dict(), 'id': doc.id} for doc in trans_docs]
            # Sort by timestamp in Python (avoids need for composite index)
            transactions.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        # Sellers see transactions where they are the seller
        elif user_type == 'seller':
            seller_record = seller_service.get_by_user_id(user_id)
            if seller_record:
                trans_docs = db.collection('transactions').where(filter=FieldFilter('seller_id', '==', seller_record['id'])).limit(50).stream()
                transactions = [{**doc.to_dict(), 'id': doc.id} for doc in trans_docs]
                # Sort by timestamp in Python (avoids need for composite index)
                transactions.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        # Deliverers see transactions where they are the deliverer
        elif user_type == 'deliverer':
            deliverer_docs = db.collection('deliverers').where(filter=FieldFilter('user_id', '==', user_id)).limit(1).stream()
            deliverer_record = None
            for doc in deliverer_docs:
                deliverer_record = {**doc.to_dict(), 'id': doc.id}
                break
            if deliverer_record:
                trans_docs = db.collection('transactions').where(filter=FieldFilter('deliverer_id', '==', deliverer_record['id'])).limit(50).stream()
                transactions = [{**doc.to_dict(), 'id': doc.id} for doc in trans_docs]
                # Sort by timestamp in Python (avoids need for composite index)
                transactions.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

    # Process transactions and add related data
    transactions_list = []
    for t in transactions:
        transaction = t.copy()

        # Get buyer info
        if transaction.get('user_id'):
            buyer = user_service.get(transaction['user_id'])
            if buyer:
                transaction['buyer_email'] = buyer.get('email', '')
                transaction['buyer_type'] = buyer.get('user_type', '')

        # Get seller info
        if transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller:
                transaction['seller_name'] = seller.get('name', '')
                transaction['seller_handle'] = seller.get('handle', '')

        # Get deliverer info
        if transaction.get('deliverer_id'):
            deliverer_doc = db.collection('deliverers').document(transaction['deliverer_id']).get()
            if deliverer_doc.exists:
                deliverer = deliverer_doc.to_dict()
                transaction['deliverer_user_id'] = deliverer.get('user_id')

        # Generate user identifiers - handle string IDs properly
        try:
            transaction['buyer_identifier'] = f"buyer{int(transaction.get('user_id', '0').replace('user_', '')):06d}" if transaction.get('user_id') else "unknown"
        except:
            transaction['buyer_identifier'] = f"buyer_{transaction.get('user_id', 'unknown')}"

        transaction['seller_identifier'] = f"seller_{transaction.get('seller_id', 'none')}"
        transaction['deliverer_identifier'] = f"deliverer_{transaction.get('deliverer_id', 'none')}"

        # Generate transaction hash
        import hashlib
        timestamp_str = str(transaction.get('timestamp', ''))
        timestamp_hash = hashlib.sha1(timestamp_str.encode()).hexdigest()[:8]
        transaction['tx_hash'] = f"0x{transaction['id'][:6]}{timestamp_hash}"
        transaction['display_amount'] = f"R{transaction.get('total_amount', 0):.2f}"
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
            try:
                user_identifier = f"buyer{int(user_id.replace('user_', '')):06d}"
            except:
                user_identifier = f"buyer_{user_id}"
        elif user_type == 'seller':
            seller_record = seller_service.get_by_user_id(user_id)
            if seller_record:
                user_identifier = f"seller_{seller_record['id']}"
        elif user_type == 'deliverer':
            deliverer_docs = db.collection('deliverers').where(filter=FieldFilter('user_id', '==', user_id)).limit(1).stream()
            for doc in deliverer_docs:
                user_identifier = f"deliverer_{doc.id}"
                break

    return render_template('transactions_explorer.html',
                         transactions=transactions_list,
                         is_admin=is_admin,
                         user_identifier=user_identifier,
                         search_query=search_query)


# ============================================================================
# ORDER CHAT ROUTES
# ============================================================================

@marketplace_bp.route('/order/<order_id>/chat')
@login_required
def order_chat(order_id):
    """Order chat page"""
    from shared.firebase_chat_utils import can_user_access_chat, get_chat_messages, get_unread_count, mark_messages_as_read
    db = get_db()
    user_service = get_user_service()
    user = session.get('user')

    # Check access
    has_access, role = can_user_access_chat(user['id'], order_id)
    if not has_access:
        flash('You do not have access to this chat', 'error')
        return redirect(url_for('marketplace.feed'))

    # Get order details
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))

    transaction = transaction_doc.to_dict()
    transaction['id'] = transaction_doc.id
    transaction_dict = transaction.copy()
    transaction_dict['user_role'] = role

    # Get seller name
    if transaction.get('seller_id'):
        seller = seller_service.get(transaction['seller_id'])
        if seller:
            transaction_dict['seller_name'] = seller.get('name', '')

    # Get buyer email
    if transaction.get('user_id'):
        buyer = user_service.get(transaction['user_id'])
        if buyer:
            transaction_dict['buyer_email'] = buyer.get('email', '')

    # Get driver info
    driver_user_id = None
    driver_email = None
    if transaction.get('driver_id'):
        driver_doc = db.collection('drivers').document(transaction['driver_id']).get()
        if driver_doc.exists:
            driver = driver_doc.to_dict()
            driver_user_id = driver.get('user_id')
            if driver_user_id:
                driver_user = user_service.get(driver_user_id)
                if driver_user:
                    driver_email = driver_user.get('email', '')

    transaction_dict['driver_user_id'] = driver_user_id
    transaction_dict['driver_email'] = driver_email

    # Get chat messages
    messages = get_chat_messages(order_id)

    # Mark messages as read
    mark_messages_as_read(order_id, user['id'])

    # Determine other party
    if role == 'buyer':
        other_user_id = driver_user_id
        other_user_name = driver_email or 'Deliverer'
    else:  # deliverer
        other_user_id = transaction.get('user_id')
        other_user_name = transaction_dict.get('buyer_email', 'Buyer')

    transaction_dict['other_user_id'] = other_user_id
    transaction_dict['other_user_name'] = other_user_name
    transaction_dict['messages'] = messages

    return render_template('order_chat.html',
                         transaction=transaction_dict,
                         current_user_id=user['id'])


@marketplace_bp.route('/order/<order_id>/chat/send', methods=['POST'])
@login_required
def send_chat_message(order_id):
    """Send a chat message"""
    from shared.firebase_chat_utils import send_chat_message as send_message, can_user_access_chat
    db = get_db()
    user = session.get('user')

    # Check access
    has_access, role = can_user_access_chat(user['id'], order_id)
    if not has_access:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    message = request.json.get('message', '').strip() if request.is_json else request.form.get('message', '').strip()

    if not message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400

    # Get recipient
    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    transaction = transaction_doc.to_dict()
    buyer_id = transaction.get('user_id')

    # Get driver user_id
    driver_user_id = None
    if transaction.get('driver_id'):
        driver_doc = db.collection('drivers').document(transaction['driver_id']).get()
        if driver_doc.exists:
            driver = driver_doc.to_dict()
            driver_user_id = driver.get('user_id')

    # Determine recipient
    if role == 'buyer':
        to_user_id = driver_user_id
    else:  # deliverer
        to_user_id = buyer_id

    if not to_user_id:
        return jsonify({'success': False, 'error': 'Recipient not available'}), 400

    # Send message
    result = send_message(order_id, user['id'], to_user_id, message)

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@marketplace_bp.route('/order/<order_id>/chat/messages')
@login_required
def get_chat_messages_api(order_id):
    """API endpoint to get chat messages (for live updates)"""
    from shared.firebase_chat_utils import can_user_access_chat, get_chat_messages
    
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


@marketplace_bp.route('/order/<order_id>/chat/flag/<message_id>', methods=['POST'])
@login_required
def flag_chat_message(order_id, message_id):
    """Flag a message for admin review"""
    from shared.firebase_chat_utils import can_user_access_chat, flag_message
    
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
    from shared.firebase_chat_utils import get_user_active_chats

    user = session.get('user')
    chats = get_user_active_chats(user['id'])

    return render_template('all_chats.html', chats=chats)


# ============================================================================
# API ROUTES FOR FLOATING SHOP MODAL
# ============================================================================

@marketplace_bp.route('/seller/<seller_id>/products')
def get_seller_products(seller_id):
    """API endpoint to fetch products for a specific seller"""
    import json
    product_service = get_product_service()

    try:
        # Get all active products for this seller
        all_products = product_service.get_seller_products(seller_id)
        active_products = [p for p in all_products if p.get('is_active', True)]

        # Sort by total_sales and created_at
        active_products.sort(key=lambda p: (p.get('total_sales', 0), p.get('created_at', '')), reverse=True)

        products_list = []
        for p in active_products:
            product_dict = p.copy()

            # Parse images JSON array and get first image
            try:
                images_array = json.loads(product_dict.get('images', '[]')) if isinstance(product_dict.get('images'), str) else product_dict.get('images', [])
                product_dict['image_url'] = images_array[0] if images_array else None
            except (json.JSONDecodeError, IndexError, TypeError):
                product_dict['image_url'] = None

            # Rename stock_count to stock_quantity for frontend compatibility
            if 'stock_count' in product_dict:
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
    product_service = get_product_service()
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

        # Get product details
        product = product_service.get(product_id)

        if not product or not product.get('is_active', True):
            return jsonify({
                'success': False,
                'message': 'Product not found'
            }), 404

        product_dict = product.copy()

        # Get seller information
        seller = seller_service.get(product.get('seller_id'))
        if seller:
            product_dict['seller_name'] = seller.get('name', '')
            product_dict['seller_id'] = seller.get('id')

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
    db = get_db()
    user = session.get('user')

    try:
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
        seller = seller_service.get(seller_id)
        if not seller:
            return jsonify({'success': False, 'error': 'Seller not found'}), 404

        # Check if user has already reviewed this seller
        existing_reviews = db.collection('reviews').where(filter=FieldFilter('user_id', '==', user['id'])).where(filter=FieldFilter('seller_id', '==', seller_id)).limit(1).stream()

        existing_review = None
        for doc in existing_reviews:
            existing_review = {**doc.to_dict(), 'id': doc.id}
            break

        if existing_review:
            # Update existing review
            db.collection('reviews').document(existing_review['id']).update({
                'rating': rating,
                'review_text': review_text,
                'updated_at': firestore.SERVER_TIMESTAMP
            })

            message = 'Review updated successfully!'
        else:
            # Create new review (seller-level review, not product-specific)
            review_service.create({
                'seller_id': seller_id,
                'user_id': user['id'],
                'rating': rating,
                'review_text': review_text,
                'product_id': None,
                'is_visible': True
            })

            message = 'Review submitted successfully!'

        # Update seller's average rating
        all_reviews = review_service.get_seller_reviews(seller_id)
        visible_reviews = [r for r in all_reviews if r.get('is_visible', True)]

        if visible_reviews:
            avg_rating = sum(r.get('rating', 0) for r in visible_reviews) / len(visible_reviews)
        else:
            avg_rating = 5.0

        seller_service.update(seller_id, {
            'avg_rating': avg_rating
        })

        return jsonify({
            'success': True,
            'message': message,
            'new_avg_rating': round(avg_rating, 1)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to submit review: {str(e)}'
        }), 500
