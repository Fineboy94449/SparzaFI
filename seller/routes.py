from flask import render_template, redirect, url_for, session, request, abort, jsonify, flash, send_file
from flask import current_app as app, g
from shared.utils import login_required, seller_required, get_db, log_error
from shared.components import render_chart_data
from . import seller_bp
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import csv
import io
import json
import os

# ==================== HELPER FUNCTIONS ====================

def get_seller_id(user_id):
    """Get seller ID from user ID"""
    db = get_db()
    seller = db.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,)).fetchone()
    return seller['id'] if seller else None

# ==================== ROUTES ====================

@seller_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup_profile():
    """Seller profile setup for new sellers"""
    user = session.get('user')
    db = get_db()

    # Check if seller profile already exists
    existing_seller = db.execute('SELECT * FROM sellers WHERE user_id = ?', (user['id'],)).fetchone()

    if request.method == 'POST':
        name = request.form.get('name')
        handle = request.form.get('handle')
        location = request.form.get('location')
        bio = request.form.get('bio', '')

        if not name or not handle or not location:
            flash('Name, handle, and location are required.', 'error')
            return render_template('seller_setup.html')

        try:
            if existing_seller:
                # Update existing profile
                db.execute("""
                    UPDATE sellers SET name = ?, handle = ?, location = ?, bio = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (name, handle, location, bio, user['id']))
            else:
                # Create new seller profile
                profile_initial = name[0].upper() if name else 'S'
                db.execute("""
                    INSERT INTO sellers (user_id, name, handle, profile_initial, location, bio)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user['id'], name, handle, profile_initial, location, bio))

                # Update user type to seller
                db.execute('UPDATE users SET user_type = "seller" WHERE id = ?', (user['id'],))
                session['user']['user_type'] = 'seller'

            db.commit()
            flash('Seller profile created successfully!', 'success')
            return redirect(url_for('seller.seller_dashboard'))

        except Exception as e:
            db.rollback()
            log_error(f"Seller Setup Error: {e}", user_id=user['id'])
            flash('Error creating seller profile. Handle may already be taken.', 'error')

    return render_template('seller_setup.html', existing_seller=dict(existing_seller) if existing_seller else None)

@seller_bp.route('/dashboard')
@login_required
@seller_required
def seller_dashboard():
    """Main Seller Dashboard - Comprehensive Overview"""
    user = session.get('user')
    db = get_db()

    # Get seller ID by user_id
    seller_id = user['id']

    # Fetch seller data, including rating and verification status
    seller_data = db.execute('SELECT * FROM sellers WHERE user_id = ?', (seller_id,)).fetchone()

    # Handle case where seller profile doesn't exist yet
    if not seller_data:
        flash('Please complete your seller profile setup.', 'warning')
        return redirect(url_for('seller.setup_profile'))

    # Get actual seller ID
    actual_seller_id = seller_data['id']

    # ====== DASHBOARD STATISTICS ======

    # Total Sales (completed transactions)
    total_sales = db.execute("""
        SELECT COALESCE(SUM(seller_amount), 0) as total
        FROM transactions
        WHERE seller_id = ? AND status IN ('COMPLETED', 'DELIVERED')
    """, (actual_seller_id,)).fetchone()['total']

    # Pending Orders Count
    pending_orders_count = db.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE seller_id = ? AND status IN ('PENDING', 'CONFIRMED')
    """, (actual_seller_id,)).fetchone()['count']

    # Active Products Count
    active_products_count = db.execute("""
        SELECT COUNT(*) as count
        FROM products
        WHERE seller_id = ? AND is_active = 1
    """, (actual_seller_id,)).fetchone()['count']

    # Wallet Balance
    wallet_balance = seller_data['balance']

    # Followers and Likes
    followers_count = seller_data['follower_count']
    likes_count = seller_data['likes_count']

    # ====== PENDING ORDERS ======
    pending_orders = db.execute("""
        SELECT t.*, u.email as buyer_email
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.seller_id = ? AND t.status IN ('PENDING', 'CONFIRMED', 'READY_FOR_PICKUP')
        ORDER BY t.timestamp DESC
        LIMIT 10
    """, (actual_seller_id,)).fetchall()

    # ====== PRODUCTS ======
    products = db.execute("""
        SELECT * FROM products
        WHERE seller_id = ?
        ORDER BY created_at DESC
    """, (actual_seller_id,)).fetchall()

    # ====== VIDEOS ======
    videos = db.execute("""
        SELECT * FROM videos
        WHERE seller_id = ?
        ORDER BY
            CASE video_type
                WHEN 'intro' THEN 1
                WHEN 'detailed' THEN 2
                WHEN 'conclusion' THEN 3
            END
    """, (actual_seller_id,)).fetchall()

    # ====== RECENT TRANSACTIONS (for earnings history) ======
    recent_transactions = db.execute("""
        SELECT t.*, u.email as buyer_email
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.seller_id = ?
        ORDER BY t.timestamp DESC
        LIMIT 20
    """, (actual_seller_id,)).fetchall()

    # ====== ANALYTICS DATA ======
    # Sales over last 7 days
    last_7_days_sales = db.execute("""
        SELECT DATE(timestamp) as date, SUM(seller_amount) as daily_total
        FROM transactions
        WHERE seller_id = ? AND status IN ('COMPLETED', 'DELIVERED')
        AND timestamp >= date('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    """, (actual_seller_id,)).fetchall()

    # Most Popular Products
    popular_products = db.execute("""
        SELECT p.name, SUM(ti.quantity) as sales_count, SUM(ti.total_price) as revenue
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        JOIN transactions t ON ti.transaction_id = t.id
        WHERE p.seller_id = ? AND t.status IN ('COMPLETED', 'DELIVERED')
        GROUP BY p.id
        ORDER BY sales_count DESC
        LIMIT 5
    """, (actual_seller_id,)).fetchall()

    # ====== REVIEWS ======
    recent_reviews = db.execute("""
        SELECT r.*, u.email as buyer_email
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.seller_id = ?
        ORDER BY r.created_at DESC
        LIMIT 5
    """, (actual_seller_id,)).fetchall()

    return render_template('seller_dashboard.html',
                           seller=dict(seller_data),
                           stats={
                               'total_sales': total_sales,
                               'pending_orders': pending_orders_count,
                               'active_products': active_products_count,
                               'wallet_balance': wallet_balance,
                               'followers': followers_count,
                               'likes': likes_count
                           },
                           pending_orders=[dict(o) for o in pending_orders],
                           products=[dict(p) for p in products],
                           videos=[dict(v) for v in videos],
                           recent_transactions=[dict(t) for t in recent_transactions],
                           last_7_days_sales=[dict(s) for s in last_7_days_sales],
                           popular_products=[dict(p) for p in popular_products],
                           recent_reviews=[dict(r) for r in recent_reviews])

@seller_bp.route('/products', methods=['GET', 'POST'])
@login_required
@seller_required
def manage_products():
    """Product CRUD (Create/Read/Update/Delete)"""
    user = session.get('user')
    db = get_db()

    # Get seller ID from sellers table
    seller = db.execute('SELECT id FROM sellers WHERE user_id = ?', (user['id'],)).fetchone()
    if not seller:
        flash('Seller profile not found. Please complete setup.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    seller_id = seller['id']

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)

        # 16. Automated Content Moderation Check
        # This function would check description against BAD_WORDS from config.py
        # moderation_utils.flag_content(user['id'], description)

        try:
            db.execute("""
                INSERT INTO products (seller_id, name, description, price)
                VALUES (?, ?, ?, ?)
            """, (seller_id, name, description, price))
            db.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('seller.manage_products'))
        except Exception as e:
            db.rollback()
            log_error(f"Seller Product Creation Error: {e}", traceback=str(e.__traceback__), user_id=user['id'])
            flash('Error adding product.', 'danger')

    products = db.execute('SELECT * FROM products WHERE seller_id = ? ORDER BY created_at DESC', (seller_id,)).fetchall()

    return render_template('seller_products.html', products=[dict(p) for p in products])

@seller_bp.route('/orders')
@login_required
@seller_required
def manage_orders():
    """View and Confirm incoming orders"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    # Fetch orders awaiting seller action
    orders = db.execute("""
        SELECT t.*, u.email as buyer_email
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.seller_id = ? AND t.status IN ('PENDING', 'CONFIRMED', 'READY_FOR_PICKUP')
        ORDER BY t.timestamp DESC
    """, (seller_id,)).fetchall()

    return render_template('seller_orders.html', orders=[dict(o) for o in orders])

@seller_bp.route('/order/<int:order_id>/confirm', methods=['POST'])
@login_required
@seller_required
def confirm_order(order_id):
    """Seller confirms a PENDING order"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    result = db.execute("""
        UPDATE transactions SET status = 'CONFIRMED', updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND seller_id = ? AND status = 'PENDING'
    """, (order_id, seller_id)).rowcount

    if result:
        # Add tracking update
        db.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'CONFIRMED', 'Seller confirmed order', ?)
        """, (order_id, user['id']))

        db.commit()

        # Create notification for buyer
        transaction = db.execute('SELECT user_id FROM transactions WHERE id = ?', (order_id,)).fetchone()
        if transaction:
            db.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type, related_id)
                VALUES (?, 'Order Confirmed', 'Your order has been confirmed by the seller', 'order', ?)
            """, (transaction['user_id'], order_id))
            db.commit()

        flash('Order confirmed successfully!', 'success')
        return jsonify({'success': True, 'message': 'Order confirmed and preparation started.'})

    return jsonify({'success': False, 'message': 'Order not found or already confirmed.'}), 400


@seller_bp.route('/order/<int:order_id>/ready', methods=['POST'])
@login_required
@seller_required
def mark_ready_for_pickup(order_id):
    """Mark order as ready for pickup and generate pickup code"""
    import secrets
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    # Generate 6-digit pickup code
    pickup_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    result = db.execute("""
        UPDATE transactions
        SET status = 'READY_FOR_PICKUP', pickup_code = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND seller_id = ? AND status = 'CONFIRMED'
    """, (pickup_code, order_id, seller_id)).rowcount

    if result:
        # Add tracking update
        db.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'READY_FOR_PICKUP', 'Order ready for pickup. Code: {}', ?)
        """.format(pickup_code), (order_id, user['id']))

        db.commit()

        # Notify buyer
        transaction = db.execute('SELECT user_id FROM transactions WHERE id = ?', (order_id,)).fetchone()
        if transaction:
            db.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type, related_id)
                VALUES (?, 'Order Ready', 'Your order is ready for pickup. Code: {}', 'order', ?)
            """.format(pickup_code), (transaction['user_id'], order_id))
            db.commit()

        flash(f'Order marked as ready! Pickup code: {pickup_code}', 'success')
        return jsonify({'success': True, 'message': f'Order ready for pickup. Code: {pickup_code}', 'pickup_code': pickup_code})

    return jsonify({'success': False, 'message': 'Order not found or not confirmed yet.'}), 400


@seller_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
@seller_required
def cancel_order(order_id):
    """Cancel an order"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    reason = request.form.get('reason', 'Cancelled by seller')

    result = db.execute("""
        UPDATE transactions
        SET status = 'CANCELLED', cancelled_reason = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND seller_id = ? AND status IN ('PENDING', 'CONFIRMED')
    """, (reason, order_id, seller_id)).rowcount

    if result:
        # Add tracking update
        db.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'CANCELLED', ?, ?)
        """, (order_id, reason, user['id']))

        db.commit()

        # Notify buyer
        transaction = db.execute('SELECT user_id FROM transactions WHERE id = ?', (order_id,)).fetchone()
        if transaction:
            db.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type, related_id)
                VALUES (?, 'Order Cancelled', 'Your order has been cancelled. Reason: {}', 'order', ?)
            """.format(reason), (transaction['user_id'], order_id))
            db.commit()

        flash('Order cancelled successfully', 'info')
        return jsonify({'success': True, 'message': 'Order cancelled.'})

    return jsonify({'success': False, 'message': 'Order not found or cannot be cancelled.'}), 400


# ==================== VIDEO MANAGEMENT ====================

@seller_bp.route('/videos/upload', methods=['POST'])
@login_required
@seller_required
def upload_video():
    """Upload or update a business video"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    video_type = request.form.get('video_type')  # intro, detailed, conclusion
    title = request.form.get('title')
    caption = request.form.get('caption', '')
    video_url = request.form.get('video_url')  # URL or uploaded file path
    duration = request.form.get('duration', type=int)

    if not video_type or video_type not in ['intro', 'detailed', 'conclusion']:
        return jsonify({'success': False, 'message': 'Invalid video type'}), 400

    try:
        # Check if video of this type already exists
        existing = db.execute("""
            SELECT id FROM videos WHERE seller_id = ? AND video_type = ?
        """, (seller_id, video_type)).fetchone()

        if existing:
            # Update existing video
            db.execute("""
                UPDATE videos
                SET title = ?, caption = ?, video_url = ?, duration = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (title, caption, video_url, duration, existing['id']))
            message = f'{video_type.capitalize()} video updated successfully!'
        else:
            # Insert new video
            db.execute("""
                INSERT INTO videos (seller_id, video_type, title, caption, video_url, duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (seller_id, video_type, title, caption, video_url, duration))
            message = f'{video_type.capitalize()} video added successfully!'

        db.commit()
        flash(message, 'success')
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db.rollback()
        log_error(f"Video Upload Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error uploading video.'}), 500


@seller_bp.route('/videos/<int:video_id>/delete', methods=['POST'])
@login_required
@seller_required
def delete_video(video_id):
    """Delete a business video"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    try:
        result = db.execute("""
            DELETE FROM videos
            WHERE id = ? AND seller_id = ?
        """, (video_id, seller_id)).rowcount

        db.commit()

        if result:
            flash('Video deleted successfully', 'success')
            return jsonify({'success': True, 'message': 'Video deleted successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Video not found.'}), 404

    except Exception as e:
        db.rollback()
        log_error(f"Video Deletion Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error deleting video.'}), 500


# ==================== WITHDRAWAL & EARNINGS ====================

@seller_bp.route('/request-withdrawal', methods=['POST'])
@login_required
@seller_required
def request_withdrawal():
    """Request withdrawal of earnings"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    # Get seller data
    seller = db.execute('SELECT balance FROM sellers WHERE id = ?', (seller_id,)).fetchone()
    amount = request.form.get('amount', type=float)
    bank_name = request.form.get('bank_name')
    account_number = request.form.get('account_number')
    account_holder = request.form.get('account_holder')

    if not amount or amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid amount'}), 400

    if amount > seller['balance']:
        return jsonify({'success': False, 'message': 'Insufficient balance'}), 400

    if not bank_name or not account_number or not account_holder:
        return jsonify({'success': False, 'message': 'Bank details required'}), 400

    try:
        # Create withdrawal request
        db.execute("""
            INSERT INTO withdrawal_requests
            (user_id, amount_spz, amount_zar, bank_name, account_number, account_holder, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (user['id'], amount, amount, bank_name, account_number, account_holder))

        # Deduct from seller balance (will be refunded if rejected)
        db.execute("""
            UPDATE sellers SET balance = balance - ? WHERE id = ?
        """, (amount, seller_id))

        db.commit()

        flash('Withdrawal request submitted successfully!', 'success')
        return jsonify({'success': True, 'message': 'Withdrawal request submitted. Processing time: 1-3 business days.'})

    except Exception as e:
        db.rollback()
        log_error(f"Withdrawal Request Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error processing withdrawal request.'}), 500


@seller_bp.route('/profile/update', methods=['POST'])
@login_required
@seller_required
def update_profile():
    """Update seller business profile"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    name = request.form.get('name')
    bio = request.form.get('bio')
    location = request.form.get('location')
    # banner_image would be handled with file upload

    try:
        db.execute("""
            UPDATE sellers
            SET name = ?, bio = ?, location = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name, bio, location, seller_id))

        db.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('seller.seller_dashboard'))

    except Exception as e:
        db.rollback()
        log_error(f"Profile Update Error: {e}", user_id=user['id'])
        flash('Error updating profile.', 'danger')
        return redirect(url_for('seller.seller_dashboard'))


@seller_bp.route('/feedback')
@login_required
@seller_required
def customer_feedback():
    """7. Ratings & Reviews System - Seller view of their feedback"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    reviews = db.execute("""
        SELECT r.*, u.email
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.seller_id = ?
        ORDER BY r.created_at DESC
    """, (seller_id,)).fetchall()

    return render_template('seller_feedback.html', reviews=[dict(r) for r in reviews])

@seller_bp.route('/messages')
@login_required
@seller_required
def seller_messages():
    """4. Direct buyer–seller messaging via an in-app chatbox"""
    user = session.get('user')
    db = get_db()

    # Fetch threads/unique users who have messaged this seller
    threads = db.execute("""
        SELECT DISTINCT u.id as user_id, u.email, u.profile_picture, MAX(m.created_at) as last_message_time
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.recipient_id = ?
        GROUP BY u.id
        ORDER BY last_message_time DESC
    """, (user['id'],)).fetchall()

    return render_template('seller_messages.html', threads=[dict(t) for t in threads])

# ==================== PRODUCT MANAGEMENT: EDIT & DELETE ====================

@seller_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@seller_required
def edit_product(product_id):
    """Edit an existing product"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    # Verify ownership
    product = db.execute('SELECT * FROM products WHERE id = ? AND seller_id = ?',
                        (product_id, seller_id)).fetchone()

    if not product:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        stock_count = request.form.get('stock_count', type=int)
        category = request.form.get('category')
        is_active = request.form.get('is_active', type=int, default=1)

        try:
            db.execute("""
                UPDATE products
                SET name = ?, description = ?, price = ?, stock_count = ?,
                    category = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND seller_id = ?
            """, (name, description, price, stock_count, category, is_active, product_id, seller_id))
            db.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('seller.manage_products'))
        except Exception as e:
            db.rollback()
            log_error(f"Product Update Error: {e}", user_id=user['id'])
            flash('Error updating product.', 'danger')

    return render_template('seller_product_edit.html', product=dict(product))

@seller_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@seller_required
def delete_product(product_id):
    """Delete a product (soft delete by setting is_active = 0)"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    try:
        result = db.execute("""
            UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND seller_id = ?
        """, (product_id, seller_id)).rowcount
        db.commit()

        if result:
            return jsonify({'success': True, 'message': 'Product deleted successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Product not found.'}), 404
    except Exception as e:
        db.rollback()
        log_error(f"Product Deletion Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error deleting product.'}), 500

# ==================== BULK UPLOAD & EDITING ====================

@seller_bp.route('/products/bulk-upload', methods=['GET', 'POST'])
@login_required
@seller_required
def bulk_upload_products():
    """Bulk upload products via CSV"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)

        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)

                success_count = 0
                error_count = 0

                for row in csv_reader:
                    try:
                        db.execute("""
                            INSERT INTO products (seller_id, name, description, price, stock_count, category, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, 1)
                        """, (
                            seller_id,
                            row.get('name', 'Unnamed Product'),
                            row.get('description', ''),
                            float(row.get('price', 0)),
                            int(row.get('stock_count', 0)),
                            row.get('category', 'General')
                        ))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        log_error(f"Bulk Upload Row Error: {e}", user_id=user['id'])

                db.commit()
                flash(f'Bulk upload completed! {success_count} products added, {error_count} errors.', 'success')
                return redirect(url_for('seller.manage_products'))

            except Exception as e:
                db.rollback()
                log_error(f"Bulk Upload Error: {e}", user_id=user['id'])
                flash('Error processing CSV file.', 'danger')
        else:
            flash('Invalid file format. Please upload a CSV file.', 'danger')

    return render_template('seller_bulk_upload.html')

@seller_bp.route('/products/bulk-edit', methods=['POST'])
@login_required
@seller_required
def bulk_edit_products():
    """Bulk edit multiple products at once"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    product_ids = request.form.getlist('product_ids[]')
    action = request.form.get('action')

    if not product_ids or not action:
        return jsonify({'success': False, 'message': 'Invalid request.'}), 400

    try:
        if action == 'activate':
            db.execute(f"""
                UPDATE products SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({','.join('?' * len(product_ids))}) AND seller_id = ?
            """, (*product_ids, seller_id))
        elif action == 'deactivate':
            db.execute(f"""
                UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({','.join('?' * len(product_ids))}) AND seller_id = ?
            """, (*product_ids, seller_id))
        elif action == 'delete':
            db.execute(f"""
                UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({','.join('?' * len(product_ids))}) AND seller_id = ?
            """, (*product_ids, seller_id))
        else:
            return jsonify({'success': False, 'message': 'Invalid action.'}), 400

        db.commit()
        return jsonify({'success': True, 'message': f'Products {action}d successfully.'})
    except Exception as e:
        db.rollback()
        log_error(f"Bulk Edit Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error performing bulk action.'}), 500

# ==================== INVENTORY TRACKING: LOW STOCK ALERTS ====================

@seller_bp.route('/inventory/alerts')
@login_required
@seller_required
def inventory_alerts():
    """View low stock alerts and inventory status"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    low_stock_threshold = request.args.get('threshold', default=10, type=int)

    # Get low stock products
    low_stock_products = db.execute("""
        SELECT * FROM products
        WHERE seller_id = ? AND stock_count <= ? AND is_active = 1
        ORDER BY stock_count ASC
    """, (seller_id, low_stock_threshold)).fetchall()

    # Get out of stock products
    out_of_stock = db.execute("""
        SELECT * FROM products
        WHERE seller_id = ? AND stock_count = 0 AND is_active = 1
        ORDER BY updated_at DESC
    """, (seller_id,)).fetchall()

    return render_template('seller_inventory_alerts.html',
                          low_stock=[dict(p) for p in low_stock_products],
                          out_of_stock=[dict(p) for p in out_of_stock],
                          threshold=low_stock_threshold)

@seller_bp.route('/inventory/update-stock', methods=['POST'])
@login_required
@seller_required
def update_stock():
    """Quick update stock count for a product"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    product_id = request.form.get('product_id', type=int)
    new_stock = request.form.get('stock_count', type=int)

    try:
        result = db.execute("""
            UPDATE products SET stock_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND seller_id = ?
        """, (new_stock, product_id, seller_id)).rowcount
        db.commit()

        if result:
            return jsonify({'success': True, 'message': 'Stock updated successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Product not found.'}), 404
    except Exception as e:
        db.rollback()
        log_error(f"Stock Update Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error updating stock.'}), 500

# ==================== CUSTOMER REVIEWS: RESPOND TO FEEDBACK ====================

@seller_bp.route('/reviews/<int:review_id>/respond', methods=['POST'])
@login_required
@seller_required
def respond_to_review(review_id):
    """Respond to a customer review"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    response_text = request.form.get('response')

    if not response_text:
        return jsonify({'success': False, 'message': 'Response text is required.'}), 400

    try:
        # Verify the review belongs to this seller
        review = db.execute("""
            SELECT * FROM reviews WHERE id = ? AND seller_id = ?
        """, (review_id, seller_id)).fetchone()

        if not review:
            return jsonify({'success': False, 'message': 'Review not found.'}), 404

        db.execute("""
            UPDATE reviews
            SET seller_response = ?, seller_responded_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (response_text, review_id))
        db.commit()

        return jsonify({'success': True, 'message': 'Response posted successfully.'})
    except Exception as e:
        db.rollback()
        log_error(f"Review Response Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error posting response.'}), 500

# ==================== AUTOMATED INVOICING ====================

@seller_bp.route('/invoices')
@login_required
@seller_required
def invoices():
    """View all invoices for completed orders"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    invoices = db.execute("""
        SELECT t.*, u.email as buyer_email, u.phone as buyer_phone
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.seller_id = ? AND t.status IN ('COMPLETED', 'DELIVERED')
        ORDER BY t.timestamp DESC
    """, (seller_id,)).fetchall()

    return render_template('seller_invoices.html', invoices=[dict(i) for i in invoices])

@seller_bp.route('/invoices/<int:transaction_id>/generate', methods=['GET'])
@login_required
@seller_required
def generate_invoice(transaction_id):
    """Generate and download invoice for a transaction"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    # Get transaction details
    transaction = db.execute("""
        SELECT t.*, u.email as buyer_email, u.phone as buyer_phone, u.address as buyer_address,
               s.name as seller_name, s.location as seller_location
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        JOIN sellers s ON t.seller_id = s.id
        WHERE t.id = ? AND t.seller_id = ?
    """, (transaction_id, seller_id)).fetchone()

    if not transaction:
        abort(404)

    # Get transaction items
    items = db.execute("""
        SELECT ti.*, p.name as product_name
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        WHERE ti.transaction_id = ?
    """, (transaction_id,)).fetchall()

    # Generate invoice HTML/PDF (simplified HTML version)
    invoice_html = render_template('seller_invoice_template.html',
                                   transaction=dict(transaction),
                                   items=[dict(i) for i in items],
                                   invoice_date=datetime.now().strftime('%Y-%m-%d'))

    return invoice_html

@seller_bp.route('/invoices/<int:transaction_id>/send', methods=['POST'])
@login_required
@seller_required
def send_invoice(transaction_id):
    """Send invoice to buyer via email (placeholder for email integration)"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        return jsonify({'success': False, 'message': 'Seller profile not found.'}), 403

    # Verify transaction belongs to seller
    transaction = db.execute("""
        SELECT * FROM transactions WHERE id = ? AND seller_id = ?
    """, (transaction_id, seller_id)).fetchone()

    if not transaction:
        return jsonify({'success': False, 'message': 'Transaction not found.'}), 404

    # TODO: Implement email sending logic here
    # For now, just create a notification
    try:
        db.execute("""
            INSERT INTO notifications (user_id, title, message, notification_type, related_id)
            VALUES (?, 'Invoice Sent', 'Your invoice has been generated and sent.', 'order', ?)
        """, (user['id'], transaction_id))
        db.commit()

        return jsonify({'success': True, 'message': 'Invoice sent successfully.'})
    except Exception as e:
        db.rollback()
        log_error(f"Invoice Send Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error sending invoice.'}), 500

# ==================== PROMOTIONS & DISCOUNTS ====================

@seller_bp.route('/promotions')
@login_required
@seller_required
def promotions():
    """View and manage seller-specific promotions"""
    user = session.get('user')
    db = get_db()

    # Get seller's promotions (filter by created_by)
    seller_promos = db.execute("""
        SELECT * FROM promotion_codes
        WHERE created_by = ?
        ORDER BY created_at DESC
    """, (user['id'],)).fetchall()

    return render_template('seller_promotions.html', promotions=[dict(p) for p in seller_promos])

@seller_bp.route('/promotions/create', methods=['GET', 'POST'])
@login_required
@seller_required
def create_promotion():
    """Create a new promotional campaign"""
    user = session.get('user')
    db = get_db()

    if request.method == 'POST':
        code = request.form.get('code').upper()
        discount_percent = request.form.get('discount_percent', type=float)
        discount_amount = request.form.get('discount_amount', type=float)
        minimum_purchase = request.form.get('minimum_purchase', type=float, default=0)
        valid_until = request.form.get('valid_until')
        uses_remaining = request.form.get('uses_remaining', type=int)

        try:
            db.execute("""
                INSERT INTO promotion_codes
                (code, discount_percent, discount_amount, minimum_purchase, valid_until, uses_remaining, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (code, discount_percent, discount_amount, minimum_purchase, valid_until, uses_remaining, user['id']))
            db.commit()
            flash('Promotion created successfully!', 'success')
            return redirect(url_for('seller.promotions'))
        except Exception as e:
            db.rollback()
            log_error(f"Promotion Creation Error: {e}", user_id=user['id'])
            flash('Error creating promotion. Code may already exist.', 'danger')

    return render_template('seller_promotion_create.html')

@seller_bp.route('/promotions/<int:promo_id>/toggle', methods=['POST'])
@login_required
@seller_required
def toggle_promotion(promo_id):
    """Activate or deactivate a promotion"""
    user = session.get('user')
    db = get_db()

    try:
        promo = db.execute('SELECT is_active FROM promotion_codes WHERE id = ? AND created_by = ?',
                          (promo_id, user['id'])).fetchone()

        if not promo:
            return jsonify({'success': False, 'message': 'Promotion not found.'}), 404

        new_status = 0 if promo['is_active'] else 1
        db.execute('UPDATE promotion_codes SET is_active = ? WHERE id = ?', (new_status, promo_id))
        db.commit()

        return jsonify({'success': True, 'message': 'Promotion status updated.', 'is_active': new_status})
    except Exception as e:
        db.rollback()
        log_error(f"Promotion Toggle Error: {e}", user_id=user['id'])
        return jsonify({'success': False, 'message': 'Error updating promotion.'}), 500

# ==================== NOTIFICATIONS SYSTEM ====================

@seller_bp.route('/notifications')
@login_required
@seller_required
def notifications():
    """View all seller notifications"""
    user = session.get('user')
    db = get_db()

    all_notifications = db.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (user['id'],)).fetchall()

    # Mark as read
    db.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0', (user['id'],))
    db.commit()

    return render_template('seller_notifications.html', notifications=[dict(n) for n in all_notifications])

# ==================== ANALYTICS ENHANCEMENTS ====================

@seller_bp.route('/analytics/detailed')
@login_required
@seller_required
def detailed_analytics():
    """Comprehensive analytics dashboard with real data"""
    user = session.get('user')
    db = get_db()

    seller_id = get_seller_id(user['id'])
    if not seller_id:
        flash('Seller profile not found.', 'danger')
        return redirect(url_for('seller.setup_profile'))

    # Revenue tracking by month
    monthly_revenue = db.execute("""
        SELECT strftime('%Y-%m', timestamp) as month, SUM(seller_amount) as revenue
        FROM transactions
        WHERE seller_id = ? AND status IN ('COMPLETED', 'DELIVERED')
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """, (seller_id,)).fetchall()

    # Top selling products
    top_products = db.execute("""
        SELECT p.name, SUM(ti.quantity) as total_sold, SUM(ti.total_price) as revenue
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        JOIN transactions t ON ti.transaction_id = t.id
        WHERE p.seller_id = ? AND t.status IN ('COMPLETED', 'DELIVERED')
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 10
    """, (seller_id,)).fetchall()

    # Order status breakdown
    order_stats = db.execute("""
        SELECT status, COUNT(*) as count
        FROM transactions
        WHERE seller_id = ?
        GROUP BY status
    """, (seller_id,)).fetchall()

    return render_template('seller_detailed_analytics.html',
                          monthly_revenue=[dict(r) for r in monthly_revenue],
                          top_products=[dict(p) for p in top_products],
                          order_stats=[dict(s) for s in order_stats])


# ==================== VERIFICATION CODE ENDPOINTS ====================

@seller_bp.route('/api/generate-pickup-code/<int:order_id>', methods=['POST'])
@login_required
@seller_required
def generate_pickup_code(order_id):
    """
    Seller generates pickup code when order is ready for delivery
    """
    user = session.get('user')
    db = get_db()

    # Verify seller owns this order
    seller_id = get_seller_id(user['id'])
    transaction = db.execute("""
        SELECT id FROM transactions
        WHERE id = ? AND seller_id = ?
    """, (order_id, seller_id)).fetchone()

    if not transaction:
        return jsonify({'success': False, 'error': 'Order not found or access denied'}), 404

    # Import the utility function
    from deliverer.utils import create_pickup_code

    result = create_pickup_code(order_id, user['id'])

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

# ==================== ENHANCED SELLER ORDER MANAGEMENT ====================

@seller_bp.route('/orders/buyer-codes')
@login_required
@seller_required
def view_buyer_delivery_codes():
    """View all buyer delivery codes for ready orders"""
    user = session.get('user')
    db = get_db()
    seller_id = get_seller_id(user['id'])
    
    # Get orders with buyer delivery codes
    orders = db.execute("""
        SELECT t.*, u.email as buyer_email,
               d.name as deliverer_name
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN deliverers d ON t.deliverer_id = d.id
        WHERE t.seller_id = ? AND t.delivery_code IS NOT NULL
        AND t.status IN ('READY_FOR_PICKUP', 'IN_TRANSIT', 'PICKED_UP')
        ORDER BY t.updated_at DESC
    """, (seller_id,)).fetchall()
    
    return render_template('seller/delivery_codes.html', orders=[dict(o) for o in orders])

@seller_bp.route('/returns')
@login_required
@seller_required
def manage_returns():
    """Manage return requests from buyers"""
    user = session.get('user')
    db = get_db()
    seller_id = get_seller_id(user['id'])
    
    # Get all return requests
    returns = db.execute("""
        SELECT r.*, t.id as transaction_id, t.total_amount,
               u.email as buyer_email,
               t.delivery_address
        FROM return_requests r
        JOIN transactions t ON r.transaction_id = t.id
        JOIN users u ON r.user_id = u.id
        WHERE r.seller_id = ?
        ORDER BY r.created_at DESC
    """, (seller_id,)).fetchall()
    
    # Separate by status
    pending_returns = [dict(r) for r in returns if r['status'] == 'PENDING']
    active_returns = [dict(r) for r in returns if r['status'] in ['APPROVED', 'PICKUP_SCHEDULED', 'PICKED_UP']]
    completed_returns = [dict(r) for r in returns if r['status'] in ['COMPLETED', 'REJECTED']]
    
    return render_template('seller/returns.html', 
                         pending=pending_returns,
                         active=active_returns,
                         completed=completed_returns)

@seller_bp.route('/return/<int:return_id>/approve', methods=['POST'])
@login_required
@seller_required
def approve_return(return_id):
    """Approve a return request"""
    user = session.get('user')
    db = get_db()
    seller_id = get_seller_id(user['id'])
    
    data = request.get_json()
    refund_amount = data.get('refund_amount')
    
    # Verify ownership
    return_req = db.execute("""
        SELECT * FROM return_requests
        WHERE id = ? AND seller_id = ?
    """, (return_id, seller_id)).fetchone()
    
    if not return_req:
        return jsonify({'success': False, 'error': 'Return not found'}), 404
    
    # Update return status
    db.execute("""
        UPDATE return_requests
        SET status = 'APPROVED', refund_amount = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (refund_amount, return_id))
    
    # Notify buyer
    from user.buyer_dashboard import send_notification
    send_notification(
        return_req['user_id'],
        'Return Approved',
        f'Your return request has been approved. Refund amount: R{refund_amount}',
        'order',
        return_req['transaction_id']
    )
    
    db.commit()
    return jsonify({'success': True, 'message': 'Return approved'})

@seller_bp.route('/return/<int:return_id>/reject', methods=['POST'])
@login_required
@seller_required
def reject_return(return_id):
    """Reject a return request"""
    user = session.get('user')
    db = get_db()
    seller_id = get_seller_id(user['id'])
    
    data = request.get_json()
    admin_notes = data.get('reason', '')
    
    # Verify ownership
    return_req = db.execute("""
        SELECT * FROM return_requests
        WHERE id = ? AND seller_id = ?
    """, (return_id, seller_id)).fetchone()
    
    if not return_req:
        return jsonify({'success': False, 'error': 'Return not found'}), 404
    
    # Update return status
    db.execute("""
        UPDATE return_requests
        SET status = 'REJECTED', admin_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (admin_notes, return_id))
    
    # Notify buyer
    from user.buyer_dashboard import send_notification
    send_notification(
        return_req['user_id'],
        'Return Rejected',
        f'Your return request has been rejected. Reason: {admin_notes}',
        'order',
        return_req['transaction_id']
    )
    
    db.commit()
    return jsonify({'success': True, 'message': 'Return rejected'})

@seller_bp.route('/order/<int:order_id>/download-slip')
@login_required
@seller_required
def download_order_slip(order_id):
    """Download order slip as CSV (seller version)"""
    user = session.get('user')
    db = get_db()
    seller_id = get_seller_id(user['id'])
    
    # Get order details
    order = db.execute("""
        SELECT t.*, u.email as buyer_email
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.id = ? AND t.seller_id = ?
    """, (order_id, seller_id)).fetchone()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Get order items
    items = db.execute("""
        SELECT ti.*, p.name as product_name
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        WHERE ti.transaction_id = ?
    """, (order_id,)).fetchall()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['SparzaFI Seller Order Slip'])
    writer.writerow(['Order ID', order_id])
    writer.writerow(['Date', order['timestamp']])
    writer.writerow(['Buyer', order['buyer_email']])
    writer.writerow(['Status', order['status']])
    writer.writerow(['Delivery Address', order['delivery_address']])
    writer.writerow([])
    
    writer.writerow(['Product', 'Quantity', 'Unit Price', 'Total'])
    for item in items:
        writer.writerow([
            item['product_name'],
            item['quantity'],
            f"R{item['unit_price']:.2f}",
            f"R{item['total_price']:.2f}"
        ])
    
    writer.writerow([])
    writer.writerow(['Seller Amount', f"R{order['seller_amount']:.2f}"])
    writer.writerow(['Platform Commission', f"R{order['platform_commission']:.2f}"])
    writer.writerow(['Order Total', f"R{order['total_amount']:.2f}"])
    
    if order['pickup_code']:
        writer.writerow([])
        writer.writerow(['Pickup Code', order['pickup_code']])
    
    if order['delivery_code']:
        writer.writerow(['Delivery Code', order['delivery_code']])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'seller_order_{order_id}_slip.csv'
    )
