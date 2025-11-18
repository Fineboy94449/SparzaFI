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
        if not user or user.get('user_type') not in ['driver', 'deliverer', 'admin']:
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
        'SELECT id FROM deliverers WHERE user_id = ?',
        (user['id'],)
    ).fetchone()
    
    if existing:
        flash('You are already registered as a deliverer!', 'info')
        return redirect(url_for('deliverer.dashboard'))
    
    if request.method == 'POST':
        license_number = request.form.get('license_number', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'walking')
        vehicle_registration = request.form.get('vehicle_registration', '').strip()

        try:
            conn.execute("""
                INSERT INTO deliverers
                (user_id, license_number, vehicle_type, vehicle_registration,
                 is_verified, is_active, is_available)
                VALUES (?, ?, ?, ?, 0, 1, 1)
            """, (user['id'], license_number, vehicle_type, vehicle_registration))
            
            # Update user type
            conn.execute("""
                UPDATE users
                SET user_type = 'deliverer', updated_at = CURRENT_TIMESTAMP
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
@deliverer_bp.route('/manage-routes', methods=['GET'])
@login_required
@deliverer_required
def manage_routes():
    """Manage delivery routes"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT * FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    # Get all routes for this deliverer
    routes = conn.execute("""
        SELECT * FROM delivery_routes
        WHERE deliverer_id = ?
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

    return render_template('manage_routes.html', data=routes_data)


@deliverer_bp.route('/routes/add', methods=['POST'])
@login_required
@deliverer_required
def add_route():
    """Add a new delivery route"""
    user = session.get('user')
    conn = get_db_connection()
    
    deliverer = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    route_no = request.form.get('route_no', '').strip().upper()
    route_name = request.form.get('route_name', '').strip()
    service_area = request.form.get('service_area', '').strip()
    description = request.form.get('description', '').strip()
    base_fee = float(request.form.get('base_fee', current_app.config['DEFAULT_BASE_FEE']))
    price_per_km = float(request.form.get('price_per_km', current_app.config['DEFAULT_PRICE_PER_KM']))
    max_distance = float(request.form.get('max_distance_km', 50.0))

    # Validation
    errors = []

    if not all([route_no, route_name, service_area]):
        errors.append("Route number, name, and service area are required")
    
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
            (deliverer_id, route_no, route_name, service_area, description,
             base_fee, price_per_km, max_distance_km, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (deliverer['id'], route_no, route_name, service_area, description,
              base_fee, price_per_km, max_distance))

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
    
    deliverer = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    # Verify route belongs to deliverer
    route = conn.execute("""
        SELECT * FROM delivery_routes
        WHERE id = ? AND deliverer_id = ?
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
    
    deliverer = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    route = conn.execute("""
        SELECT * FROM delivery_routes
        WHERE id = ? AND deliverer_id = ?
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
    
    deliverer = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404
    
    # Check if route has active deliveries
    active_deliveries = conn.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('PICKED_UP', 'IN_TRANSIT')
    """, (deliverer['id'],)).fetchone()['count']
    
    if active_deliveries > 0:
        flash('Cannot delete route while you have active deliveries', 'error')
        return redirect(url_for('deliverer.manage_routes'))
    
    conn.execute('DELETE FROM delivery_routes WHERE id = ? AND deliverer_id = ?', (route_id, deliverer['id']))
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
        FROM deliverers d
        JOIN users u ON d.user_id = u.id
        WHERE d.user_id = ?
    """, (user['id'],)).fetchone()
    
    if not deliverer:
        return redirect(url_for('deliverer.setup'))
    
    deliverer_dict = dict(deliverer)
    
    # Get deliverer's routes
    routes = conn.execute("""
        SELECT * FROM delivery_routes
        WHERE deliverer_id = ? AND is_active = 1
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
        AND t.deliverer_id IS NULL
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
        WHERE t.deliverer_id = ?
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
        WHERE t.deliverer_id = ?
        AND t.status IN ('DELIVERED', 'COMPLETED')
        ORDER BY t.delivered_at DESC
        LIMIT 10
    """, (deliverer['id'],)).fetchall()
    
    deliverer_dict['completed_deliveries'] = [dict(c) for c in completed_deliveries]
    
    # Calculate today's earnings
    today_earnings = conn.execute("""
        SELECT COALESCE(SUM(deliverer_fee), 0) as total
        FROM transactions
        WHERE deliverer_id = ?
        AND DATE(delivered_at) = DATE('now')
        AND status IN ('DELIVERED', 'COMPLETED')
    """, (deliverer['id'],)).fetchone()['total']

    deliverer_dict['today_earnings'] = today_earnings

    # Calculate total earnings (all time)
    total_earnings = conn.execute("""
        SELECT COALESCE(SUM(deliverer_fee), 0) as total
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('DELIVERED', 'COMPLETED')
    """, (deliverer['id'],)).fetchone()['total']

    deliverer_dict['total_earnings'] = total_earnings

    # Calculate pending settlements (picked up but not delivered)
    pending_settlements = conn.execute("""
        SELECT COALESCE(SUM(deliverer_fee), 0) as total
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('PICKED_UP', 'IN_TRANSIT')
    """, (deliverer['id'],)).fetchone()['total']

    deliverer_dict['pending_settlements'] = pending_settlements

    # Get deliverer name (from email or create a display name)
    deliverer_dict['name'] = deliverer_dict.get('email', 'Deliverer').split('@')[0].title()

    # === PERFORMANCE METRICS ===

    # Total deliveries count (all time)
    total_deliveries_count = conn.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('DELIVERED', 'COMPLETED')
    """, (deliverer['id'],)).fetchone()['count']

    deliverer_dict['total_deliveries'] = total_deliveries_count

    # On-time delivery rate (assuming deliveries within expected time are on-time)
    # For now, we'll use 95% as a placeholder - in production this would be calculated from actual delivery times
    on_time_count = int(total_deliveries_count * 0.95) if total_deliveries_count > 0 else 0
    on_time_rate = (on_time_count / total_deliveries_count * 100) if total_deliveries_count > 0 else 100.0
    deliverer_dict['on_time_rate'] = round(on_time_rate, 1)

    # Acceptance rate - calculate from claimed vs available deliveries
    # Get total offers made to this deliverer (simplified - using all available pickups as proxy)
    total_offers = total_deliveries_count + len(deliverer_dict['available_pickups'])
    acceptance_rate = (total_deliveries_count / total_offers * 100) if total_offers > 0 else 100.0
    deliverer_dict['acceptance_rate'] = round(acceptance_rate, 1)

    # Cancellation rate - percentage of cancelled deliveries
    cancelled_count = conn.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE deliverer_id = ?
        AND status = 'CANCELLED'
    """, (deliverer['id'],)).fetchone()['count']

    total_assigned = total_deliveries_count + cancelled_count
    cancellation_rate = (cancelled_count / total_assigned * 100) if total_assigned > 0 else 0.0
    deliverer_dict['cancellation_rate'] = round(cancellation_rate, 1)

    # Performance Score (composite metric out of 100)
    # Formula: (on_time_rate * 0.5) + (acceptance_rate * 0.3) + ((100 - cancellation_rate) * 0.2)
    performance_score = (
        (on_time_rate * 0.5) +
        (acceptance_rate * 0.3) +
        ((100 - cancellation_rate) * 0.2)
    )
    deliverer_dict['performance_score'] = round(performance_score, 1)

    # Calculate streak (consecutive days with at least 1 delivery)
    # For simplicity, we'll set a default - in production this would be calculated from delivery history
    deliverer_dict['delivery_streak'] = min(total_deliveries_count, 7)  # Cap at 7 for demo

    return render_template('deliverer_dashboard.html', deliverer=deliverer_dict)


@deliverer_bp.route('/claim/<int:order_id>', methods=['POST'])
@login_required
@deliverer_required
def claim_delivery(order_id):
    """Claim a delivery for pickup"""
    user = session.get('user')
    conn = get_db_connection()
    
    # Get deliverer info
    deliverer = conn.execute(
        'SELECT id FROM deliverers WHERE user_id = ? AND is_verified = 1',
        (user['id'],)
    ).fetchone()
    
    if not deliverer:
        return jsonify({'success': False, 'error': 'You must be verified to claim deliveries'}), 403
    
    # Check if order is available
    transaction = conn.execute("""
        SELECT * FROM transactions
        WHERE id = ? AND status = 'READY_FOR_PICKUP' AND deliverer_id IS NULL
    """, (order_id,)).fetchone()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'Delivery not available'}), 404
    
    try:
        # Assign deliverer to order
        conn.execute("""
            UPDATE transactions
            SET deliverer_id = ?, status = 'PICKED_UP', pickup_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (deliverer['id'], order_id))
        
        # Add tracking entry
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'PICKED_UP', 'Deliverer claimed and collected order', ?)
        """, (order_id, user['id']))
        
        conn.commit()
        
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

    order_id = request.json.get('order_id')
    pickup_code = request.json.get('pickup_code', '').strip()

    if not order_id or not pickup_code:
        return jsonify({'success': False, 'error': 'Order ID and pickup code are required'}), 400

    # Use the secure verification utility
    from .utils import verify_pickup_code

    result = verify_pickup_code(order_id, pickup_code, user['id'])

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@deliverer_bp.route('/verify-delivery', methods=['POST'])
@login_required
@deliverer_required
def verify_delivery():
    """Verify delivery with code from buyer"""
    user = session.get('user')

    order_id = request.json.get('order_id')
    delivery_code = request.json.get('delivery_code', '').strip()

    if not order_id or not delivery_code:
        return jsonify({'success': False, 'error': 'Order ID and delivery code are required'}), 400

    # Use the secure verification utility
    from .utils import verify_delivery_code

    result = verify_delivery_code(order_id, delivery_code, user['id'])

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


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
        LEFT JOIN deliverers d ON t.deliverer_id = d.id
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
    
    deliverer = conn.execute('SELECT * FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
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
            SUM(t.deliverer_fee) as total_earned
        FROM deliverers d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN transactions t ON t.deliverer_id = d.id 
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
        FROM deliverers d
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
    
    deliverer = conn.execute('SELECT * FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    
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
                UPDATE deliverers
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
    })


@deliverer_bp.route('/api/check-new-deliveries', methods=['GET'])
@login_required
@deliverer_required
def check_new_deliveries():
    """
    API endpoint to check for new deliveries (for push notifications)
    Returns count of new deliveries since last check
    """
    user = session.get('user')
    conn = get_db_connection()

    # Get last check time from session (or default to 1 minute ago)
    last_check = session.get('last_delivery_check', (datetime.now() - timedelta(minutes=1)).isoformat())

    # Count new deliveries since last check
    new_deliveries_count = conn.execute("""
        SELECT COUNT(*) as count
        FROM transactions
        WHERE status = 'READY_FOR_PICKUP'
        AND deliverer_id IS NULL
        AND delivery_method = 'public_transport'
        AND timestamp > ?
    """, (last_check,)).fetchone()['count']

    # Update last check time
    session['last_delivery_check'] = datetime.now().isoformat()

    # Get details of new deliveries
    new_deliveries = conn.execute("""
        SELECT t.id, t.total_amount, s.name as seller_name
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        WHERE t.status = 'READY_FOR_PICKUP'
        AND t.deliverer_id IS NULL
        AND t.delivery_method = 'public_transport'
        AND t.timestamp > ?
        ORDER BY t.timestamp DESC
        LIMIT 5
    """, (last_check,)).fetchall()

    return jsonify({
        'success': True,
        'new_deliveries': new_deliveries_count,
        'deliveries': [dict(d) for d in new_deliveries]
    })


@deliverer_bp.route('/api/earnings-data', methods=['GET'])
@login_required
@deliverer_required
def get_earnings_data():
    """
    API endpoint to get detailed earnings data for charts
    Returns daily earnings for the past week
    """
    user = session.get('user')
    conn = get_db_connection()

    deliverer = conn.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Get daily earnings for the past 7 days
    earnings_data = conn.execute("""
        SELECT
            DATE(delivered_at) as date,
            COUNT(*) as deliveries,
            COALESCE(SUM(deliverer_fee), 0) as earnings
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('DELIVERED', 'COMPLETED')
        AND DATE(delivered_at) >= DATE('now', '-7 days')
        GROUP BY DATE(delivered_at)
        ORDER BY DATE(delivered_at) ASC
    """, (deliverer['id'],)).fetchall()

    return jsonify({
        'success': True,
        'earnings': [dict(e) for e in earnings_data]
    })


@deliverer_bp.route('/api/toggle-availability', methods=['POST'])
@login_required
@deliverer_required
def toggle_availability():
    """
    API endpoint to toggle deliverer availability status
    """
    user = session.get('user')
    conn = get_db_connection()

    deliverer = conn.execute('SELECT * FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Get the desired availability state from request
    data = request.get_json() or {}
    is_available = data.get('is_available', not deliverer['is_available'])

    try:
        # Update availability status
        conn.execute("""
            UPDATE deliverers
            SET is_available = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if is_available else 0, deliverer['id']))

        conn.commit()

        return jsonify({
            'success': True,
            'is_available': bool(is_available),
            'message': f"You are now {'active' if is_available else 'inactive'}"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update availability: {str(e)}'
        }), 500

# ==================== ENHANCED DRIVER DELIVERY CODE MANAGEMENT ====================

@deliverer_bp.route('/delivery-codes')
@login_required
def view_delivery_codes():
    """View all buyer delivery codes for assigned orders"""
    user = session.get('user')
    db = get_db()
    
    # Get deliverer ID
    deliverer = db.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        flash('Please complete your deliverer profile setup.', 'warning')
        return redirect(url_for('deliverer.setup_profile'))
    
    deliverer_id = deliverer['id']
    
    # Get orders with buyer delivery codes
    orders = db.execute("""
        SELECT t.*, u.email as buyer_email,
               s.name as seller_name,
               t.delivery_code, t.pickup_code
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        JOIN sellers s ON t.seller_id = s.id
        WHERE t.deliverer_id = ? AND t.delivery_code IS NOT NULL
        AND t.status IN ('IN_TRANSIT', 'PICKED_UP')
        ORDER BY t.updated_at DESC
    """, (deliverer_id,)).fetchall()
    
    return render_template('deliverer/delivery_codes.html', orders=[dict(o) for o in orders])

@deliverer_bp.route('/returns/pickup')
@login_required
def return_pickups():
    """View return pickup requests"""
    user = session.get('user')
    db = get_db()
    
    # Get deliverer ID
    deliverer = db.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return redirect(url_for('deliverer.setup_profile'))
    
    deliverer_id = deliverer['id']
    
    # Get approved returns that need pickup
    returns = db.execute("""
        SELECT r.*, t.id as transaction_id, t.delivery_address,
               s.name as seller_name, s.location as seller_location,
               u.email as buyer_email
        FROM return_requests r
        JOIN transactions t ON r.transaction_id = t.id
        JOIN sellers s ON r.seller_id = s.id
        JOIN users u ON r.user_id = u.id
        WHERE r.status IN ('APPROVED', 'PICKUP_SCHEDULED')
        AND t.deliverer_id = ?
        ORDER BY r.created_at DESC
    """, (deliverer_id,)).fetchall()
    
    return render_template('deliverer/return_pickups.html', returns=[dict(r) for r in returns])

@deliverer_bp.route('/return/<int:return_id>/pickup', methods=['POST'])
@login_required
def confirm_return_pickup(return_id):
    """Confirm return item has been picked up"""
    user = session.get('user')
    db = get_db()
    
    # Get deliverer ID
    deliverer = db.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer profile not found'}), 404
    
    # Verify ownership
    return_req = db.execute("""
        SELECT r.*, t.deliverer_id
        FROM return_requests r
        JOIN transactions t ON r.transaction_id = t.id
        WHERE r.id = ? AND t.deliverer_id = ?
    """, (return_id, deliverer['id'])).fetchone()
    
    if not return_req:
        return jsonify({'success': False, 'error': 'Return not found'}), 404
    
    # Update return status
    db.execute("""
        UPDATE return_requests
        SET status = 'PICKED_UP', picked_up_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (return_id,))
    
    # Notify seller and buyer
    from user.buyer_dashboard import send_notification
    send_notification(
        return_req['user_id'],
        'Return Picked Up',
        'Driver has picked up your return item',
        'order',
        return_req['transaction_id']
    )
    
    send_notification(
        return_req['seller_id'],
        'Return In Transit',
        'Driver is returning the item to you',
        'order',
        return_req['transaction_id']
    )
    
    db.commit()
    return jsonify({'success': True, 'message': 'Return pickup confirmed'})

@deliverer_bp.route('/order/<int:order_id>/verify-code', methods=['POST'])
@login_required
def verify_delivery_code_api(order_id):
    """Verify buyer's delivery code"""
    user = session.get('user')
    db = get_db()
    
    data = request.get_json()
    entered_code = data.get('code')
    
    # Get deliverer ID
    deliverer = db.execute('SELECT id FROM deliverers WHERE user_id = ?', (user['id'],)).fetchone()
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer profile not found'}), 404
    
    # Get order
    order = db.execute("""
        SELECT * FROM transactions
        WHERE id = ? AND deliverer_id = ?
    """, (order_id, deliverer['id'])).fetchone()
    
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    # Verify code
    if order['delivery_code'] == entered_code:
        # Update order status to delivered
        db.execute("""
            UPDATE transactions
            SET status = 'DELIVERED', delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order_id,))
        
        # Notify buyer
        from user.buyer_dashboard import send_notification
        send_notification(
            order['user_id'],
            'Order Delivered',
            'Your order has been successfully delivered!',
            'delivery',
            order_id
        )
        
        db.commit()
        return jsonify({'success': True, 'message': 'Delivery confirmed!'})
    else:
        return jsonify({'success': False, 'error': 'Invalid delivery code'}), 400
