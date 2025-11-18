"""
SparzaFi Deliverer Routes - Migrated to Firebase
Dashboard, delivery management, live tracking, earnings, and leaderboard
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, current_app
from . import deliverer_bp
from shared.utils import login_required, generate_verification_code
from datetime import datetime, timedelta
import random

# Firebase imports
from firebase_db import (
    deliverer_service,
    delivery_route_service,
    get_user_service,
    transaction_service,
    delivery_tracking_service,
    seller_service,
    get_notification_service
)
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


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
    user_service = get_user_service()

    # Check if already a deliverer
    existing = deliverer_service.get_by_user_id(user['id'])

    if existing:
        flash('You are already registered as a deliverer!', 'info')
        return redirect(url_for('deliverer.dashboard'))

    if request.method == 'POST':
        license_number = request.form.get('license_number', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'walking')
        vehicle_registration = request.form.get('vehicle_registration', '').strip()

        try:
            # Create deliverer profile
            deliverer_service.create({
                'user_id': user['id'],
                'license_number': license_number,
                'vehicle_type': vehicle_type,
                'vehicle_registration': vehicle_registration,
                'is_verified': False,
                'is_active': True,
                'is_available': True,
                'rating': 0.0,
                'total_deliveries': 0
            })

            # Update user type
            user_service.update(user['id'], {'user_type': 'deliverer'})

            # Update session
            updated_user = user_service.get(user['id'])
            session['user'] = updated_user

            flash('Deliverer profile created! Now add your delivery routes.', 'success')
            return redirect(url_for('deliverer.manage_routes'))

        except Exception as e:
            flash(f'Setup failed: {str(e)}', 'error')
            return render_template('deliverer/setup.html', error=f"Setup failed: {str(e)}")

    return render_template('deliverer/setup.html')


@deliverer_bp.route('/routes', methods=['GET'])
@deliverer_bp.route('/manage-routes', methods=['GET'])
@login_required
@deliverer_required
def manage_routes():
    """Manage delivery routes"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return redirect(url_for('deliverer.setup'))

    # Get all routes for this deliverer
    routes = delivery_route_service.get_deliverer_routes(deliverer['id'])

    routes_data = {
        'deliverer': deliverer,
        'routes': routes,
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

    deliverer = deliverer_service.get_by_user_id(user['id'])
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
        delivery_route_service.create({
            'deliverer_id': deliverer['id'],
            'route_no': route_no,
            'route_name': route_name,
            'service_area': service_area,
            'description': description,
            'base_fee': base_fee,
            'price_per_km': price_per_km,
            'max_distance_km': max_distance,
            'is_active': True
        })

        flash(f'Route {route_no} added successfully!', 'success')

    except Exception as e:
        flash(f'Failed to add route: {str(e)}', 'error')

    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/routes/<route_id>/edit', methods=['POST'])
@login_required
@deliverer_required
def edit_route(route_id):
    """Edit an existing route"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Verify route belongs to deliverer
    route = delivery_route_service.get(route_id)

    if not route or route['deliverer_id'] != deliverer['id']:
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
        delivery_route_service.update(route_id, {
            'base_fee': base_fee,
            'price_per_km': price_per_km,
            'max_distance_km': max_distance
        })

        flash('Route updated successfully!', 'success')

    except Exception as e:
        flash(f'Failed to update route: {str(e)}', 'error')

    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/routes/<route_id>/toggle', methods=['POST'])
@login_required
@deliverer_required
def toggle_route(route_id):
    """Activate/deactivate a route"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    route = delivery_route_service.get(route_id)

    if not route or route['deliverer_id'] != deliverer['id']:
        return jsonify({'success': False, 'error': 'Route not found'}), 404

    new_status = not route.get('is_active', True)

    delivery_route_service.update(route_id, {
        'is_active': new_status
    })

    status_text = 'activated' if new_status else 'deactivated'
    return jsonify({
        'success': True,
        'message': f'Route {status_text} successfully',
        'is_active': new_status
    })


@deliverer_bp.route('/routes/<route_id>/delete', methods=['POST'])
@login_required
@deliverer_required
def delete_route(route_id):
    """Delete a route"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Check if route has active deliveries
    # Get all transactions for this deliverer with active status
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    active_deliveries = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['PICKED_UP', 'IN_TRANSIT'])
    ).stream()

    active_count = sum(1 for _ in active_deliveries)

    if active_count > 0:
        flash('Cannot delete route while you have active deliveries', 'error')
        return redirect(url_for('deliverer.manage_routes'))

    delivery_route_service.delete(route_id)

    flash('Route deleted successfully', 'success')
    return redirect(url_for('deliverer.manage_routes'))


@deliverer_bp.route('/dashboard')
@login_required
@deliverer_required
def dashboard():
    """Deliverer dashboard with routes"""
    user = session.get('user')
    user_service = get_user_service()

    # Get deliverer info
    deliverer = deliverer_service.get_by_user_id(user['id'])

    if not deliverer:
        return redirect(url_for('deliverer.setup'))

    # Get user email
    user_data = user_service.get(user['id'])
    deliverer['email'] = user_data.get('email', '')

    # Get deliverer's routes
    routes = delivery_route_service.get_active_routes(deliverer['id'])
    deliverer['routes'] = routes
    deliverer['route_count'] = len(routes)

    # Get available pickups (orders ready for collection)
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    available_pickups_query = db.collection('transactions').where(
        filter=FieldFilter('status', '==', 'READY_FOR_PICKUP')
    ).where(
        filter=FieldFilter('delivery_method', '==', 'public_transport')
    ).stream()

    available_pickups = []
    for doc in available_pickups_query:
        trans_data = {**doc.to_dict(), 'id': doc.id}
        # Skip if already has deliverer
        if trans_data.get('deliverer_id'):
            continue

        # Get seller and buyer info
        if trans_data.get('seller_id'):
            seller = seller_service.get(trans_data['seller_id'])
            trans_data['seller_name'] = seller.get('name', '') if seller else ''
            trans_data['seller_location'] = seller.get('location', '') if seller else ''

        if trans_data.get('user_id'):
            buyer = user_service.get(trans_data['user_id'])
            trans_data['buyer_email'] = buyer.get('email', '') if buyer else ''
            trans_data['buyer_address'] = buyer.get('address', '') if buyer else ''

        available_pickups.append(trans_data)

    deliverer['available_pickups'] = sorted(available_pickups, key=lambda x: x.get('created_at', ''), reverse=True)

    # Get active deliveries (assigned to this deliverer)
    active_deliveries_query = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['PICKED_UP', 'IN_TRANSIT'])
    ).stream()

    active_deliveries = []
    for doc in active_deliveries_query:
        trans_data = {**doc.to_dict(), 'id': doc.id}

        # Get seller and buyer info
        if trans_data.get('seller_id'):
            seller = seller_service.get(trans_data['seller_id'])
            trans_data['seller_name'] = seller.get('name', '') if seller else ''
            trans_data['seller_location'] = seller.get('location', '') if seller else ''

        if trans_data.get('user_id'):
            buyer = user_service.get(trans_data['user_id'])
            trans_data['buyer_email'] = buyer.get('email', '') if buyer else ''
            trans_data['buyer_address'] = buyer.get('address', '') if buyer else ''

        active_deliveries.append(trans_data)

    deliverer['active_deliveries'] = sorted(active_deliveries, key=lambda x: x.get('created_at', ''), reverse=True)

    # Get completed deliveries (last 10)
    completed_deliveries_query = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['DELIVERED', 'COMPLETED'])
    ).limit(10).stream()

    completed_deliveries = []
    for doc in completed_deliveries_query:
        trans_data = {**doc.to_dict(), 'id': doc.id}

        # Get seller and buyer info
        if trans_data.get('seller_id'):
            seller = seller_service.get(trans_data['seller_id'])
            trans_data['seller_name'] = seller.get('name', '') if seller else ''

        if trans_data.get('user_id'):
            buyer = user_service.get(trans_data['user_id'])
            trans_data['buyer_email'] = buyer.get('email', '') if buyer else ''

        completed_deliveries.append(trans_data)

    deliverer['completed_deliveries'] = sorted(completed_deliveries, key=lambda x: x.get('delivered_at', ''), reverse=True)

    # Calculate today's earnings
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_earnings = 0.0

    for trans in completed_deliveries:
        delivered_at = trans.get('delivered_at')
        if delivered_at and isinstance(delivered_at, str):
            try:
                delivered_date = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
                if delivered_date >= today_start:
                    today_earnings += float(trans.get('deliverer_fee', 0))
            except:
                pass

    deliverer['today_earnings'] = today_earnings

    # Calculate total earnings (all time)
    all_completed = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['DELIVERED', 'COMPLETED'])
    ).stream()

    total_earnings = sum(float(doc.to_dict().get('deliverer_fee', 0)) for doc in all_completed)
    deliverer['total_earnings'] = total_earnings

    # Calculate pending settlements (picked up but not delivered)
    pending_settlements = sum(float(trans.get('deliverer_fee', 0)) for trans in active_deliveries)
    deliverer['pending_settlements'] = pending_settlements

    # Get deliverer name
    deliverer['name'] = deliverer.get('email', 'Deliverer').split('@')[0].title()

    # === PERFORMANCE METRICS ===

    # Recount all completed deliveries for metrics
    all_completed = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['DELIVERED', 'COMPLETED'])
    ).stream()

    total_deliveries_count = sum(1 for _ in all_completed)
    deliverer['total_deliveries'] = total_deliveries_count

    # On-time delivery rate (95% placeholder)
    on_time_count = int(total_deliveries_count * 0.95) if total_deliveries_count > 0 else 0
    on_time_rate = (on_time_count / total_deliveries_count * 100) if total_deliveries_count > 0 else 100.0
    deliverer['on_time_rate'] = round(on_time_rate, 1)

    # Acceptance rate
    total_offers = total_deliveries_count + len(deliverer['available_pickups'])
    acceptance_rate = (total_deliveries_count / total_offers * 100) if total_offers > 0 else 100.0
    deliverer['acceptance_rate'] = round(acceptance_rate, 1)

    # Cancellation rate
    cancelled_query = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', '==', 'CANCELLED')
    ).stream()

    cancelled_count = sum(1 for _ in cancelled_query)
    total_assigned = total_deliveries_count + cancelled_count
    cancellation_rate = (cancelled_count / total_assigned * 100) if total_assigned > 0 else 0.0
    deliverer['cancellation_rate'] = round(cancellation_rate, 1)

    # Performance Score
    performance_score = (
        (on_time_rate * 0.5) +
        (acceptance_rate * 0.3) +
        ((100 - cancellation_rate) * 0.2)
    )
    deliverer['performance_score'] = round(performance_score, 1)

    # Delivery streak
    deliverer['delivery_streak'] = min(total_deliveries_count, 7)

    return render_template('deliverer_dashboard.html', deliverer=deliverer)


@deliverer_bp.route('/claim/<order_id>', methods=['POST'])
@login_required
@deliverer_required
def claim_delivery(order_id):
    """Claim a delivery for pickup"""
    user = session.get('user')

    # Get deliverer info
    deliverer = deliverer_service.get_by_user_id(user['id'])

    if not deliverer or not deliverer.get('is_verified'):
        return jsonify({'success': False, 'error': 'You must be verified to claim deliveries'}), 403

    # Check if order is available
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        return jsonify({'success': False, 'error': 'Delivery not available'}), 404

    transaction = transaction_doc.to_dict()

    if transaction.get('status') != 'READY_FOR_PICKUP' or transaction.get('deliverer_id'):
        return jsonify({'success': False, 'error': 'Delivery not available'}), 404

    try:
        # Assign deliverer to order
        db.collection('transactions').document(order_id).update({
            'deliverer_id': deliverer['id'],
            'status': 'PICKED_UP',
            'pickup_verified_at': firestore.SERVER_TIMESTAMP
        })

        # Add tracking entry
        delivery_tracking_service.create({
            'transaction_id': order_id,
            'status': 'PICKED_UP',
            'notes': 'Deliverer claimed and collected order',
            'created_by': user['id']
        })

        return jsonify({'success': True, 'message': 'Delivery claimed successfully!'})

    except Exception as e:
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

    order_id = request.json.get('order_id')
    latitude = request.json.get('latitude')
    longitude = request.json.get('longitude')

    if not all([order_id, latitude, longitude]):
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    try:
        # Add tracking with location
        delivery_tracking_service.create({
            'transaction_id': order_id,
            'status': 'IN_TRANSIT',
            'notes': 'Location update',
            'latitude': latitude,
            'longitude': longitude,
            'created_by': user['id']
        })

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@deliverer_bp.route('/track/<order_id>')
def track_delivery(order_id):
    """Live delivery tracking page (for buyers)"""
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    transaction_doc = db.collection('transactions').document(order_id).get()

    if not transaction_doc.exists:
        flash('Order not found', 'error')
        return redirect(url_for('marketplace.feed'))

    transaction = {**transaction_doc.to_dict(), 'id': transaction_doc.id}

    # Get seller info
    if transaction.get('seller_id'):
        seller = seller_service.get(transaction['seller_id'])
        transaction['seller_name'] = seller.get('name', '') if seller else ''
        transaction['seller_location'] = seller.get('location', '') if seller else ''

    # Get buyer info
    if transaction.get('user_id'):
        user_service = get_user_service()
        buyer = user_service.get(transaction['user_id'])
        transaction['buyer_email'] = buyer.get('email', '') if buyer else ''
        transaction['buyer_address'] = buyer.get('address', '') if buyer else ''

    # Get deliverer info
    if transaction.get('deliverer_id'):
        deliverer = deliverer_service.get(transaction['deliverer_id'])
        if deliverer:
            transaction['vehicle_type'] = deliverer.get('vehicle_type', '')
            # Get deliverer user email
            if deliverer.get('user_id'):
                deliverer_user = get_user_service().get(deliverer['user_id'])
                transaction['driver_email'] = deliverer_user.get('email', '') if deliverer_user else ''

    # Get tracking history with locations
    tracking = delivery_tracking_service.get_transaction_tracking(order_id)
    transaction['tracking'] = tracking

    # Get latest location
    latest_location = next(
        (t for t in tracking if t.get('latitude') and t.get('longitude')),
        None
    )
    transaction['latest_location'] = latest_location

    # Calculate estimated distance (mock calculation)
    if latest_location:
        transaction['estimated_distance_km'] = round(random.uniform(0.5, 5.0), 1)
        transaction['estimated_time_minutes'] = round(transaction['estimated_distance_km'] * 3)

    return render_template('deliverer/track_delivery.html',
                         transaction=transaction,
                         google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@deliverer_bp.route('/earnings')
@login_required
@deliverer_required
def earnings():
    """Deliverer earnings history page with route breakdown"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return redirect(url_for('deliverer.setup'))

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
    deliverer['route_earnings'] = route_earnings

    # Calculate totals
    total_deliveries = sum(r['delivery_count'] for r in route_earnings)
    total_gross = sum(r['gross_earnings'] for r in route_earnings)
    total_platform_fees = sum(r['platform_fees'] for r in route_earnings)
    total_net = sum(r['net_earnings'] for r in route_earnings)

    deliverer['total_deliveries'] = total_deliveries
    deliverer['total_gross'] = total_gross
    deliverer['total_platform_fees'] = total_platform_fees
    deliverer['total_net'] = total_net
    deliverer['average_per_delivery'] = total_net / total_deliveries if total_deliveries > 0 else 0
    deliverer['period'] = period
    deliverer['platform_fee_rate'] = current_app.config['DELIVERER_PLATFORM_FEE_RATE']

    return render_template('deliverer/earnings.html', deliverer=deliverer)


@deliverer_bp.route('/leaderboard')
def leaderboard():
    """Gamified deliverer leaderboard"""
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    # Get time period
    period = request.args.get('period', 'month')

    if period == 'day':
        days = 1
    elif period == 'week':
        days = 7
    else:  # month
        days = 30

    cutoff_date = datetime.now() - timedelta(days=days)

    # Get all verified deliverers
    all_deliverers = deliverer_service.get_all_deliverers(is_active=True)

    leaderboard_data = []

    for deliverer in all_deliverers:
        if not deliverer.get('is_verified'):
            continue

        # Get user email
        deliverer_user = get_user_service().get(deliverer['user_id'])
        deliverer_name = deliverer_user.get('email', '').split('@')[0] if deliverer_user else 'Unknown'

        # Count deliveries and earnings in period
        transactions = db.collection('transactions').where(
            filter=FieldFilter('deliverer_id', '==', deliverer['id'])
        ).where(
            filter=FieldFilter('status', 'in', ['DELIVERED', 'COMPLETED'])
        ).stream()

        delivery_count = 0
        total_earned = 0.0

        for doc in transactions:
            trans = doc.to_dict()
            delivered_at = trans.get('delivered_at')

            # Filter by date
            if delivered_at and isinstance(delivered_at, str):
                try:
                    delivered_date = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
                    if delivered_date >= cutoff_date:
                        delivery_count += 1
                        total_earned += float(trans.get('deliverer_fee', 0))
                except:
                    pass

        if delivery_count > 0 or total_earned > 0:
            leaderboard_data.append({
                'id': deliverer['id'],
                'deliverer_name': deliverer_name,
                'vehicle_type': deliverer.get('vehicle_type', ''),
                'rating': deliverer.get('rating', 0.0),
                'delivery_count': delivery_count,
                'total_earned': total_earned
            })

    # Sort by total earned
    leaderboard_data.sort(key=lambda x: x['total_earned'], reverse=True)

    # Add rank and badge
    for rank, deliverer in enumerate(leaderboard_data[:20], 1):
        deliverer['rank'] = rank
        deliverer['badge'] = get_rank_badge(rank)

    return render_template('deliverer/leaderboard.html',
                         leaderboard=leaderboard_data[:20],
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

    deliverer = deliverer_service.get_by_user_id(user['id'])

    if not deliverer:
        return redirect(url_for('deliverer.setup'))

    # Get verification submission if exists
    from firebase_db import verification_submission_service
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    vs_query = db.collection('verification_submissions').where(
        filter=FieldFilter('user_id', '==', user['id'])
    ).where(
        filter=FieldFilter('submission_type', '==', 'driver')
    ).limit(1).stream()

    verification_data = None
    for doc in vs_query:
        verification_data = {**doc.to_dict(), 'id': doc.id}
        break

    deliverer['verification_status'] = verification_data.get('status') if verification_data else None
    deliverer['rejection_reason'] = verification_data.get('rejection_reason') if verification_data else None
    deliverer['submitted_at'] = verification_data.get('submitted_at') if verification_data else None
    deliverer['reviewed_at'] = verification_data.get('reviewed_at') if verification_data else None

    return render_template('deliverer/verification_status.html', deliverer=deliverer)


@deliverer_bp.route('/pricing', methods=['GET', 'POST'])
@login_required
@deliverer_required
def update_pricing():
    """Update deliverer pricing settings"""
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])

    if not deliverer:
        return redirect(url_for('deliverer.setup'))

    if request.method == 'POST':
        price_per_km = float(request.form.get('price_per_km', deliverer.get('price_per_km', 8.0)))
        base_fee = float(request.form.get('base_fee', deliverer.get('base_fee', 15.0)))
        max_delivery_distance = float(request.form.get('max_delivery_distance', deliverer.get('max_delivery_distance_km', 50.0)))
        service_areas = request.form.get('service_areas', deliverer.get('service_areas', '')).strip()
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
            deliverer['platform_fee_rate'] = current_app.config['DELIVERER_PLATFORM_FEE_RATE']
            return render_template('deliverer/pricing.html',
                                 deliverer=deliverer,
                                 errors=errors,
                                 platform_fee_rate=current_app.config['DELIVERER_PLATFORM_FEE_RATE'])

        try:
            deliverer_service.update(deliverer['id'], {
                'price_per_km': price_per_km,
                'base_fee': base_fee,
                'max_delivery_distance_km': max_delivery_distance,
                'service_areas': service_areas,
                'is_available': is_available
            })

            flash('Pricing updated successfully!', 'success')
            return redirect(url_for('deliverer.dashboard'))

        except Exception as e:
            flash(f'Update failed: {str(e)}', 'error')

    deliverer['platform_fee_rate'] = current_app.config['DELIVERER_PLATFORM_FEE_RATE']
    deliverer['min_price_per_km'] = current_app.config['MIN_PRICE_PER_KM']
    deliverer['max_price_per_km'] = current_app.config['MAX_PRICE_PER_KM']
    deliverer['min_base_fee'] = current_app.config['MIN_BASE_FEE']
    deliverer['max_base_fee'] = current_app.config['MAX_BASE_FEE']

    return render_template('deliverer/pricing.html', deliverer=deliverer)


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
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    # Get last check time from session (or default to 1 minute ago)
    last_check = session.get('last_delivery_check', (datetime.now() - timedelta(minutes=1)).isoformat())

    # Count new deliveries since last check
    new_deliveries_query = db.collection('transactions').where(
        filter=FieldFilter('status', '==', 'READY_FOR_PICKUP')
    ).where(
        filter=FieldFilter('delivery_method', '==', 'public_transport')
    ).stream()

    new_deliveries_list = []
    for doc in new_deliveries_query:
        trans = {**doc.to_dict(), 'id': doc.id}
        # Skip if has deliverer or before last check
        if trans.get('deliverer_id'):
            continue

        timestamp = trans.get('timestamp', '')
        if timestamp and isinstance(timestamp, str):
            try:
                trans_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                last_check_time = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                if trans_time > last_check_time:
                    # Get seller name
                    seller = seller_service.get(trans.get('seller_id', ''))
                    new_deliveries_list.append({
                        'id': trans['id'],
                        'total_amount': trans.get('total_amount', 0),
                        'seller_name': seller.get('name', '') if seller else ''
                    })
            except:
                pass

    # Update last check time
    session['last_delivery_check'] = datetime.now().isoformat()

    return jsonify({
        'success': True,
        'new_deliveries': len(new_deliveries_list),
        'deliveries': new_deliveries_list[:5]
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

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Get daily earnings for the past 7 days
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    cutoff_date = datetime.now() - timedelta(days=7)

    transactions = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['DELIVERED', 'COMPLETED'])
    ).stream()

    # Group by date
    daily_earnings = {}

    for doc in transactions:
        trans = doc.to_dict()
        delivered_at = trans.get('delivered_at')

        if delivered_at and isinstance(delivered_at, str):
            try:
                delivered_date = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
                if delivered_date >= cutoff_date:
                    date_str = delivered_date.strftime('%Y-%m-%d')
                    if date_str not in daily_earnings:
                        daily_earnings[date_str] = {'deliveries': 0, 'earnings': 0.0}

                    daily_earnings[date_str]['deliveries'] += 1
                    daily_earnings[date_str]['earnings'] += float(trans.get('deliverer_fee', 0))
            except:
                pass

    # Convert to list
    earnings_list = [
        {
            'date': date,
            'deliveries': data['deliveries'],
            'earnings': data['earnings']
        }
        for date, data in sorted(daily_earnings.items())
    ]

    return jsonify({
        'success': True,
        'earnings': earnings_list
    })


@deliverer_bp.route('/api/toggle-availability', methods=['POST'])
@login_required
@deliverer_required
def toggle_availability():
    """
    API endpoint to toggle deliverer availability status
    """
    user = session.get('user')

    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer not found'}), 404

    # Get the desired availability state from request
    data = request.get_json() or {}
    is_available = data.get('is_available', not deliverer.get('is_available', True))

    try:
        # Update availability status
        deliverer_service.update(deliverer['id'], {
            'is_available': is_available
        })

        return jsonify({
            'success': True,
            'is_available': bool(is_available),
            'message': f"You are now {'active' if is_available else 'inactive'}"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update availability: {str(e)}'
        }), 500


# ==================== DELIVERY CODE MANAGEMENT ====================

@deliverer_bp.route('/delivery-codes')
@login_required
def view_delivery_codes():
    """View all buyer delivery codes for assigned orders"""
    user = session.get('user')
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    # Get deliverer ID
    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        flash('Please complete your deliverer profile setup.', 'warning')
        return redirect(url_for('deliverer.setup'))

    # Get orders with buyer delivery codes
    orders_query = db.collection('transactions').where(
        filter=FieldFilter('deliverer_id', '==', deliverer['id'])
    ).where(
        filter=FieldFilter('status', 'in', ['IN_TRANSIT', 'PICKED_UP'])
    ).stream()

    orders = []
    for doc in orders_query:
        trans = {**doc.to_dict(), 'id': doc.id}

        # Get buyer and seller info
        if trans.get('user_id'):
            buyer = get_user_service().get(trans['user_id'])
            trans['buyer_email'] = buyer.get('email', '') if buyer else ''

        if trans.get('seller_id'):
            seller = seller_service.get(trans['seller_id'])
            trans['seller_name'] = seller.get('name', '') if seller else ''

        orders.append(trans)

    # Sort by updated_at
    orders.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

    return render_template('deliverer/delivery_codes.html', orders=orders)


@deliverer_bp.route('/returns/pickup')
@login_required
def return_pickups():
    """View return pickup requests"""
    user = session.get('user')
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    # Get deliverer ID
    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return redirect(url_for('deliverer.setup'))

    # Get approved returns that need pickup
    returns_query = db.collection('return_requests').where(
        filter=FieldFilter('status', 'in', ['APPROVED', 'PICKUP_SCHEDULED'])
    ).stream()

    returns = []
    for doc in returns_query:
        return_req = {**doc.to_dict(), 'id': doc.id}

        # Get transaction to check if assigned to this deliverer
        trans_id = return_req.get('transaction_id')
        if trans_id:
            trans_doc = db.collection('transactions').document(trans_id).get()
            if trans_doc.exists:
                trans = trans_doc.to_dict()
                if trans.get('deliverer_id') == deliverer['id']:
                    return_req['transaction_id'] = trans_id
                    return_req['delivery_address'] = trans.get('delivery_address', '')

                    # Get seller and buyer info
                    if return_req.get('seller_id'):
                        seller = seller_service.get(return_req['seller_id'])
                        return_req['seller_name'] = seller.get('name', '') if seller else ''
                        return_req['seller_location'] = seller.get('location', '') if seller else ''

                    if return_req.get('user_id'):
                        buyer = get_user_service().get(return_req['user_id'])
                        return_req['buyer_email'] = buyer.get('email', '') if buyer else ''

                    returns.append(return_req)

    # Sort by created_at
    returns.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return render_template('deliverer/return_pickups.html', returns=returns)


@deliverer_bp.route('/return/<return_id>/pickup', methods=['POST'])
@login_required
def confirm_return_pickup(return_id):
    """Confirm return item has been picked up"""
    user = session.get('user')
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    # Get deliverer ID
    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer profile not found'}), 404

    # Get return request
    return_doc = db.collection('return_requests').document(return_id).get()
    if not return_doc.exists:
        return jsonify({'success': False, 'error': 'Return not found'}), 404

    return_req = {**return_doc.to_dict(), 'id': return_doc.id}

    # Verify ownership via transaction
    trans_id = return_req.get('transaction_id')
    if trans_id:
        trans_doc = db.collection('transactions').document(trans_id).get()
        if not trans_doc.exists or trans_doc.to_dict().get('deliverer_id') != deliverer['id']:
            return jsonify({'success': False, 'error': 'Return not found'}), 404

    # Update return status
    db.collection('return_requests').document(return_id).update({
        'status': 'PICKED_UP',
        'picked_up_at': firestore.SERVER_TIMESTAMP
    })

    # Notify seller and buyer
    notification_service = get_notification_service()

    notification_service.create_notification(
        user_id=return_req['user_id'],
        title='Return Picked Up',
        message='Driver has picked up your return item',
        notification_type='order',
        data={'transaction_id': trans_id}
    )

    notification_service.create_notification(
        user_id=return_req.get('seller_id', ''),
        title='Return In Transit',
        message='Driver is returning the item to you',
        notification_type='order',
        data={'transaction_id': trans_id}
    )

    return jsonify({'success': True, 'message': 'Return pickup confirmed'})


@deliverer_bp.route('/order/<order_id>/verify-code', methods=['POST'])
@login_required
def verify_delivery_code_api(order_id):
    """Verify buyer's delivery code"""
    user = session.get('user')
    from firebase_config import get_firestore_db
    db = get_firestore_db()

    data = request.get_json()
    entered_code = data.get('code')

    # Get deliverer ID
    deliverer = deliverer_service.get_by_user_id(user['id'])
    if not deliverer:
        return jsonify({'success': False, 'error': 'Deliverer profile not found'}), 404

    # Get order
    order_doc = db.collection('transactions').document(order_id).get()

    if not order_doc.exists:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    order = {**order_doc.to_dict(), 'id': order_doc.id}

    if order.get('deliverer_id') != deliverer['id']:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    # Verify code
    if order.get('delivery_code') == entered_code:
        # Update order status to delivered
        db.collection('transactions').document(order_id).update({
            'status': 'DELIVERED',
            'delivered_at': firestore.SERVER_TIMESTAMP
        })

        # Notify buyer
        notification_service = get_notification_service()
        notification_service.create_notification(
            user_id=order['user_id'],
            title='Order Delivered',
            message='Your order has been successfully delivered!',
            notification_type='delivery',
            data={'order_id': order_id}
        )

        return jsonify({'success': True, 'message': 'Delivery confirmed!'})
    else:
        return jsonify({'success': False, 'error': 'Invalid delivery code'}), 400
