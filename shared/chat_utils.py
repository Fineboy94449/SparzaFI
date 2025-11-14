"""
SparzaFi Deliverer Routes
Dashboard, delivery management, live tracking, earnings, and leaderboard
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, current_app
from . import deliverer_bp
from database_seed import get_db_connection
from shared.utils import login_required, generate_verification_code
from datetime import datetime, timedelta
import random


def deliverer_required(f):
    """Decorator to require deliverer access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('user_type') not in ['driver', 'admin']:
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@deliverer_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """Deliverer profile setup - Basic info only"""
    user = session.get('user')
    conn = get_db_connection()
    
    # Check if already a deliverer
    existing = conn.execute(
        'SELECT id FROM drivers WHERE user_id = ?', 
        (user['id'],)
    ).fetchone()
    
    if existing:
        flash('You are already registered as a deliverer!', 'info')
        return redirect(url_for('deliverer.dashboard'))
    
    if request.method == 'POST':
        license_number = request.form.get('license_number', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'walking')
        vehicle_registration = request.form.get('vehicle_registration', '').strip()
        service_description = request.form.get('service_description', '').strip()
        
        try:
            conn.execute("""
                INSERT INTO drivers 
                (user_id, license_number, vehicle_type, vehicle_registration, service_description,
                 is_verified, is_active, is_available)
                VALUES (?, ?, ?, ?, ?, 0, 1, 1)
            """, (user['id'], license_number, vehicle_type, vehicle_registration, service_description))
            
            # Update user type
            conn.execute("""
                UPDATE users 
                SET user_type = 'driver', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user['id'],))
            
            conn.commit()
            
            # Update session
            updated_user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            session['user'] = dict(updated_user)
            
            flash('Deliverer profile created! Now add your delivery routes.', 'success')
            return redirect(url_for('deliverer.manage_routes'))
            
        except Exception as e:
            conn.rollback()
            return render_template('deliverer/setup.html', error=f"Setup failed: {str(e)}")
    
    return render_template('deliverer/setup.html')


@deliverer_bp.route('/routes', methods=['GET'])
@login_required
@deliverer_required
def manage_routes():
    """Manage delivery routes"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT * FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    # Get all routes for this deliverer
    routes = conn.execute("""
        SELECT * FROM delivery_routes 
        WHERE driver_id = ?
        ORDER BY is_active DESC, created_at DESC
    """, (deliverer['id'],)).fetchall()
    
    routes_data = {
        'deliverer': dict(deliverer),
        'routes': [dict(r) for r in routes],
        'min_price_per_km': current_app.config['MIN_PRICE_PER_KM'],
        'max_price_per_km': current_app.config['MAX_PRICE_PER_KM'],
        'min_base_fee': current_app.config['MIN_BASE_FEE'],
        'max_base_fee': current_app.config['MAX_BASE_FEE'],
        'platform_fee_rate': current_app.config['DELIVERER_PLATFORM_FEE_RATE']
    }
    
    return render_template('deliverer/manage_routes.html', data=routes_data)


@deliverer_bp.route('/routes/add', methods=['POST'])
@login_required
@deliverer_required
def add_route():
    """Add a new delivery route"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    route_no = request.form.get('route_no', '').strip().upper()
    route_name = request.form.get('route_name', '').strip()
    from_location = request.form.get('from_location', '').strip()
    to_location = request.form.get('to_location', '').strip()
    base_fee = float(request.form.get('base_fee', current_app.config['DEFAULT_BASE_FEE']))
    price_per_km = float(request.form.get('price_per_km', current_app.config['DEFAULT_PRICE_PER_KM']))
    max_distance = float(request.form.get('max_distance_km', 50.0))
    estimated_distance = float(request.form.get('estimated_distance_km', 0))
    
    # Validation
    errors = []
    
    if not all([route_no, route_name, from_location, to_location]):
        errors.append("All route fields are required")
    
    if price_per_km < current_app.config['MIN_PRICE_PER_KM']:
        errors.append(f"Price per km must be at least R{current_app.config['MIN_PRICE_PER_KM']}")
    
    if price_per_km > current_app.config['MAX_PRICE_PER_KM']:
        errors.append(f"Price per km cannot exceed R{current_app.config['MAX_PRICE_PER_KM']}")
    
    if base_fee < current_app.config['MIN_BASE_FEE']:
        errors.append(f"Base fee must be at least R{current_app.config['MIN_BASE_FEE']}")
    
    if base_fee > current_app.config['MAX_BASE_FEE']:
        errors.append(f"Base fee cannot exceed R{current_app.config['MAX_BASE_FEE']}")
    
    if errors:
        flash('; '.join(errors), 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    try:
        conn.execute("""
            INSERT INTO delivery_routes 
            (driver_id, route_no, route_name, from_location, to_location,
             base_fee, price_per_km, max_distance_km, estimated_distance_km, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (deliverer['id'], route_no, route_name, from_location, to_location,
              base_fee, price_per_km, max_distance, estimated_distance))
        
        conn.commit()
        
        flash(f'Route {route_no} added successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Failed to add route: {str(e)}', 'error')
    
    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/routes/<int:route_id>/edit', methods=['POST'])
@login_required
@deliverer_required
def edit_route(route_id):
    """Edit an existing route"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    # Verify route belongs to deliverer
    route = conn.execute("""
        SELECT * FROM delivery_routes 
        WHERE id = ? AND driver_id = ?
    """, (route_id, deliverer['id'])).fetchone()
    
    if not route:
        flash('Route not found', 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    base_fee = float(request.form.get('base_fee', route['base_fee']))
    price_per_km = float(request.form.get('price_per_km', route['price_per_km']))
    max_distance = float(request.form.get('max_distance_km', route['max_distance_km']))
    
    # Validation
    if price_per_km < current_app.config['MIN_PRICE_PER_KM'] or price_per_km > current_app.config['MAX_PRICE_PER_KM']:
        flash(f"Price per km must be between R{current_app.config['MIN_PRICE_PER_KM']} and R{current_app.config['MAX_PRICE_PER_KM']}", 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    if base_fee < current_app.config['MIN_BASE_FEE'] or base_fee > current_app.config['MAX_BASE_FEE']:
        flash(f"Base fee must be between R{current_app.config['MIN_BASE_FEE']} and R{current_app.config['MAX_BASE_FEE']}", 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    try:
        conn.execute("""
            UPDATE delivery_routes 
            SET base_fee = ?,
                price_per_km = ?,
                max_distance_km = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (base_fee, price_per_km, max_distance, route_id))
        
        conn.commit()
        flash('Route updated successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Failed to update route: {str(e)}', 'error')
    
    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/routes/<int:route_id>/toggle', methods=['POST'])
@login_required
@deliverer_required
def toggle_route(route_id):
    """Activate/deactivate a route"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    route = conn.execute("""
        SELECT * FROM delivery_routes 
        WHERE id = ? AND driver_id = ?
    """, (route_id, deliverer['id'])).fetchone()
    
    if not route:
        return jsonify({'success': False, 'error': 'Route not found'}), 404
    
    new_status = not route['is_active']
    
    conn.execute("""
        UPDATE delivery_routes 
        SET is_active = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, route_id))
    
    conn.commit()
    
    status_text = 'activated' if new_status else 'deactivated'
    return jsonify({
        'success': True,
        'message': f'Route {status_text} successfully',
        'is_active': new_status
    })


@deliverer_bp.route('/routes/<int:route_id>/delete', methods=['POST'])
@login_required
@deliverer_required
def delete_route(route_id):
    """Delete a route"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    # Check if route has active deliveries
    active_deliveries = conn.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE driver_id = ? 
        AND status IN ('PICKED_UP', 'IN_TRANSIT')
    """, (deliverer['id'],)).fetchone()['count']
    
    if active_deliveries > 0:
        flash('Cannot delete route while you have active deliveries', 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    conn.execute('DELETE FROM delivery_routes WHERE id = ? AND driver_id = ?', (route_id, deliverer['id']))
    conn.commit()
    
    flash('Route deleted successfully', 'success')
    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/dashboard')
@login_required
@deliverer_required
def dashboard():
    """Deliverer dashboard with routes"""
    user = session.get('user')
    conn = get_db_connection()
    
    # Get deliverer info
    deliverer = conn.execute("""
        SELECT d.*, u.email
        FROM drivers d
        JOIN users u ON d.user_id = u.id
        WHERE d.user_id = ?
    """, (user['id'],)).fetchone()
    
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    deliverer_dict = dict(deliverer)
    
    # Get deliverer's routes
    routes = conn.execute("""
        SELECT * FROM delivery_routes
        WHERE driver_id = ? AND is_active = 1
        ORDER BY created_at DESC
    """, (deliverer['id'],)).fetchall()
    
    deliverer_dict['routes'] = [dict(r) for r in routes]
    deliverer_dict['route_count'] = len(deliverer_dict['routes'])
    
    # Get available pickups (orders ready for collection)
    available_pickups = conn.execute("""
        SELECT t.*, 
               s.name as seller_name, 
               s.location as seller_location,
               u.email as buyer_email,
               u.address as buyer_address
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        JOIN users u ON t.user_id = u.id
        WHERE t.status = 'READY_FOR_PICKUP' 
        AND t.driver_id IS NULL
        AND t.delivery_method = 'public_transport'
        ORDER BY t.timestamp DESC
    """).fetchall()
    
    deliverer_dict['available_pickups'] = [dict(p) for p in available_pickups]
    
    # Get active deliveries (assigned to this deliverer)
    active_deliveries = conn.execute("""
        SELECT t.*, 
               s.name as seller_name, 
               s.location as seller_location,
               u.email as buyer_email,
               u.address as buyer_address
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        JOIN users u ON t.user_id = u.id
        WHERE t.driver_id = ? 
        AND t.status IN ('PICKED_UP', 'IN_TRANSIT')
        ORDER BY t.timestamp DESC
    """, (deliverer['id'],)).fetchall()
    
    deliverer_dict['active_deliveries'] = [dict(d) for d in active_deliveries]
    
    # Get completed deliveries (last 10)
    completed_deliveries = conn.execute("""
        SELECT t.*, 
               s.name as seller_name,
               u.email as buyer_email
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        JOIN users u ON t.user_id = u.id
        WHERE t.driver_id = ? 
        AND t.status IN ('DELIVERED', 'COMPLETED')
        ORDER BY t.delivered_at DESC
        LIMIT 10
    """, (deliverer['id'],)).fetchall()
    
    deliverer_dict['completed_deliveries'] = [dict(c) for c in completed_deliveries]
    
    # Calculate today's earnings
    today_earnings = conn.execute("""
        SELECT COALESCE(SUM(driver_fee), 0) as total
        FROM transactions
        WHERE driver_id = ?
        AND DATE(delivered_at) = DATE('now')
        AND status IN ('DELIVERED', 'COMPLETED')
    """, (deliverer['id'],)).fetchone()['total']
    
    deliverer_dict['today_earnings'] = today_earnings
    
    return render_template('deliverer/dashboard.html', deliverer=deliverer_dict)


@deliverer_bp.route('/claim/<int:order_id>', methods=['POST'])
@login_required
@deliverer_required
def claim_delivery(order_id):
    """Claim a delivery for pickup"""
    user = session.get('user')
    conn = get_db_connection()
    
    # Get deliverer info
    deliverer = conn.execute(
        'SELECT id FROM drivers WHERE user_id = ? AND is_verified = 1',
        (user['id'],)
    ).fetchone()
    
    if not deliverer:
        return jsonify({'success': False, 'error': 'You must be verified to claim deliveries'}), 403
    
    # Check if order is available
    transaction = conn.execute("""
        SELECT * FROM transactions 
        WHERE id = ? AND status = 'READY_FOR_PICKUP' AND driver_id IS NULL
    """, (order_id,)).fetchone()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'Delivery not available'}), 404
    
    try:
        # Assign deliverer to order
        conn.execute("""
            UPDATE transactions 
            SET driver_id = ?, status = 'PICKED_UP', pickup_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (deliverer['id'], order_id))
        
        # Add tracking entry
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'PICKED_UP', 'Deliverer claimed and collected order', ?)
        """, (order_id, user['id']))
        
        conn.commit()
        
        # Send system message to chat
        from shared.chat_utils import send_system_message
        send_system_message(order_id, f"🚚 Deliverer has claimed your order and is on the way!")
        
        return jsonify({'success': True, 'message': 'Delivery claimed successfully!'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@deliverer_bp.route('/verify-pickup', methods=['POST'])
@login_required
@deliverer_required
def verify_pickup():
    """Verify pickup with code from seller"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    order_id = request.json.get('order_id')
    pickup_code = request.json.get('pickup_code', '').strip()
    
    # Verify code
    transaction = conn.execute("""
        SELECT * FROM transactions 
        WHERE id = ? AND pickup_code = ?
    """, (order_id, pickup_code)).fetchone()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'Invalid pickup code'}), 400
    
    try:
        # Update transaction
        conn.execute("""
            UPDATE transactions 
            SET status = 'IN_TRANSIT', pickup_verified_at = CURRENT_TIMESTAMP, driver_id = ?
            WHERE id = ?
        """, (deliverer['id'], order_id))
        
        # Mark verification code as used
        conn.execute("""
            UPDATE verification_codes 
            SET is_used = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ? AND code_type = 'PICKUP' AND code = ?
        """, (user['id'], order_id, pickup_code))
        
        # Add tracking
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'IN_TRANSIT', 'Order verified and in transit to buyer', ?)
        """, (order_id, user['id']))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Pickup verified! Order now in transit.'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@deliverer_bp.route('/verify-delivery', methods=['POST'])
@login_required
@deliverer_required
def verify_delivery():
    """Verify delivery with code from buyer"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    order_id = request.json.get('order_id')
    delivery_code = request.json.get('delivery_code', '').strip()
    
    # Verify code
    transaction = conn.execute("""
        SELECT * FROM transactions 
        WHERE id = ? AND delivery_code = ? AND driver_id = ?
    """, (order_id, delivery_code, deliverer['id'])).fetchone()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'Invalid delivery code'}), 400
    
    try:
        # Update transaction
        conn.execute("""
            UPDATE transactions 
            SET status = 'DELIVERED', delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order_id,))
        
        # Mark verification code as used
        conn.execute("""
            UPDATE verification_codes 
            SET is_used = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ? AND code_type = 'DELIVERY' AND code = ?
        """, (user['id'], order_id, delivery_code))
        
        # Add tracking
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'DELIVERED', 'Product delivered to buyer successfully', ?)
        """, (order_id, user['id']))
        
        conn.commit()
        
        # Trigger settlement (this would be in shared utils)
        from .utils import settle_delivery_transaction
        settle_delivery_transaction(order_id)
        
        # Send system message
        from shared.chat_utils import send_system_message
        send_system_message(order_id, f"✅ Order delivered successfully! Payment is being processed.")
        
        return jsonify({'success': True, 'message': 'Delivery verified! Payment processing...'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@deliverer_bp.route('/update-location', methods=['POST'])
@login_required
@deliverer_required
def update_location():
    """Update deliverer's current location (for live tracking)"""
    user = session.get('user')
    conn = get_db_connection()
    
    order_id = request.json.get('order_id')
    latitude = request.json.get('latitude')
    longitude = request.json.get('longitude')
    
    if not all([order_id, latitude, longitude]):
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    try:
        # Add tracking with location
        conn.execute("""
            INSERT INTO delivery_tracking 
            (transaction_id, status, notes, latitude, longitude, created_by)
            VALUES (?, 'IN_TRANSIT', 'Location update', ?, ?, ?)
        """, (order_id, latitude, longitude, user['id']))
        
        conn.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@deliverer_bp.route('/track/<int:order_id>')
def track_delivery(order_id):
    """Live delivery tracking page (for buyers)"""
    conn = get_db_connection()
    
    transaction = conn.execute("""
        SELECT t.*, 
               s.name as seller_name,
               s.location as seller_location,
               u.email as buyer_email,
               u.address as buyer_address,
               d.vehicle_type,
               du.email as driver_email
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        JOIN users u ON t.user_id = u.id
        LEFT JOIN drivers d ON t.driver_id = d.id
        LEFT JOIN users du ON d.user_id = du.id
        WHERE t.id = ?
    """, (order_id,)).fetchone()
    
    if not transaction:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))
    
    transaction_dict = dict(transaction)
    
    # Get tracking history with locations
    tracking = conn.execute("""
        SELECT * FROM delivery_tracking
        WHERE transaction_id = ?
        ORDER BY created_at DESC
    """, (order_id,)).fetchall()
    
    transaction_dict['tracking'] = [dict(t) for t in tracking]
    
    # Get latest location
    latest_location = next(
        (t for t in transaction_dict['tracking'] if t.get('latitude') and t.get('longitude')),
        None
    )
    transaction_dict['latest_location'] = latest_location
    
    # Calculate estimated distance (mock calculation)
    if latest_location:
        # In production, use Google Maps Distance Matrix API
        transaction_dict['estimated_distance_km'] = round(random.uniform(0.5, 5.0), 1)
        transaction_dict['estimated_time_minutes'] = round(transaction_dict['estimated_distance_km'] * 3)
    
    return render_template('deliverer/track_delivery.html', 
                         transaction=transaction_dict,
                         google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@deliverer_bp.route('/earnings')
@login_required
@deliverer_required
def earnings():
    """Deliverer earnings history page with route breakdown"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT * FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    deliverer_dict = dict(deliverer)
    
    # Get time period from query
    period = request.args.get('period', 'month')
    
    if period == 'day':
        days = 1
    elif period == 'week':
        days = 7
    else:  # month
        days = 30
    
    # Get route-based earnings breakdown
    from .utils import get_deliverer_route_earnings
    
    route_earnings = get_deliverer_route_earnings(deliverer['id'], None, days)
    deliverer_dict['route_earnings'] = route_earnings
    
    # Calculate totals
    total_deliveries = sum(r['delivery_count'] for r in route_earnings)
    total_gross = sum(r['gross_earnings'] for r in route_earnings)
    total_platform_fees = sum(r['platform_fees'] for r in route_earnings)
    total_net = sum(r['net_earnings'] for r in route_earnings)
    
    deliverer_dict['total_deliveries'] = total_deliveries
    deliverer_dict['total_gross'] = total_gross
    deliverer_dict['total_platform_fees'] = total_platform_fees
    deliverer_dict['total_net'] = total_net
    deliverer_dict['average_per_delivery'] = total_net / total_deliveries if total_deliveries > 0 else 0
    deliverer_dict['period'] = period
    deliverer_dict['platform_fee_rate'] = current_app.config['DELIVERER_PLATFORM_FEE_RATE']
    
    return render_template('deliverer/earnings.html', deliverer=deliverer_dict)


@deliverer_bp.route('/leaderboard')
def leaderboard():
    """Gamified deliverer leaderboard"""
    conn = get_db_connection()
    
    # Get time period
    period = request.args.get('period', 'month')
    
    if period == 'day':
        date_filter = "DATE(t.delivered_at) = DATE('now')"
    elif period == 'week':
        date_filter = "DATE(t.delivered_at) >= DATE('now', '-7 days')"
    else:  # month
        date_filter = "DATE(t.delivered_at) >= DATE('now', '-30 days')"
    
    # Get top deliverers by earnings
    top_earners = conn.execute(f"""
        SELECT 
            d.id,
            u.email as deliverer_name,
            d.vehicle_type,
            d.rating,
            COUNT(t.id) as delivery_count,
            SUM(t.driver_fee) as total_earned
        FROM drivers d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN transactions t ON t.driver_id = d.id 
            AND t.status IN ('DELIVERED', 'COMPLETED')
            AND {date_filter}
        WHERE d.is_verified = 1 AND d.is_active = 1
        GROUP BY d.id, u.email, d.vehicle_type, d.rating
        ORDER BY total_earned DESC
        LIMIT 20
    """).fetchall()
    
    leaderboard_data = []
    for rank, deliverer in enumerate(top_earners, 1):
        deliverer_dict = dict(deliverer)
        deliverer_dict['rank'] = rank
        deliverer_dict['badge'] = get_rank_badge(rank)
        leaderboard_data.append(deliverer_dict)
    
    return render_template('deliverer/leaderboard.html', 
                         leaderboard=leaderboard_data,
                         period=period)


def get_rank_badge(rank):
    """Get badge emoji based on rank"""
    badges = {
        1: '🥇 Gold',
        2: '🥈 Silver',
        3: '🥉 Bronze'
    }
    return badges.get(rank, '⭐ Star')


@deliverer_bp.route('/verification-status')
@login_required
@deliverer_required
def verification_status():
    """Check deliverer verification status"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute("""
        SELECT d.*, 
               vs.status as verification_status,
               vs.rejection_reason,
               vs.submitted_at,
               vs.reviewed_at
        FROM drivers d
        LEFT JOIN verification_submissions vs ON vs.user_id = d.user_id AND vs.submission_type = 'driver'
        WHERE d.user_id = ?
    """, (user['id'],)).fetchone()
    
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    return render_template('deliverer/verification_status.html', deliverer=dict(deliverer))


@deliverer_bp.route('/pricing', methods=['GET', 'POST'])
@login_required
@deliverer_required
def update_pricing():
    """Update deliverer pricing settings"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT * FROM drivers WHERE user_id = ?', (user['id'],)).fetchone()
    
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    if request.method == 'POST':
        price_per_km = float(request.form.get('price_per_km', deliverer['price_per_km']))
        base_fee = float(request.form.get('base_fee', deliverer['base_fee']))
        max_delivery_distance = float(request.form.get('max_delivery_distance', deliverer['max_delivery_distance_km']))
        service_areas = request.form.get('service_areas', deliverer['service_areas'] or '').strip()
        is_available = request.form.get('is_available') == 'on'
        
        # Validate pricing
        errors = []
        
        if price_per_km < current_app.config['MIN_PRICE_PER_KM']:
            errors.append(f"Price per km must be at least R{current_app.config['MIN_PRICE_PER_KM']}")
        
        if price_per_km > current_app.config['MAX_PRICE_PER_KM']:
            errors.append(f"Price per km cannot exceed R{current_app.config['MAX_PRICE_PER_KM']}")
        
        if base_fee < current_app.config['MIN_BASE_FEE']:
            errors.append(f"Base fee must be at least R{current_app.config['MIN_BASE_FEE']}")
        
        if base_fee > current_app.config['MAX_BASE_FEE']:
            errors.append(f"Base fee cannot exceed R{current_app.config['MAX_BASE_FEE']}")
        
        if errors:
            return render_template('deliverer/pricing.html', 
                                 deliverer=dict(deliverer), 
                                 errors=errors,
                                 platform_fee_rate=current_app.config['DELIVERER_PLATFORM_FEE_RATE'])
        
        try:
            conn.execute("""
                UPDATE drivers 
                SET price_per_km = ?,
                    base_fee = ?,
                    max_delivery_distance_km = ?,
                    service_areas = ?,
                    is_available = ?
                WHERE user_id = ?
            """, (price_per_km, base_fee, max_delivery_distance, service_areas, is_available, user['id']))
            
            conn.commit()
            
            flash('Pricing updated successfully!', 'success')
            return redirect(url_for('deliverer.dashboard'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {str(e)}', 'error')
    
    deliverer_dict = dict(deliverer)
    deliverer_dict['platform_fee_rate'] = current_app.config['DELIVERER_PLATFORM_FEE_RATE']
    deliverer_dict['min_price_per_km'] = current_app.config['MIN_PRICE_PER_KM']
    deliverer_dict['max_price_per_km'] = current_app.config['MAX_PRICE_PER_KM']
    deliverer_dict['min_base_fee'] = current_app.config['MIN_BASE_FEE']
    deliverer_dict['max_base_fee'] = current_app.config['MAX_BASE_FEE']
    
    return render_template('deliverer/pricing.html', deliverer=deliverer_dict)


@deliverer_bp.route('/api/quotes', methods=['POST'])
def get_delivery_quotes():
    """
    API endpoint to get delivery quotes from multiple routes
    Used during checkout process
    """
    data = request.get_json() if request.is_json else request.form
    from_location = data.get('from_location', '').strip()
    to_location = data.get('to_location', '').strip()
    
    if not from_location or not to_location:
        return jsonify({'success': False, 'error': 'Both pickup and delivery locations are required'}), 400
    
    from .utils import find_routes_for_delivery
    
    quotes = find_routes_for_delivery(from_location, to_location, max_results=10)
    
    if not quotes:
        return jsonify({
            'success': False,
            'error': 'No available deliverers for this route. Try different locations.'
        }), 404
    
    return jsonify({
        'success': True,
        'quotes': quotes,
        'count': len(quotes)
    })"""
SparzaFi Order Chat Utilities
Functions for managing order-based communication between buyers and deliverers
"""

from database_seed import get_db_connection
from datetime import datetime


def can_user_access_chat(user_id, transaction_id):
    """
    Check if user has permission to access chat for this order
    Returns: (has_access: bool, role: str)
    """
    conn = get_db_connection()
    
    transaction = conn.execute("""
        SELECT t.user_id as buyer_id, 
               t.seller_id,
               d.user_id as driver_user_id,
               t.status
        FROM transactions t
        LEFT JOIN drivers d ON t.driver_id = d.id
        WHERE t.id = ?
    """, (transaction_id,)).fetchone()
    
    if not transaction:
        return False, None
    
    # Check if user is buyer
    if transaction['buyer_id'] == user_id:
        return True, 'buyer'
    
    # Check if user is deliverer
    if transaction['driver_user_id'] == user_id:
        return True, 'deliverer'
    
    # Check if user is admin
    user = conn.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,)).fetchone()
    if user and user['is_admin']:
        return True, 'admin'
    
    return False, None


def get_chat_messages(transaction_id, limit=50):
    """Get all chat messages for an order"""
    conn = get_db_connection()
    
    messages = conn.execute("""
        SELECT ocm.*,
               u_from.email as from_email,
               u_to.email as to_email
        FROM order_chat_messages ocm
        JOIN users u_from ON ocm.from_user_id = u_from.id
        JOIN users u_to ON ocm.to_user_id = u_to.id
        WHERE ocm.transaction_id = ?
        ORDER BY ocm.created_at ASC
        LIMIT ?
    """, (transaction_id, limit)).fetchall()
    
    return [dict(m) for m in messages]


def send_chat_message(transaction_id, from_user_id, to_user_id, message, message_type='text', attachment_url=None):
    """Send a chat message"""
    conn = get_db_connection()
    
    # Verify sender has access
    has_access, role = can_user_access_chat(from_user_id, transaction_id)
    if not has_access:
        return {'success': False, 'error': 'You do not have access to this chat'}
    
    # Sanitize message
    message = message.strip()
    if not message and message_type == 'text':
        return {'success': False, 'error': 'Message cannot be empty'}
    
    if len(message) > 1000:
        return {'success': False, 'error': 'Message too long (max 1000 characters)'}
    
    # Check for spam (more than 10 messages in last minute)
    recent_count = conn.execute("""
        SELECT COUNT(*) as count
        FROM order_chat_messages
        WHERE from_user_id = ?
        AND transaction_id = ?
        AND created_at >= datetime('now', '-1 minute')
    """, (from_user_id, transaction_id)).fetchone()['count']
    
    if recent_count >= 10:
        return {'success': False, 'error': 'Too many messages. Please wait before sending more.'}
    
    try:
        cursor = conn.execute("""
            INSERT INTO order_chat_messages 
            (transaction_id, from_user_id, to_user_id, message, message_type, attachment_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transaction_id, from_user_id, to_user_id, message, message_type, attachment_url))
        
        message_id = cursor.lastrowid
        conn.commit()
        
        # Send notification to recipient
        send_chat_notification(to_user_id, transaction_id, message)
        
        return {
            'success': True,
            'message_id': message_id,
            'created_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def mark_messages_as_read(transaction_id, user_id):
    """Mark all messages in chat as read for user"""
    conn = get_db_connection()
    
    conn.execute("""
        UPDATE order_chat_messages
        SET is_read = 1
        WHERE transaction_id = ?
        AND to_user_id = ?
        AND is_read = 0
    """, (transaction_id, user_id))
    
    conn.commit()


def get_unread_count(user_id, transaction_id=None):
    """Get count of unread messages for user"""
    conn = get_db_connection()
    
    if transaction_id:
        # Specific order
        count = conn.execute("""
            SELECT COUNT(*) as count
            FROM order_chat_messages
            WHERE to_user_id = ?
            AND transaction_id = ?
            AND is_read = 0
        """, (user_id, transaction_id)).fetchone()['count']
    else:
        # All orders
        count = conn.execute("""
            SELECT COUNT(*) as count
            FROM order_chat_messages
            WHERE to_user_id = ?
            AND is_read = 0
        """, (user_id,)).fetchone()['count']
    
    return count


def get_user_active_chats(user_id):
    """Get all active chats for a user"""
    conn = get_db_connection()
    
    chats = conn.execute("""
        SELECT DISTINCT
            ocm.transaction_id,
            t.status,
            t.timestamp as order_date,
            CASE 
                WHEN t.user_id = ? THEN d.user_id
                ELSE t.user_id
            END as other_user_id,
            CASE 
                WHEN t.user_id = ? THEN u_driver.email
                ELSE u_buyer.email
            END as other_user_email,
            (SELECT COUNT(*) 
             FROM order_chat_messages 
             WHERE transaction_id = ocm.transaction_id 
             AND to_user_id = ? 
             AND is_read = 0) as unread_count,
            (SELECT message 
             FROM order_chat_messages 
             WHERE transaction_id = ocm.transaction_id 
             ORDER BY created_at DESC 
             LIMIT 1) as last_message,
            (SELECT created_at 
             FROM order_chat_messages 
             WHERE transaction_id = ocm.transaction_id 
             ORDER BY created_at DESC 
             LIMIT 1) as last_message_time
        FROM order_chat_messages ocm
        JOIN transactions t ON ocm.transaction_id = t.id
        LEFT JOIN drivers d ON t.driver_id = d.id
        LEFT JOIN users u_driver ON d.user_id = u_driver.id
        LEFT JOIN users u_buyer ON t.user_id = u_buyer.id
        WHERE ocm.from_user_id = ? OR ocm.to_user_id = ?
        GROUP BY ocm.transaction_id
        ORDER BY last_message_time DESC
    """, (user_id, user_id, user_id, user_id, user_id)).fetchall()
    
    return [dict(c) for c in chats]


def flag_message(message_id, reason, flagged_by_user_id):
    """Flag a message for admin review"""
    conn = get_db_connection()
    
    conn.execute("""
        UPDATE order_chat_messages
        SET is_flagged = 1,
            flagged_reason = ?
        WHERE id = ?
    """, (reason, message_id))
    
    # Create admin notification
    conn.execute("""
        INSERT INTO system_notifications (user_id, title, message, notification_type)
        SELECT id, 'Message Flagged', ?, 'moderation'
        FROM users
        WHERE is_admin = 1
    """, (f'Message #{message_id} flagged by user #{flagged_by_user_id}: {reason}',))
    
    conn.commit()


def send_system_message(transaction_id, message):
    """Send automated system message to chat"""
    conn = get_db_connection()
    
    # Get buyer and driver
    transaction = conn.execute("""
        SELECT t.user_id as buyer_id, d.user_id as driver_user_id
        FROM transactions t
        LEFT JOIN drivers d ON t.driver_id = d.id
        WHERE t.id = ?
    """, (transaction_id,)).fetchone()
    
    if not transaction:
        return False
    
    # Send to both parties
    for to_user_id in [transaction['buyer_id'], transaction['driver_user_id']]:
        if to_user_id:
            conn.execute("""
                INSERT INTO order_chat_messages 
                (transaction_id, from_user_id, to_user_id, message, message_type)
                VALUES (?, 1, ?, ?, 'system')
            """, (transaction_id, to_user_id, message))
    
    conn.commit()
    return True


def send_chat_notification(user_id, transaction_id, message_preview):
    """Send notification about new chat message"""
    # In production, this would integrate with push notifications, SMS, or email
    conn = get_db_connection()
    
    # Truncate message for notification
    preview = message_preview[:50] + '...' if len(message_preview) > 50 else message_preview
    
    conn.execute("""
        INSERT INTO system_notifications 
        (user_id, title, message, notification_type)
        VALUES (?, ?, ?, 'chat')
    """, (user_id, 'New Message', f'Order #{transaction_id}: {preview}'))
    
    conn.commit()


def delete_old_chats(days=90):
    """
    Delete chat messages older than specified days for completed orders
    Called by scheduled job
    """
    conn = get_db_connection()
    
    deleted = conn.execute("""
        DELETE FROM order_chat_messages
        WHERE transaction_id IN (
            SELECT id FROM transactions 
            WHERE status = 'COMPLETED'
            AND DATE(funds_settled_at) < DATE('now', '-' || ? || ' days')
        )
    """, (days,))
    
    conn.commit()
    return deleted.rowcount


def get_chat_statistics(transaction_id):
    """Get chat statistics for analytics"""
    conn = get_db_connection()
    
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_messages,
            SUM(CASE WHEN message_type = 'system' THEN 1 ELSE 0 END) as system_messages,
            SUM(CASE WHEN is_flagged = 1 THEN 1 ELSE 0 END) as flagged_messages,
            MIN(created_at) as first_message_time,
            MAX(created_at) as last_message_time
        FROM order_chat_messages
        WHERE transaction_id = ?
    """, (transaction_id,)).fetchone()
    
    return dict(stats) if stats else None


def search_chat_messages(transaction_id, search_query):
    """Search messages in a chat"""
    conn = get_db_connection()
    
    messages = conn.execute("""
        SELECT ocm.*,
               u_from.email as from_email
        FROM order_chat_messages ocm
        JOIN users u_from ON ocm.from_user_id = u_from.id
        WHERE ocm.transaction_id = ?
        AND ocm.message LIKE ?
        ORDER BY ocm.created_at DESC
        LIMIT 20
    """, (transaction_id, f'%{search_query}%')).fetchall()
    
    return [dict(m) for m in messages]