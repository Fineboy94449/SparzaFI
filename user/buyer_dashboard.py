"""
Buyer Dashboard Module
Comprehensive buyer features including order tracking, returns, ratings, and more
"""

from flask import render_template, redirect, url_for, session, request, jsonify, send_file
from shared.utils import login_required
from database_seed import get_db_connection
from datetime import datetime
import random
import csv
import io
import json

def generate_delivery_code():
    """Generate a unique 6-digit delivery verification code"""
    return f"{random.randint(100000, 999999)}"

def send_notification(user_id, title, message, notification_type='order', related_id=None):
    """Helper function to send notifications"""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO notifications (user_id, title, message, notification_type, related_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, message, notification_type, related_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Notification error: {e}")
        return False
    finally:
        conn.close()

def buyer_dashboard():
    """Main buyer dashboard with order overview"""
    user = session.get('user')
    conn = get_db_connection()

    # Get active orders
    active_orders = conn.execute("""
        SELECT t.*, s.name as seller_name, s.handle as seller_handle,
               d.id as deliverer_user_id,
               COUNT(ti.id) as item_count
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        LEFT JOIN deliverers d ON t.deliverer_id = d.id
        LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
        WHERE t.user_id = ? AND t.status NOT IN ('COMPLETED', 'CANCELLED', 'REFUNDED')
        GROUP BY t.id
        ORDER BY t.timestamp DESC
        LIMIT 10
    """, (user['id'],)).fetchall()

    # Get recent completed orders
    completed_orders = conn.execute("""
        SELECT t.*, s.name as seller_name, s.handle as seller_handle,
               COUNT(ti.id) as item_count
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
        WHERE t.user_id = ? AND t.status IN ('COMPLETED', 'CANCELLED', 'REFUNDED')
        GROUP BY t.id
        ORDER BY t.timestamp DESC
        LIMIT 5
    """, (user['id'],)).fetchall()

    # Get unread notifications
    notifications = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC
        LIMIT 5
    """, (user['id'],)).fetchall()

    # Get pending returns
    pending_returns = conn.execute("""
        SELECT r.*, t.id as transaction_id, s.name as seller_name
        FROM return_requests r
        JOIN transactions t ON r.transaction_id = t.id
        JOIN sellers s ON r.seller_id = s.id
        WHERE r.user_id = ? AND r.status NOT IN ('COMPLETED', 'REJECTED')
        ORDER BY r.created_at DESC
    """, (user['id'],)).fetchall()

    # Calculate stats
    total_orders = conn.execute("""
        SELECT COUNT(*) as count FROM transactions WHERE user_id = ?
    """, (user['id'],)).fetchone()['count']

    total_spent = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0) as total
        FROM transactions
        WHERE user_id = ? AND status NOT IN ('CANCELLED', 'REFUNDED')
    """, (user['id'],)).fetchone()['total']

    dashboard_data = {
        'active_orders': [dict(o) for o in active_orders],
        'completed_orders': [dict(o) for o in completed_orders],
        'notifications': [dict(n) for n in notifications],
        'pending_returns': [dict(r) for r in pending_returns],
        'stats': {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'active_count': len(active_orders),
            'notifications_count': len(notifications)
        }
    }

    conn.close()
    return render_template('buyer/dashboard.html', data=dashboard_data)

def order_tracking(order_id):
    """Detailed order tracking with timeline"""
    user = session.get('user')
    conn = get_db_connection()

    # Get order details
    order = conn.execute("""
        SELECT t.*, s.name as seller_name, s.handle as seller_handle,
               s.location as seller_location, s.id as seller_id,
               d.id as deliverer_user_id, d.name as deliverer_name
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        LEFT JOIN deliverers d ON t.deliverer_id = d.id
        WHERE t.id = ? AND t.user_id = ?
    """, (order_id, user['id'])).fetchone()

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    order_dict = dict(order)

    # Get order items
    items = conn.execute("""
        SELECT ti.*, p.name as product_name, p.images
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        WHERE ti.transaction_id = ?
    """, (order_id,)).fetchall()
    order_dict['items'] = [dict(i) for i in items]

    # Get tracking timeline
    tracking = conn.execute("""
        SELECT * FROM delivery_tracking
        WHERE transaction_id = ?
        ORDER BY created_at ASC
    """, (order_id,)).fetchall()
    order_dict['tracking'] = [dict(t) for t in tracking]

    # Check if review exists
    review = conn.execute("""
        SELECT * FROM reviews
        WHERE user_id = ? AND transaction_id = ?
    """, (user['id'], order_id)).fetchone()
    order_dict['has_review'] = review is not None

    deliverer_review = conn.execute("""
        SELECT * FROM deliverer_reviews
        WHERE user_id = ? AND transaction_id = ?
    """, (user['id'], order_id)).fetchone()
    order_dict['has_deliverer_review'] = deliverer_review is not None

    conn.close()
    return render_template('buyer/order_tracking.html', order=order_dict)

def generate_delivery_code_endpoint(order_id):
    """Generate delivery verification code for buyer"""
    user = session.get('user')
    conn = get_db_connection()

    # Verify order belongs to buyer
    order = conn.execute("""
        SELECT * FROM transactions
        WHERE id = ? AND user_id = ?
    """, (order_id, user['id'])).fetchone()

    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    # Generate code
    code = generate_delivery_code()

    # Update order
    conn.execute("""
        UPDATE transactions
        SET delivery_code = ?
        WHERE id = ?
    """, (code, order_id))
    conn.commit()

    # Send notification to deliverer
    if order['deliverer_id']:
        send_notification(
            order['deliverer_id'],
            'Delivery Code Generated',
            f'Buyer generated delivery code for order #{order_id}',
            'delivery',
            order_id
        )

    conn.close()
    return jsonify({'success': True, 'code': code})

def request_return(order_id):
    """Submit a return request"""
    user = session.get('user')
    conn = get_db_connection()

    data = request.get_json()
    reason = data.get('reason')
    description = data.get('description', '')
    images = json.dumps(data.get('images', []))

    # Get order details
    order = conn.execute("""
        SELECT * FROM transactions
        WHERE id = ? AND user_id = ?
    """, (order_id, user['id'])).fetchone()

    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    if order['status'] != 'DELIVERED':
        return jsonify({'success': False, 'error': 'Can only return delivered orders'}), 400

    # Create return request
    conn.execute("""
        INSERT INTO return_requests
        (transaction_id, user_id, seller_id, reason, description, images)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, user['id'], order['seller_id'], reason, description, images))
    conn.commit()

    # Send notifications
    send_notification(
        order['seller_id'],
        'Return Request',
        f'Customer requested return for order #{order_id}',
        'order',
        order_id
    )

    conn.close()
    return jsonify({'success': True, 'message': 'Return request submitted'})

def download_order_csv(order_id):
    """Download order receipt as CSV"""
    user = session.get('user')
    conn = get_db_connection()

    # Get order details
    order = conn.execute("""
        SELECT t.*, s.name as seller_name
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        WHERE t.id = ? AND t.user_id = ?
    """, (order_id, user['id'])).fetchone()

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Get order items
    items = conn.execute("""
        SELECT ti.*, p.name as product_name
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        WHERE ti.transaction_id = ?
    """, (order_id,)).fetchall()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['SparzaFI Order Receipt'])
    writer.writerow(['Order ID', order_id])
    writer.writerow(['Date', order['timestamp']])
    writer.writerow(['Seller', order['seller_name']])
    writer.writerow(['Status', order['status']])
    writer.writerow([])

    # Write items
    writer.writerow(['Product', 'Quantity', 'Unit Price', 'Total'])
    for item in items:
        writer.writerow([
            item['product_name'],
            item['quantity'],
            f"R{item['unit_price']:.2f}",
            f"R{item['total_price']:.2f}"
        ])

    writer.writerow([])
    writer.writerow(['Subtotal', f"R{order['seller_amount']:.2f}"])
    writer.writerow(['Delivery Fee', f"R{order['deliverer_fee']:.2f}"])
    writer.writerow(['Tax', f"R{order['tax_amount']:.2f}"])
    writer.writerow(['Total', f"R{order['total_amount']:.2f}"])

    # Convert to bytes
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'order_{order_id}_receipt.csv'
    )

def purchase_history():
    """Full purchase history with pagination"""
    user = session.get('user')
    conn = get_db_connection()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Get orders
    orders = conn.execute("""
        SELECT t.*, s.name as seller_name, s.handle as seller_handle,
               COUNT(ti.id) as item_count
        FROM transactions t
        LEFT JOIN sellers s ON t.seller_id = s.id
        LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.timestamp DESC
        LIMIT ? OFFSET ?
    """, (user['id'], per_page, offset)).fetchall()

    # Get total count
    total = conn.execute("""
        SELECT COUNT(*) as count FROM transactions WHERE user_id = ?
    """, (user['id'],)).fetchone()['count']

    history_data = {
        'orders': [dict(o) for o in orders],
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': (total + per_page - 1) // per_page
    }

    conn.close()
    return render_template('buyer/purchase_history.html', data=history_data)

def manage_addresses():
    """Manage delivery addresses"""
    user = session.get('user')
    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            label = request.form.get('label')
            full_address = request.form.get('full_address')
            city = request.form.get('city')
            postal_code = request.form.get('postal_code')
            phone_number = request.form.get('phone_number')
            delivery_instructions = request.form.get('delivery_instructions')
            is_default = request.form.get('is_default') == 'on'

            # If setting as default, unset others
            if is_default:
                conn.execute("UPDATE buyer_addresses SET is_default = 0 WHERE user_id = ?", (user['id'],))

            conn.execute("""
                INSERT INTO buyer_addresses
                (user_id, label, full_address, city, postal_code, phone_number, delivery_instructions, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user['id'], label, full_address, city, postal_code, phone_number, delivery_instructions, is_default))
            conn.commit()

        elif action == 'delete':
            address_id = request.form.get('address_id')
            conn.execute("DELETE FROM buyer_addresses WHERE id = ? AND user_id = ?", (address_id, user['id']))
            conn.commit()

        elif action == 'set_default':
            address_id = request.form.get('address_id')
            conn.execute("UPDATE buyer_addresses SET is_default = 0 WHERE user_id = ?", (user['id'],))
            conn.execute("UPDATE buyer_addresses SET is_default = 1 WHERE id = ? AND user_id = ?", (address_id, user['id']))
            conn.commit()

    # Get all addresses
    addresses = conn.execute("""
        SELECT * FROM buyer_addresses
        WHERE user_id = ?
        ORDER BY is_default DESC, created_at DESC
    """, (user['id'],)).fetchall()

    conn.close()
    return render_template('buyer/addresses.html', addresses=[dict(a) for a in addresses])
