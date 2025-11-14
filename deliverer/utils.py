"""
SparzaFi Deliverer Utilities
Helper functions for delivery management, route pricing, and settlement
"""

from database_seed import get_db_connection
from flask import current_app
import random
import hashlib
from datetime import datetime, timedelta


# ==================== ROUTE MANAGEMENT ====================

def add_delivery_route(deliverer_id, route_no, route_name, base_fee, price_per_km, max_distance_km, service_area=None, description=None):
    """
    Add a new delivery route for a deliverer
    """
    conn = get_db_connection()

    try:
        conn.execute("""
            INSERT INTO delivery_routes
            (deliverer_id, route_no, route_name, base_fee, price_per_km, max_distance_km, service_area, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (deliverer_id, route_no, route_name, base_fee, price_per_km, max_distance_km, service_area, description))

        conn.commit()
        return {'success': True, 'message': 'Route added successfully'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def update_delivery_route(route_id, route_no=None, route_name=None, base_fee=None, price_per_km=None, max_distance_km=None, service_area=None, description=None, is_active=None):
    """
    Update an existing delivery route
    """
    conn = get_db_connection()

    updates = []
    params = []

    if route_no is not None:
        updates.append("route_no = ?")
        params.append(route_no)
    if route_name is not None:
        updates.append("route_name = ?")
        params.append(route_name)
    if base_fee is not None:
        updates.append("base_fee = ?")
        params.append(base_fee)
    if price_per_km is not None:
        updates.append("price_per_km = ?")
        params.append(price_per_km)
    if max_distance_km is not None:
        updates.append("max_distance_km = ?")
        params.append(max_distance_km)
    if service_area is not None:
        updates.append("service_area = ?")
        params.append(service_area)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if not updates:
        return {'success': False, 'error': 'No updates provided'}

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(route_id)

    try:
        conn.execute(f"""
            UPDATE delivery_routes
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()
        return {'success': True, 'message': 'Route updated successfully'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def get_deliverer_routes(deliverer_id, include_inactive=False):
    """
    Get all routes for a specific deliverer
    """
    conn = get_db_connection()

    query = """
        SELECT * FROM delivery_routes
        WHERE deliverer_id = ?
    """

    if not include_inactive:
        query += " AND is_active = 1"

    query += " ORDER BY created_at DESC"

    routes = conn.execute(query, (deliverer_id,)).fetchall()
    return [dict(r) for r in routes]


def delete_delivery_route(route_id, deliverer_id):
    """
    Delete a delivery route (soft delete by setting is_active = 0)
    """
    conn = get_db_connection()

    try:
        conn.execute("""
            UPDATE delivery_routes
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deliverer_id = ?
        """, (route_id, deliverer_id))

        conn.commit()
        return {'success': True, 'message': 'Route deactivated successfully'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


# ==================== ROUTE PRICING & QUOTES ====================

def get_route_quote(route_id, distance_km):
    """
    Calculate delivery fee using route-specific pricing
    Returns breakdown of fees including platform commission
    """
    conn = get_db_connection()

    route = conn.execute("""
        SELECT dr.*, d.vehicle_type, d.rating, u.email as deliverer_name, d.id as deliverer_id
        FROM delivery_routes dr
        JOIN deliverers d ON dr.deliverer_id = d.id
        JOIN users u ON d.user_id = u.id
        WHERE dr.id = ? AND dr.is_active = 1
    """, (route_id,)).fetchone()

    if not route:
        return None

    # Check if distance exceeds max
    if distance_km > route['max_distance_km']:
        return {
            'error': f"Distance exceeds maximum delivery range of {route['max_distance_km']} km"
        }

    # Calculate gross delivery fee
    distance_fee = distance_km * route['price_per_km']
    gross_fee = route['base_fee'] + distance_fee

    # Platform takes 15% from deliverer's earnings
    platform_fee = gross_fee * 0.15
    deliverer_earnings = gross_fee - platform_fee

    return {
        'route_id': route_id,
        'deliverer_id': route['deliverer_id'],
        'route_no': route['route_no'],
        'route_name': route['route_name'],
        'distance_km': distance_km,
        'price_per_km': route['price_per_km'],
        'base_fee': route['base_fee'],
        'distance_fee': round(distance_fee, 2),
        'gross_delivery_fee': round(gross_fee, 2),
        'platform_fee': round(platform_fee, 2),
        'deliverer_earnings': round(deliverer_earnings, 2),
        'buyer_pays': round(gross_fee, 2),
        'deliverer_name': route['deliverer_name'],
        'vehicle_type': route['vehicle_type'],
        'rating': route['rating'],
        'estimated_time': estimate_delivery_time(distance_km, route['vehicle_type'])
    }


def find_routes_for_area(search_term, distance_km=None, max_results=10):
    """
    Find delivery routes that service a specific area
    Returns list of routes with quotes
    """
    conn = get_db_connection()

    # Search for routes by route number, name, or service area
    routes = conn.execute("""
        SELECT dr.*, d.vehicle_type, d.rating, d.total_deliveries, u.email as deliverer_name
        FROM delivery_routes dr
        JOIN deliverers d ON dr.deliverer_id = d.id
        JOIN users u ON d.user_id = u.id
        WHERE dr.is_active = 1
        AND dr.is_verified = 1
        AND d.is_verified = 1
        AND d.is_available = 1
        AND (
            LOWER(dr.route_no) LIKE LOWER(?)
            OR LOWER(dr.route_name) LIKE LOWER(?)
            OR LOWER(dr.service_area) LIKE LOWER(?)
        )
        ORDER BY d.rating DESC, dr.price_per_km ASC
        LIMIT ?
    """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', max_results)).fetchall()

    quotes = []
    for route in routes:
        # Use provided distance or estimate
        dist = distance_km if distance_km else 10.0

        quote = get_route_quote(route['id'], dist)
        if quote and 'error' not in quote:
            quote['total_deliveries'] = route['total_deliveries']
            quotes.append(quote)

    # Sort by total cost (cheapest first)
    quotes.sort(key=lambda x: x['buyer_pays'])

    return quotes


def get_all_active_routes():
    """Get all active verified routes for marketplace display"""
    conn = get_db_connection()

    routes = conn.execute("""
        SELECT dr.*,
               d.vehicle_type,
               d.rating,
               d.total_deliveries,
               u.email as deliverer_name
        FROM delivery_routes dr
        JOIN deliverers d ON dr.deliverer_id = d.id
        JOIN users u ON d.user_id = u.id
        WHERE dr.is_active = 1
        AND dr.is_verified = 1
        AND d.is_verified = 1
        ORDER BY d.rating DESC, dr.price_per_km ASC
    """).fetchall()

    return [dict(r) for r in routes]


# ==================== EARNINGS & ANALYTICS ====================

def get_deliverer_route_earnings(deliverer_id, route_id=None, days=30):
    """
    Get earnings breakdown by route for a deliverer
    """
    conn = get_db_connection()

    if route_id:
        # Specific route earnings
        query = """
            SELECT
                dr.route_no,
                dr.route_name,
                COUNT(t.id) as delivery_count,
                COALESCE(SUM(t.deliverer_fee), 0) as gross_earnings,
                COALESCE(SUM(t.platform_commission * 0.15), 0) as platform_fees,
                COALESCE(SUM(t.deliverer_fee) - SUM(t.platform_commission * 0.15), 0) as net_earnings
            FROM delivery_routes dr
            LEFT JOIN transactions t ON t.deliverer_id = ?
                AND t.status IN ('DELIVERED', 'COMPLETED')
                AND DATE(t.delivered_at) >= DATE('now', '-' || ? || ' days')
            WHERE dr.id = ?
            GROUP BY dr.id, dr.route_no, dr.route_name
        """
        result = conn.execute(query, (deliverer_id, days, route_id)).fetchone()
        return dict(result) if result else None
    else:
        # All routes for deliverer
        query = """
            SELECT
                dr.id,
                dr.route_no,
                dr.route_name,
                dr.base_fee,
                dr.price_per_km,
                COUNT(t.id) as delivery_count,
                COALESCE(SUM(t.deliverer_fee), 0) as gross_earnings,
                COALESCE(SUM(t.platform_commission * 0.15), 0) as platform_fees,
                COALESCE(SUM(t.deliverer_fee) - SUM(t.platform_commission * 0.15), 0) as net_earnings
            FROM delivery_routes dr
            LEFT JOIN transactions t ON t.deliverer_id = dr.deliverer_id
                AND t.status IN ('DELIVERED', 'COMPLETED')
                AND DATE(t.delivered_at) >= DATE('now', '-' || ? || ' days')
            WHERE dr.deliverer_id = ?
            GROUP BY dr.id, dr.route_no, dr.route_name, dr.base_fee, dr.price_per_km
            ORDER BY delivery_count DESC
        """
        results = conn.execute(query, (days, deliverer_id)).fetchall()
        return [dict(r) for r in results]


# ==================== SETTLEMENT & TRANSACTIONS ====================

def settle_delivery_transaction(transaction_id):
    """
    Settle funds after delivery confirmation
    Distributes payment to seller, deliverer, and platform
    """
    conn = get_db_connection()
    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?',
        (transaction_id,)
    ).fetchone()

    if not transaction or transaction['status'] != 'DELIVERED':
        return {'success': False, 'error': 'Transaction not eligible for settlement'}

    try:
        total = transaction['total_amount']
        deliverer_fee = transaction['deliverer_fee']
        commission = total * current_app.config['COMMISSION_RATE']
        seller_amount = total - deliverer_fee - commission

        # Update transaction with settlement details
        conn.execute("""
            UPDATE transactions
            SET status = 'COMPLETED',
                seller_amount = ?,
                platform_commission = ?,
                funds_settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (seller_amount, commission, transaction_id))

        # Update seller balance
        if transaction['seller_id']:
            conn.execute("""
                UPDATE sellers
                SET balance = balance + ?,
                    total_sales = total_sales + 1
                WHERE id = ?
            """, (seller_amount, transaction['seller_id']))

        # Update deliverer balance and stats
        if transaction['deliverer_id']:
            conn.execute("""
                UPDATE deliverers
                SET balance = balance + ?,
                    total_deliveries = total_deliveries + 1,
                    successful_deliveries = successful_deliveries + 1
                WHERE id = ?
            """, (deliverer_fee, transaction['deliverer_id']))

        # Create settlement records
        conn.execute("""
            INSERT INTO payment_settlements
            (transaction_id, recipient_id, recipient_type, amount, status, settled_at)
            VALUES (?, ?, 'SELLER', ?, 'COMPLETED', CURRENT_TIMESTAMP)
        """, (transaction_id, transaction['seller_id'], seller_amount))

        if transaction['deliverer_id']:
            # Get deliverer user_id
            deliverer = conn.execute(
                'SELECT user_id FROM deliverers WHERE id = ?',
                (transaction['deliverer_id'],)
            ).fetchone()

            if deliverer:
                conn.execute("""
                    INSERT INTO payment_settlements
                    (transaction_id, recipient_id, recipient_type, amount, status, settled_at)
                    VALUES (?, ?, 'DELIVERER', ?, 'COMPLETED', CURRENT_TIMESTAMP)
                """, (transaction_id, deliverer['user_id'], deliverer_fee))

        # Add completion tracking
        conn.execute("""
            INSERT INTO delivery_tracking
            (transaction_id, status, notes, created_by)
            VALUES (?, 'COMPLETED', 'Transaction completed, funds settled successfully', ?)
        """, (transaction_id, transaction['user_id']))

        conn.commit()

        return {
            'success': True,
            'seller_amount': seller_amount,
            'deliverer_fee': deliverer_fee,
            'commission': commission
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


# ==================== UTILITY FUNCTIONS ====================

def calculate_delivery_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    distance = R * c
    return round(distance, 2)


def estimate_delivery_time(distance_km, vehicle_type):
    """
    Estimate delivery time based on distance and vehicle type
    Returns estimated time in minutes
    """
    # Average speeds in km/h
    speeds = {
        'Walking': 5,
        'Bicycle': 15,
        'Motorcycle': 40,
        'Minibus Taxi': 35
    }

    speed = speeds.get(vehicle_type, 30)
    time_hours = distance_km / speed
    time_minutes = int(time_hours * 60)

    # Add buffer time for traffic and pickups
    buffer = 10

    return time_minutes + buffer


def get_deliverer_performance_stats(deliverer_id, days=30):
    """
    Get performance statistics for a deliverer
    """
    conn = get_db_connection()

    stats = conn.execute("""
        SELECT
            COUNT(*) as total_deliveries,
            SUM(deliverer_fee) as total_earnings,
            AVG(deliverer_fee) as avg_earnings_per_delivery,
            AVG(
                CAST((julianday(delivered_at) - julianday(pickup_verified_at)) * 24 * 60 AS INTEGER)
            ) as avg_delivery_time_minutes
        FROM transactions
        WHERE deliverer_id = ?
        AND status IN ('DELIVERED', 'COMPLETED')
        AND DATE(delivered_at) >= DATE('now', '-' || ? || ' days')
    """, (deliverer_id, days)).fetchone()

    if stats:
        stats_dict = dict(stats)

        # Calculate performance rating
        if stats_dict['total_deliveries'] and stats_dict['total_deliveries'] > 0:
            # Rating based on deliveries, speed, and earnings
            base_rating = 3.0
            delivery_bonus = min(stats_dict['total_deliveries'] / 10, 1.5)
            speed_bonus = 0.5 if stats_dict['avg_delivery_time_minutes'] and stats_dict['avg_delivery_time_minutes'] < 30 else 0

            performance_rating = min(base_rating + delivery_bonus + speed_bonus, 5.0)
            stats_dict['performance_rating'] = round(performance_rating, 1)
        else:
            stats_dict['performance_rating'] = 0

        return stats_dict

    return {
        'total_deliveries': 0,
        'total_earnings': 0,
        'avg_earnings_per_delivery': 0,
        'avg_delivery_time_minutes': 0,
        'performance_rating': 0
    }


def get_nearby_deliverers(latitude, longitude, radius_km=10):
    """
    Find deliverers within a certain radius
    (In production, this would use spatial database queries)
    """
    conn = get_db_connection()

    # For now, return all active verified deliverers
    # In production, filter by last known location
    deliverers = conn.execute("""
        SELECT d.*, u.email
        FROM deliverers d
        JOIN users u ON d.user_id = u.id
        WHERE d.is_verified = 1
        AND d.is_active = 1
        ORDER BY d.rating DESC
        LIMIT 10
    """).fetchall()

    return [dict(d) for d in deliverers]


def assign_best_deliverer(transaction_id):
    """
    Auto-assign the best available deliverer to an order
    Based on rating, proximity, and current workload
    """
    conn = get_db_connection()

    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?',
        (transaction_id,)
    ).fetchone()

    if not transaction:
        return {'success': False, 'error': 'Transaction not found'}

    # Get available deliverers (not currently on a delivery)
    available_deliverers = conn.execute("""
        SELECT d.*,
            (SELECT COUNT(*) FROM transactions
             WHERE deliverer_id = d.id
             AND status IN ('PICKED_UP', 'IN_TRANSIT')) as active_deliveries
        FROM deliverers d
        WHERE d.is_verified = 1
        AND d.is_active = 1
        HAVING active_deliveries = 0
        ORDER BY d.rating DESC, d.total_deliveries DESC
        LIMIT 1
    """).fetchone()

    if not available_deliverers:
        return {'success': False, 'error': 'No available deliverers'}

    deliverer_id = available_deliverers['id']

    try:
        conn.execute("""
            UPDATE transactions
            SET deliverer_id = ?,
                status = 'PICKED_UP',
                pickup_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (deliverer_id, transaction_id))

        conn.execute("""
            INSERT INTO delivery_tracking
            (transaction_id, status, notes, created_by)
            VALUES (?, 'PICKED_UP', 'Auto-assigned to deliverer', NULL)
        """, (transaction_id,))

        conn.commit()

        return {
            'success': True,
            'deliverer_id': deliverer_id
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def notify_deliverer(deliverer_id, message, notification_type='delivery'):
    """
    Send notification to deliverer
    (In production, this would use push notifications or SMS)
    """
    conn = get_db_connection()

    deliverer = conn.execute(
        'SELECT user_id FROM deliverers WHERE id = ?',
        (deliverer_id,)
    ).fetchone()

    if not deliverer:
        return False

    try:
        # Insert notification
        conn.execute("""
            INSERT INTO notifications
            (user_id, title, message, notification_type)
            VALUES (?, 'New Delivery', ?, ?)
        """, (deliverer['user_id'], message, notification_type))

        conn.commit()
        return True
    except:
        return False


# ==================== VERIFICATION CODE SYSTEM ====================

def generate_verification_code(code_type='PICKUP'):
    """
    Generate a 6-digit verification code with prefix
    code_type: 'PICKUP' or 'DELIVERY'
    Returns: dict with 'code' (raw) and 'display_code' (with prefix)
    """
    # Generate 6-digit code
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # Add prefix based on type
    prefix = 'PU-' if code_type == 'PICKUP' else 'DL-'
    display_code = f"{prefix}{code}"

    return {
        'code': code,
        'display_code': display_code,
        'code_type': code_type
    }


def hash_code(code):
    """
    Hash verification code using SHA256 for secure storage
    """
    return hashlib.sha256(code.encode()).hexdigest()


def create_pickup_code(transaction_id, created_by):
    """
    Seller generates a pickup code when order is ready
    Stores hashed code in database with 24-hour expiration
    """
    conn = get_db_connection()

    # Check if code already exists for this transaction
    existing = conn.execute("""
        SELECT id FROM verification_codes
        WHERE transaction_id = ? AND code_type = 'PICKUP' AND is_used = 0
    """, (transaction_id,)).fetchone()

    if existing:
        return {'success': False, 'error': 'Pickup code already exists'}

    # Generate new code
    code_data = generate_verification_code('PICKUP')
    code_hash = hash_code(code_data['code'])

    # Calculate expiration (24 hours from now)
    expires_at = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Store hashed code
        conn.execute("""
            INSERT INTO verification_codes
            (transaction_id, code_type, code_hash, expires_at, created_by, max_attempts)
            VALUES (?, 'PICKUP', ?, ?, ?, 3)
        """, (transaction_id, code_hash, expires_at, created_by))

        # Update transaction with pickup code (plain text for quick lookup)
        conn.execute("""
            UPDATE transactions
            SET pickup_code = ?, status = 'READY_FOR_PICKUP'
            WHERE id = ?
        """, (code_data['code'], transaction_id))

        # Send notification to seller
        transaction = conn.execute('SELECT seller_id FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
        if transaction and transaction['seller_id']:
            seller = conn.execute('SELECT user_id FROM sellers WHERE id = ?', (transaction['seller_id'],)).fetchone()
            if seller:
                conn.execute("""
                    INSERT INTO notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Pickup Code Generated', ?, 'pickup_code')
                """, (seller['user_id'], f"Your pickup code is: {code_data['display_code']}. Give this to the driver."))

        conn.commit()

        return {
            'success': True,
            'display_code': code_data['display_code'],
            'expires_at': expires_at
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def create_delivery_code(transaction_id, created_by):
    """
    Buyer generates a delivery code once they're ready to receive
    Stores hashed code in database with 24-hour expiration
    """
    conn = get_db_connection()

    # Check if code already exists
    existing = conn.execute("""
        SELECT id FROM verification_codes
        WHERE transaction_id = ? AND code_type = 'DELIVERY' AND is_used = 0
    """, (transaction_id,)).fetchone()

    if existing:
        return {'success': False, 'error': 'Delivery code already exists'}

    # Generate new code
    code_data = generate_verification_code('DELIVERY')
    code_hash = hash_code(code_data['code'])

    # Calculate expiration (24 hours from now)
    expires_at = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Store hashed code
        conn.execute("""
            INSERT INTO verification_codes
            (transaction_id, code_type, code_hash, expires_at, created_by, max_attempts)
            VALUES (?, 'DELIVERY', ?, ?, ?, 3)
        """, (transaction_id, code_hash, expires_at, created_by))

        # Update transaction with delivery code (plain text for quick lookup)
        conn.execute("""
            UPDATE transactions
            SET delivery_code = ?
            WHERE id = ?
        """, (code_data['code'], transaction_id))

        # Send notification to buyer
        transaction = conn.execute('SELECT user_id FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
        if transaction:
            conn.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, 'Delivery Code Generated', ?, 'delivery_code')
            """, (transaction['user_id'], f"Your delivery code is: {code_data['display_code']}. Give this to the driver when you receive your order."))

        conn.commit()

        return {
            'success': True,
            'display_code': code_data['display_code'],
            'expires_at': expires_at
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def verify_pickup_code(transaction_id, input_code, verified_by):
    """
    Driver verifies pickup code from seller
    Handles attempt limits and expiration
    """
    conn = get_db_connection()

    # Strip prefix if present
    clean_code = input_code.replace('PU-', '').replace('DL-', '').strip()
    code_hash = hash_code(clean_code)

    # Get verification code record
    code_record = conn.execute("""
        SELECT * FROM verification_codes
        WHERE transaction_id = ? AND code_type = 'PICKUP' AND is_used = 0
    """, (transaction_id,)).fetchone()

    if not code_record:
        return {'success': False, 'error': 'Invalid or already used pickup code'}

    # Check expiration
    if datetime.now() > datetime.strptime(code_record['expires_at'], '%Y-%m-%d %H:%M:%S'):
        return {'success': False, 'error': 'Pickup code has expired'}

    # Check attempts
    if code_record['attempts'] >= code_record['max_attempts']:
        return {'success': False, 'error': 'Maximum verification attempts exceeded'}

    # Verify code
    if code_hash != code_record['code_hash']:
        # Increment attempts
        conn.execute("""
            UPDATE verification_codes
            SET attempts = attempts + 1
            WHERE id = ?
        """, (code_record['id'],))
        conn.commit()

        remaining = code_record['max_attempts'] - (code_record['attempts'] + 1)
        return {
            'success': False,
            'error': f'Invalid pickup code. {remaining} attempt(s) remaining'
        }

    # Code is valid - mark as used and update transaction
    try:
        conn.execute("""
            UPDATE verification_codes
            SET is_used = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (verified_by, code_record['id']))

        conn.execute("""
            UPDATE transactions
            SET status = 'PICKED_UP', pickup_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (transaction_id,))

        # Add tracking
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'PICKED_UP', 'Pickup verified with code', ?)
        """, (transaction_id, verified_by))

        # Notify seller
        transaction = conn.execute('SELECT seller_id FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
        if transaction and transaction['seller_id']:
            seller = conn.execute('SELECT user_id FROM sellers WHERE id = ?', (transaction['seller_id'],)).fetchone()
            if seller:
                conn.execute("""
                    INSERT INTO notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Order Picked Up', ?, 'pickup_verified')
                """, (seller['user_id'], f"Order #{transaction_id} has been picked up by the driver."))

        conn.commit()

        return {
            'success': True,
            'message': 'Pickup verified successfully! Order now in transit.'
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def verify_delivery_code(transaction_id, input_code, verified_by):
    """
    Driver verifies delivery code from buyer
    Handles attempt limits, expiration, and triggers settlement
    """
    conn = get_db_connection()

    # Strip prefix if present
    clean_code = input_code.replace('PU-', '').replace('DL-', '').strip()
    code_hash = hash_code(clean_code)

    # Get verification code record
    code_record = conn.execute("""
        SELECT * FROM verification_codes
        WHERE transaction_id = ? AND code_type = 'DELIVERY' AND is_used = 0
    """, (transaction_id,)).fetchone()

    if not code_record:
        return {'success': False, 'error': 'Invalid or already used delivery code'}

    # Check expiration
    if datetime.now() > datetime.strptime(code_record['expires_at'], '%Y-%m-%d %H:%M:%S'):
        return {'success': False, 'error': 'Delivery code has expired'}

    # Check attempts
    if code_record['attempts'] >= code_record['max_attempts']:
        return {'success': False, 'error': 'Maximum verification attempts exceeded'}

    # Verify code
    if code_hash != code_record['code_hash']:
        # Increment attempts
        conn.execute("""
            UPDATE verification_codes
            SET attempts = attempts + 1
            WHERE id = ?
        """, (code_record['id'],))
        conn.commit()

        remaining = code_record['max_attempts'] - (code_record['attempts'] + 1)
        return {
            'success': False,
            'error': f'Invalid delivery code. {remaining} attempt(s) remaining'
        }

    # Code is valid - mark as used and complete delivery
    try:
        conn.execute("""
            UPDATE verification_codes
            SET is_used = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (verified_by, code_record['id']))

        conn.execute("""
            UPDATE transactions
            SET status = 'DELIVERED', delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (transaction_id,))

        # Add tracking
        conn.execute("""
            INSERT INTO delivery_tracking (transaction_id, status, notes, created_by)
            VALUES (?, 'DELIVERED', 'Delivery verified with code', ?)
        """, (transaction_id, verified_by))

        # Notify buyer
        transaction = conn.execute('SELECT user_id FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
        if transaction:
            conn.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, 'Delivery Confirmed', ?, 'delivery_verified')
            """, (transaction['user_id'], f"Order #{transaction_id} has been delivered successfully!"))

        conn.commit()

        # Trigger settlement
        settlement_result = settle_delivery_transaction(transaction_id)

        return {
            'success': True,
            'message': 'Delivery verified successfully! Funds are being processed.',
            'settlement': settlement_result
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}


def expire_old_verification_codes():
    """
    Cleanup job to expire old verification codes
    Should be run periodically (e.g., daily via cron job)
    """
    conn = get_db_connection()

    try:
        result = conn.execute("""
            UPDATE verification_codes
            SET is_used = 1
            WHERE expires_at < CURRENT_TIMESTAMP
            AND is_used = 0
        """)

        expired_count = result.rowcount
        conn.commit()

        return {
            'success': True,
            'expired_count': expired_count
        }

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
