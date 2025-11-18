"""
Buyer Dashboard Module - Migrated to Firebase
Comprehensive buyer features including order tracking, returns, ratings, and more
"""

from flask import render_template, redirect, url_for, session, request, jsonify, send_file
from shared.utils import login_required
from datetime import datetime
import random
import csv
import io
import json

# Firebase imports
from firebase_db import (
    transaction_service,
    seller_service,
    deliverer_service,
    get_product_service,
    get_notification_service,
    review_service,
    delivery_tracking_service
)
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


def generate_delivery_code():
    """Generate a unique 6-digit delivery verification code"""
    return f"{random.randint(100000, 999999)}"


def send_notification(user_id, title, message, notification_type='order', related_id=None):
    """Helper function to send notifications"""
    notification_service = get_notification_service()
    try:
        notification_data = {
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'related_id': related_id,
            'is_read': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        notification_service.create(user_id, notification_data)
        return True
    except Exception as e:
        print(f"Notification error: {e}")
        return False


def buyer_dashboard():
    """Main buyer dashboard with order overview"""
    user = session.get('user')
    db = get_firestore_db()
    product_service = get_product_service()

    # Get all transactions for user
    user_transactions = transaction_service.get_by_user(user['id'])

    # Split into active and completed
    active_orders = []
    completed_orders = []

    for trans in user_transactions:
        # Add seller info
        if trans.get('seller_id'):
            seller = seller_service.get(trans['seller_id'])
            if seller:
                trans['seller_name'] = seller.get('name', '')
                trans['seller_handle'] = seller.get('handle', '')

        # Add deliverer info
        if trans.get('deliverer_id'):
            deliverer = deliverer_service.get(trans['deliverer_id'])
            if deliverer:
                trans['deliverer_user_id'] = deliverer.get('user_id')

        # Count items
        trans['item_count'] = len(trans.get('items', []))

        # Categorize
        if trans.get('status') in ['COMPLETED', 'CANCELLED', 'REFUNDED']:
            if len(completed_orders) < 5:
                completed_orders.append(trans)
        else:
            if len(active_orders) < 10:
                active_orders.append(trans)

    # Sort by timestamp
    active_orders = sorted(active_orders, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
    completed_orders = sorted(completed_orders, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]

    # Get unread notifications
    notification_service = get_notification_service()
    all_notifications = notification_service.get_by_user(user['id'])
    notifications = [n for n in all_notifications if not n.get('is_read', False)][:5]

    # Get pending returns
    return_requests_ref = db.collection('return_requests')
    return_query = return_requests_ref.where(filter=FieldFilter('user_id', '==', user['id']))
    pending_returns = []

    for doc in return_query.stream():
        return_data = doc.to_dict()
        return_data['id'] = doc.id

        if return_data.get('status') not in ['COMPLETED', 'REJECTED']:
            # Get transaction and seller info
            if return_data.get('transaction_id'):
                trans = transaction_service.get(return_data['transaction_id'])
                if trans:
                    return_data['transaction_id'] = trans.get('id')

            if return_data.get('seller_id'):
                seller = seller_service.get(return_data['seller_id'])
                if seller:
                    return_data['seller_name'] = seller.get('name', '')

            pending_returns.append(return_data)

    # Calculate stats
    total_orders = len(user_transactions)
    total_spent = sum(
        float(t.get('total_amount', 0))
        for t in user_transactions
        if t.get('status') not in ['CANCELLED', 'REFUNDED']
    )

    dashboard_data = {
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'notifications': notifications,
        'pending_returns': pending_returns,
        'stats': {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'active_count': len(active_orders),
            'notifications_count': len(notifications)
        }
    }

    return render_template('buyer/dashboard.html', data=dashboard_data)


def order_tracking(order_id):
    """Detailed order tracking with timeline"""
    user = session.get('user')
    db = get_firestore_db()
    product_service = get_product_service()

    # Get order details
    order = transaction_service.get(order_id)

    if not order or order.get('user_id') != user['id']:
        return jsonify({'error': 'Order not found'}), 404

    # Add seller info
    if order.get('seller_id'):
        seller = seller_service.get(order['seller_id'])
        if seller:
            order['seller_name'] = seller.get('name', '')
            order['seller_handle'] = seller.get('handle', '')
            order['seller_location'] = seller.get('location', '')
            order['seller_id'] = order['seller_id']

    # Add deliverer info
    if order.get('deliverer_id'):
        deliverer = deliverer_service.get(order['deliverer_id'])
        if deliverer:
            order['deliverer_user_id'] = deliverer.get('user_id')
            order['deliverer_name'] = deliverer.get('name', '')

    # Add product details to items
    items = order.get('items', [])
    for item in items:
        if item.get('product_id'):
            product = product_service.get(item['product_id'])
            if product:
                item['product_name'] = product.get('name', '')
                item['images'] = product.get('images', [])

    order['items'] = items

    # Get tracking timeline
    tracking = delivery_tracking_service.get_by_transaction(order_id)
    order['tracking'] = sorted(tracking, key=lambda x: x.get('created_at', ''))

    # Check if review exists
    user_reviews = review_service.get_by_user(user['id'])
    has_review = any(r.get('transaction_id') == order_id for r in user_reviews)
    order['has_review'] = has_review

    # Check deliverer review
    deliverer_reviews_ref = db.collection('deliverer_reviews')
    deliverer_review_query = deliverer_reviews_ref.where(filter=FieldFilter('user_id', '==', user['id'])).where(filter=FieldFilter('transaction_id', '==', order_id))
    has_deliverer_review = len(list(deliverer_review_query.limit(1).stream())) > 0
    order['has_deliverer_review'] = has_deliverer_review

    return render_template('buyer/order_tracking.html', order=order)


def generate_delivery_code_endpoint(order_id):
    """Generate delivery verification code for buyer"""
    user = session.get('user')

    # Verify order belongs to buyer
    order = transaction_service.get(order_id)

    if not order or order.get('user_id') != user['id']:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    # Generate code
    code = generate_delivery_code()

    # Update order
    transaction_service.update(order_id, {'delivery_code': code})

    # Send notification to deliverer
    if order.get('deliverer_id'):
        deliverer = deliverer_service.get(order['deliverer_id'])
        if deliverer and deliverer.get('user_id'):
            send_notification(
                deliverer['user_id'],
                'Delivery Code Generated',
                f'Buyer generated delivery code for order #{order_id}',
                'delivery',
                order_id
            )

    return jsonify({'success': True, 'code': code})


def request_return(order_id):
    """Submit a return request"""
    user = session.get('user')
    db = get_firestore_db()

    data = request.get_json()
    reason = data.get('reason')
    description = data.get('description', '')
    images = data.get('images', [])

    # Get order details
    order = transaction_service.get(order_id)

    if not order or order.get('user_id') != user['id']:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    if order.get('status') != 'DELIVERED':
        return jsonify({'success': False, 'error': 'Can only return delivered orders'}), 400

    # Create return request
    return_data = {
        'transaction_id': order_id,
        'user_id': user['id'],
        'seller_id': order.get('seller_id'),
        'reason': reason,
        'description': description,
        'images': images,
        'status': 'PENDING',
        'created_at': firestore.SERVER_TIMESTAMP
    }

    db.collection('return_requests').add(return_data)

    # Send notification to seller
    if order.get('seller_id'):
        seller = seller_service.get(order['seller_id'])
        if seller and seller.get('user_id'):
            send_notification(
                seller['user_id'],
                'Return Request',
                f'Customer requested return for order #{order_id}',
                'order',
                order_id
            )

    return jsonify({'success': True, 'message': 'Return request submitted'})


def download_order_csv(order_id):
    """Download order receipt as CSV"""
    user = session.get('user')
    product_service = get_product_service()

    # Get order details
    order = transaction_service.get(order_id)

    if not order or order.get('user_id') != user['id']:
        return jsonify({'error': 'Order not found'}), 404

    # Get seller name
    seller_name = ''
    if order.get('seller_id'):
        seller = seller_service.get(order['seller_id'])
        if seller:
            seller_name = seller.get('name', '')

    # Get order items with product names
    items = []
    for item in order.get('items', []):
        item_data = dict(item)
        if item.get('product_id'):
            product = product_service.get(item['product_id'])
            if product:
                item_data['product_name'] = product.get('name', '')
        items.append(item_data)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['SparzaFI Order Receipt'])
    writer.writerow(['Order ID', order_id])
    writer.writerow(['Date', order.get('timestamp', '')])
    writer.writerow(['Seller', seller_name])
    writer.writerow(['Status', order.get('status', '')])
    writer.writerow([])

    # Write items
    writer.writerow(['Product', 'Quantity', 'Unit Price', 'Total'])
    for item in items:
        writer.writerow([
            item.get('product_name', ''),
            item.get('quantity', 0),
            f"R{item.get('unit_price', 0):.2f}",
            f"R{item.get('total_price', 0):.2f}"
        ])

    writer.writerow([])
    writer.writerow(['Subtotal', f"R{order.get('seller_amount', 0):.2f}"])
    writer.writerow(['Delivery Fee', f"R{order.get('deliverer_fee', 0):.2f}"])
    writer.writerow(['Tax', f"R{order.get('tax_amount', 0):.2f}"])
    writer.writerow(['Total', f"R{order.get('total_amount', 0):.2f}"])

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
    product_service = get_product_service()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Get all user transactions
    all_transactions = transaction_service.get_by_user(user['id'])

    # Add seller info and item count
    for trans in all_transactions:
        if trans.get('seller_id'):
            seller = seller_service.get(trans['seller_id'])
            if seller:
                trans['seller_name'] = seller.get('name', '')
                trans['seller_handle'] = seller.get('handle', '')

        trans['item_count'] = len(trans.get('items', []))

    # Sort by timestamp
    all_transactions = sorted(all_transactions, key=lambda x: x.get('timestamp', ''), reverse=True)

    # Paginate
    total = len(all_transactions)
    orders = all_transactions[offset:offset + per_page]

    history_data = {
        'orders': orders,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': (total + per_page - 1) // per_page
    }

    return render_template('buyer/purchase_history.html', data=history_data)


def manage_addresses():
    """Manage delivery addresses"""
    user = session.get('user')
    db = get_firestore_db()

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
                addresses_ref = db.collection('buyer_addresses')
                user_addresses = addresses_ref.where(filter=FieldFilter('user_id', '==', user['id'])).stream()
                for doc in user_addresses:
                    doc.reference.update({'is_default': False})

            address_data = {
                'user_id': user['id'],
                'label': label,
                'full_address': full_address,
                'city': city,
                'postal_code': postal_code,
                'phone_number': phone_number,
                'delivery_instructions': delivery_instructions,
                'is_default': is_default,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('buyer_addresses').add(address_data)

        elif action == 'delete':
            address_id = request.form.get('address_id')
            address_ref = db.collection('buyer_addresses').document(address_id)
            address = address_ref.get()
            if address.exists and address.to_dict().get('user_id') == user['id']:
                address_ref.delete()

        elif action == 'set_default':
            address_id = request.form.get('address_id')
            # Unset all defaults
            addresses_ref = db.collection('buyer_addresses')
            user_addresses = addresses_ref.where(filter=FieldFilter('user_id', '==', user['id'])).stream()
            for doc in user_addresses:
                doc.reference.update({'is_default': False})

            # Set new default
            address_ref = db.collection('buyer_addresses').document(address_id)
            address = address_ref.get()
            if address.exists and address.to_dict().get('user_id') == user['id']:
                address_ref.update({'is_default': True})

    # Get all addresses
    addresses_ref = db.collection('buyer_addresses')
    addresses_query = addresses_ref.where(filter=FieldFilter('user_id', '==', user['id']))

    addresses = []
    for doc in addresses_query.stream():
        addr = doc.to_dict()
        addr['id'] = doc.id
        addresses.append(addr)

    # Sort by default first, then by created_at
    addresses = sorted(addresses, key=lambda x: (not x.get('is_default', False), x.get('created_at', '')), reverse=True)

    return render_template('buyer/addresses.html', addresses=addresses)
