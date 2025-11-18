"""
Firebase-based Verification Code System
Handles pickup and delivery verification codes for SparzaFI
"""

from datetime import datetime, timedelta
import random
import hashlib
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Firebase imports
from firebase_config import get_firestore_db
from firebase_db import (
    transaction_service,
    seller_service,
    get_notification_service,
    delivery_tracking_service
)


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
    Stores hashed code in Firestore with 24-hour expiration
    """
    db = get_firestore_db()
    notification_service = get_notification_service()

    # Check if code already exists for this transaction
    codes_ref = db.collection('verification_codes')
    existing_query = codes_ref.where(filter=FieldFilter('transaction_id', '==', transaction_id)) \
                               .where(filter=FieldFilter('code_type', '==', 'PICKUP')) \
                               .where(filter=FieldFilter('is_used', '==', False))

    existing = list(existing_query.limit(1).stream())

    if existing:
        return {'success': False, 'error': 'Pickup code already exists'}

    # Generate new code
    code_data = generate_verification_code('PICKUP')
    code_hash = hash_code(code_data['code'])

    # Calculate expiration (24 hours from now)
    expires_at = datetime.now() + timedelta(hours=24)

    try:
        # Store hashed code in Firebase
        code_doc_data = {
            'transaction_id': transaction_id,
            'code_type': 'PICKUP',
            'code_hash': code_hash,
            'expires_at': expires_at,
            'created_by': created_by,
            'max_attempts': 3,
            'attempts': 0,
            'is_used': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        db.collection('verification_codes').add(code_doc_data)

        # Update transaction with pickup code and status
        transaction_service.update(transaction_id, {
            'pickup_code': code_data['code'],
            'status': 'READY_FOR_PICKUP'
        })

        # Get transaction to send notification
        transaction = transaction_service.get(transaction_id)
        if transaction and transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller and seller.get('user_id'):
                notification_service.create(seller['user_id'], {
                    'title': 'Pickup Code Generated',
                    'message': f"Your pickup code is: {code_data['display_code']}. Give this to the driver.",
                    'notification_type': 'pickup_code',
                    'is_read': False,
                    'created_at': firestore.SERVER_TIMESTAMP
                })

        return {
            'success': True,
            'display_code': code_data['display_code'],
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_delivery_code(transaction_id, created_by):
    """
    Buyer generates a delivery code once they're ready to receive
    Stores hashed code in Firestore with 24-hour expiration
    """
    db = get_firestore_db()
    notification_service = get_notification_service()

    # Check if code already exists
    codes_ref = db.collection('verification_codes')
    existing_query = codes_ref.where(filter=FieldFilter('transaction_id', '==', transaction_id)) \
                               .where(filter=FieldFilter('code_type', '==', 'DELIVERY')) \
                               .where(filter=FieldFilter('is_used', '==', False))

    existing = list(existing_query.limit(1).stream())

    if existing:
        return {'success': False, 'error': 'Delivery code already exists'}

    # Generate new code
    code_data = generate_verification_code('DELIVERY')
    code_hash = hash_code(code_data['code'])

    # Calculate expiration (24 hours from now)
    expires_at = datetime.now() + timedelta(hours=24)

    try:
        # Store hashed code in Firebase
        code_doc_data = {
            'transaction_id': transaction_id,
            'code_type': 'DELIVERY',
            'code_hash': code_hash,
            'expires_at': expires_at,
            'created_by': created_by,
            'max_attempts': 3,
            'attempts': 0,
            'is_used': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        db.collection('verification_codes').add(code_doc_data)

        # Update transaction with delivery code
        transaction_service.update(transaction_id, {
            'delivery_code': code_data['code']
        })

        # Get transaction to send notification
        transaction = transaction_service.get(transaction_id)
        if transaction and transaction.get('user_id'):
            notification_service.create(transaction['user_id'], {
                'title': 'Delivery Code Generated',
                'message': f"Your delivery code is: {code_data['display_code']}. Give this to the driver when you receive your order.",
                'notification_type': 'delivery_code',
                'is_read': False,
                'created_at': firestore.SERVER_TIMESTAMP
            })

        return {
            'success': True,
            'display_code': code_data['display_code'],
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def verify_pickup_code(transaction_id, input_code, verified_by):
    """
    Driver verifies pickup code from seller
    Handles attempt limits and expiration
    """
    db = get_firestore_db()
    notification_service = get_notification_service()

    # Strip prefix if present
    clean_code = input_code.replace('PU-', '').replace('DL-', '').strip()
    code_hash = hash_code(clean_code)

    # Get verification code record
    codes_ref = db.collection('verification_codes')
    code_query = codes_ref.where(filter=FieldFilter('transaction_id', '==', transaction_id)) \
                          .where(filter=FieldFilter('code_type', '==', 'PICKUP')) \
                          .where(filter=FieldFilter('is_used', '==', False))

    code_docs = list(code_query.limit(1).stream())

    if not code_docs:
        return {'success': False, 'error': 'Invalid or already used pickup code'}

    code_doc = code_docs[0]
    code_record = code_doc.to_dict()
    code_doc_ref = code_doc.reference

    # Check expiration
    expires_at = code_record['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
    elif hasattr(expires_at, 'replace'):  # Firestore timestamp
        expires_at = expires_at.replace(tzinfo=None) if hasattr(expires_at, 'tzinfo') else expires_at

    if datetime.now() > expires_at:
        return {'success': False, 'error': 'Pickup code has expired'}

    # Check attempts
    attempts = code_record.get('attempts', 0)
    max_attempts = code_record.get('max_attempts', 3)

    if attempts >= max_attempts:
        return {'success': False, 'error': 'Maximum verification attempts exceeded'}

    # Verify code
    if code_hash != code_record['code_hash']:
        # Increment attempts
        code_doc_ref.update({'attempts': attempts + 1})

        remaining = max_attempts - (attempts + 1)
        return {
            'success': False,
            'error': f'Invalid pickup code. {remaining} attempt(s) remaining'
        }

    # Code is valid - mark as used and update transaction
    try:
        code_doc_ref.update({
            'is_used': True,
            'verified_by': verified_by,
            'verified_at': firestore.SERVER_TIMESTAMP
        })

        transaction_service.update(transaction_id, {
            'status': 'PICKED_UP',
            'pickup_verified_at': firestore.SERVER_TIMESTAMP
        })

        # Add tracking
        delivery_tracking_service.create({
            'transaction_id': transaction_id,
            'status': 'PICKED_UP',
            'notes': 'Pickup verified with code',
            'created_by': verified_by,
            'created_at': firestore.SERVER_TIMESTAMP
        })

        # Notify seller
        transaction = transaction_service.get(transaction_id)
        if transaction and transaction.get('seller_id'):
            seller = seller_service.get(transaction['seller_id'])
            if seller and seller.get('user_id'):
                notification_service.create(seller['user_id'], {
                    'title': 'Order Picked Up',
                    'message': f"Order #{transaction_id} has been picked up by the driver.",
                    'notification_type': 'pickup_verified',
                    'is_read': False,
                    'created_at': firestore.SERVER_TIMESTAMP
                })

        return {
            'success': True,
            'message': 'Pickup verified successfully! Order now in transit.'
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def verify_delivery_code(transaction_id, input_code, verified_by):
    """
    Driver verifies delivery code from buyer
    Handles attempt limits, expiration, and triggers settlement
    """
    db = get_firestore_db()
    notification_service = get_notification_service()

    # Strip prefix if present
    clean_code = input_code.replace('PU-', '').replace('DL-', '').strip()
    code_hash = hash_code(clean_code)

    # Get verification code record
    codes_ref = db.collection('verification_codes')
    code_query = codes_ref.where(filter=FieldFilter('transaction_id', '==', transaction_id)) \
                          .where(filter=FieldFilter('code_type', '==', 'DELIVERY')) \
                          .where(filter=FieldFilter('is_used', '==', False))

    code_docs = list(code_query.limit(1).stream())

    if not code_docs:
        return {'success': False, 'error': 'Invalid or already used delivery code'}

    code_doc = code_docs[0]
    code_record = code_doc.to_dict()
    code_doc_ref = code_doc.reference

    # Check expiration
    expires_at = code_record['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
    elif hasattr(expires_at, 'replace'):  # Firestore timestamp
        expires_at = expires_at.replace(tzinfo=None) if hasattr(expires_at, 'tzinfo') else expires_at

    if datetime.now() > expires_at:
        return {'success': False, 'error': 'Delivery code has expired'}

    # Check attempts
    attempts = code_record.get('attempts', 0)
    max_attempts = code_record.get('max_attempts', 3)

    if attempts >= max_attempts:
        return {'success': False, 'error': 'Maximum verification attempts exceeded'}

    # Verify code
    if code_hash != code_record['code_hash']:
        # Increment attempts
        code_doc_ref.update({'attempts': attempts + 1})

        remaining = max_attempts - (attempts + 1)
        return {
            'success': False,
            'error': f'Invalid delivery code. {remaining} attempt(s) remaining'
        }

    # Code is valid - mark as used and complete delivery
    try:
        code_doc_ref.update({
            'is_used': True,
            'verified_by': verified_by,
            'verified_at': firestore.SERVER_TIMESTAMP
        })

        transaction_service.update(transaction_id, {
            'status': 'DELIVERED',
            'delivered_at': firestore.SERVER_TIMESTAMP
        })

        # Add tracking
        delivery_tracking_service.create({
            'transaction_id': transaction_id,
            'status': 'DELIVERED',
            'notes': 'Delivery verified with code',
            'created_by': verified_by,
            'created_at': firestore.SERVER_TIMESTAMP
        })

        # Notify buyer
        transaction = transaction_service.get(transaction_id)
        if transaction and transaction.get('user_id'):
            notification_service.create(transaction['user_id'], {
                'title': 'Delivery Confirmed',
                'message': f"Order #{transaction_id} has been delivered successfully!",
                'notification_type': 'delivery_verified',
                'is_read': False,
                'created_at': firestore.SERVER_TIMESTAMP
            })

        # TODO: Trigger settlement (implement settlement logic)
        settlement_result = {'success': True, 'message': 'Settlement will be processed'}

        return {
            'success': True,
            'message': 'Delivery verified successfully! Funds are being processed.',
            'settlement': settlement_result
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def expire_old_verification_codes():
    """
    Cleanup job to expire old verification codes
    Should be run periodically (e.g., daily via cron job)
    """
    db = get_firestore_db()

    try:
        codes_ref = db.collection('verification_codes')
        # Get all unused codes
        query = codes_ref.where(filter=FieldFilter('is_used', '==', False))

        expired_count = 0
        now = datetime.now()

        for doc in query.stream():
            code_data = doc.to_dict()
            expires_at = code_data.get('expires_at')

            if isinstance(expires_at, str):
                expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            elif hasattr(expires_at, 'replace'):  # Firestore timestamp
                expires_at = expires_at.replace(tzinfo=None) if hasattr(expires_at, 'tzinfo') else expires_at

            # Check if expired
            if expires_at and now > expires_at:
                doc.reference.update({'is_used': True})
                expired_count += 1

        return {
            'success': True,
            'expired_count': expired_count
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}
