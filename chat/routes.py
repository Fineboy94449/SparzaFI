"""
Chat Routes - Enhanced API endpoints for 3 chat types
Supports: Buyer↔Seller, Buyer↔Deliverer, Seller↔Deliverer
With KYC verification and message filtering
"""
from flask import request, jsonify, session, render_template
from . import chat_bp
from .message_filter import validate_message

# Firebase imports
from firebase_db import (
    conversation_service,
    message_service,
    get_user_service,
    get_notification_service,
    seller_service,
    deliverer_service,
    transaction_service
)


def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_user_role(user_id, transaction_id=None):
    """
    Determine user's role in a transaction or general context

    Returns:
        str: 'buyer', 'seller', or 'deliverer'
    """
    # Check if user is a seller
    seller = seller_service.get_by_user_id(user_id)
    if seller:
        # If transaction provided, check if they're the seller for this transaction
        if transaction_id:
            txn = transaction_service.get(transaction_id)
            if txn and txn.get('seller_id') == seller['id']:
                return 'seller'
        else:
            return 'seller'

    # Check if user is a deliverer
    deliverer = deliverer_service.get_by_user_id(user_id)
    if deliverer:
        if transaction_id:
            txn = transaction_service.get(transaction_id)
            if txn and txn.get('deliverer_id') == deliverer['id']:
                return 'deliverer'
        else:
            return 'deliverer'

    # Default to buyer
    return 'buyer'


def check_kyc_permission(user_id, role):
    """
    Check if user has permission to send messages (KYC check)

    Args:
        user_id: User ID
        role: User role ('buyer', 'seller', 'deliverer')

    Returns:
        tuple: (has_permission: bool, error_message: str)
    """
    user_service = get_user_service()
    user = user_service.get(user_id)

    if not user:
        return False, "User not found"

    # Buyers can always send messages
    if role == 'buyer':
        return True, ""

    # Sellers must be KYC verified
    if role == 'seller':
        seller = seller_service.get_by_user_id(user_id)
        if not seller:
            return False, "Seller profile not found"

        if not seller.get('is_verified', False):
            return False, "Your seller account must be KYC verified to send messages. Please complete verification."

        return True, ""

    # Deliverers must be verified
    if role == 'deliverer':
        deliverer = deliverer_service.get_by_user_id(user_id)
        if not deliverer:
            return False, "Deliverer profile not found"

        if not deliverer.get('is_verified', False):
            return False, "Your deliverer account must be verified to send messages. Please complete verification."

        return True, ""

    return True, ""


@chat_bp.route('/send', methods=['POST'])
@require_auth
def send_message():
    """
    Send a message (supports all 3 chat types)

    Expected JSON:
    {
        "recipient_id": "uuid",
        "message": "text",
        "transaction_id": "uuid" (optional),
        "chat_type": "buyer_seller" | "buyer_deliverer" | "seller_deliverer"
    }
    """
    current_user_id = session['user']['id']
    data = request.get_json()

    recipient_id = data.get('recipient_id')
    message_text = data.get('message', '').strip()
    transaction_id = data.get('transaction_id')
    chat_type = data.get('chat_type', 'buyer_seller')

    # Validate inputs
    if not recipient_id:
        return jsonify({'error': 'Recipient ID is required'}), 400

    if not message_text:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if recipient_id == current_user_id:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    # Validate message content (filter phone/email/URLs)
    is_valid, error_msg = validate_message(message_text)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    # Determine sender role
    sender_role = get_user_role(current_user_id, transaction_id)

    # Check KYC permission
    has_permission, permission_error = check_kyc_permission(current_user_id, sender_role)
    if not has_permission:
        return jsonify({'error': permission_error}), 403

    # Verify recipient exists
    user_service = get_user_service()
    recipient = user_service.get(recipient_id)
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    # For transaction-based chats, verify transaction exists
    if transaction_id:
        txn = transaction_service.get(transaction_id)
        if not txn:
            return jsonify({'error': 'Transaction not found'}), 404

    # Find or create conversation
    conversation = conversation_service.get_or_create_conversation(
        current_user_id,
        recipient_id,
        transaction_id=transaction_id,
        chat_type=chat_type
    )
    conversation_id = conversation['id']

    # Create message
    message_data = {
        'conversation_id': conversation_id,
        'sender_id': current_user_id,
        'recipient_id': recipient_id,
        'message_text': message_text,
        'sender_role': sender_role,
        'is_read': False
    }

    if transaction_id:
        message_data['transaction_id'] = transaction_id

    message_id = message_service.create(message_data)

    # Update conversation last message
    conversation_service.update_last_message(conversation_id, message_text)

    # Create notification for recipient
    notification_service = get_notification_service()
    sender_name = session['user'].get('name') or session['user'].get('email')

    notification_service.create_notification(
        user_id=recipient_id,
        title='New Message',
        message=f'{sender_name}: {message_text[:50]}...',
        notification_type='message',
        data={'conversation_id': conversation_id, 'transaction_id': transaction_id}
    )

    return jsonify({
        'status': 'Message sent',
        'conversation_id': conversation_id,
        'message_id': message_id
    }), 201


@chat_bp.route('/history/<conversation_id>', methods=['GET'])
@require_auth
def get_chat_history(conversation_id):
    """Get all messages for a specific conversation"""
    current_user_id = session['user']['id']
    user_service = get_user_service()

    # Verify user is part of this conversation
    conversation = conversation_service.get(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    # Check if user is participant
    user_ids = [
        conversation.get('user1_id'),
        conversation.get('user2_id'),
        conversation.get('buyer_id'),
        conversation.get('seller_id'),
        conversation.get('deliverer_id')
    ]

    if current_user_id not in user_ids:
        return jsonify({'error': 'Not authorized to view this conversation'}), 403

    # Get all messages
    messages = message_service.get_conversation_messages(conversation_id)

    # Mark messages as read
    message_service.mark_as_read(conversation_id, current_user_id)

    # Format messages for response
    result = []
    for msg in messages:
        sender = user_service.get(msg['sender_id'])
        sender_name = sender.get('name') or sender.get('email') if sender else 'Unknown'

        result.append({
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'sender_name': sender_name,
            'sender_role': msg.get('sender_role', 'buyer'),
            'message': msg.get('message_text', ''),
            'timestamp': msg.get('created_at'),
            'is_read': msg.get('is_read', False),
            'is_mine': msg['sender_id'] == current_user_id
        })

    return jsonify({
        'conversation_id': conversation_id,
        'chat_type': conversation.get('chat_type', 'buyer_seller'),
        'transaction_id': conversation.get('transaction_id'),
        'messages': result
    })


@chat_bp.route('/transaction/<transaction_id>', methods=['GET'])
@require_auth
def get_transaction_chat(transaction_id):
    """
    Get chat for a specific transaction
    Returns all conversations related to the transaction
    """
    current_user_id = session['user']['id']

    # Verify transaction exists and user is participant
    txn = transaction_service.get(transaction_id)
    if not txn:
        return jsonify({'error': 'Transaction not found'}), 404

    # Check if user is buyer, seller, or deliverer for this transaction
    user_role = get_user_role(current_user_id, transaction_id)

    # Get seller profile to check if user is the seller
    seller = seller_service.get(txn.get('seller_id', ''))
    is_seller = seller and seller.get('user_id') == current_user_id

    # Get deliverer profile
    deliverer = deliverer_service.get(txn.get('deliverer_id', '')) if txn.get('deliverer_id') else None
    is_deliverer = deliverer and deliverer.get('user_id') == current_user_id

    # Check if user is buyer
    is_buyer = txn.get('buyer_id') == current_user_id

    if not (is_buyer or is_seller or is_deliverer):
        return jsonify({'error': 'Not authorized to view this transaction chat'}), 403

    # Get all conversations for this transaction
    conversations = conversation_service.get_transaction_conversations(transaction_id)

    result = []
    for conv in conversations:
        messages = message_service.get_conversation_messages(conv['id'])

        result.append({
            'conversation_id': conv['id'],
            'chat_type': conv.get('chat_type'),
            'message_count': len(messages),
            'last_message_at': conv.get('last_message_at'),
            'last_message': conv.get('last_message', '')
        })

    return jsonify({
        'transaction_id': transaction_id,
        'user_role': user_role,
        'conversations': result
    })


@chat_bp.route('/mark_read', methods=['POST'])
@require_auth
def mark_messages_read():
    """Mark all messages in a conversation as read"""
    current_user_id = session['user']['id']
    data = request.get_json()

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return jsonify({'error': 'Conversation ID is required'}), 400

    # Verify conversation exists and user is participant
    conversation = conversation_service.get(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    # Check if user is participant
    user_ids = [
        conversation.get('user1_id'),
        conversation.get('user2_id'),
        conversation.get('buyer_id'),
        conversation.get('seller_id'),
        conversation.get('deliverer_id')
    ]

    if current_user_id not in user_ids:
        return jsonify({'error': 'Not authorized'}), 403

    # Mark messages as read
    message_service.mark_as_read(conversation_id, current_user_id)

    return jsonify({'status': 'Messages marked as read'})


@chat_bp.route('/unread-count', methods=['GET'])
@require_auth
def get_unread_count():
    """Get count of unread messages for current user"""
    current_user_id = session['user']['id']

    # Use the enhanced method in MessageService
    unread_count = message_service.get_unread_count(current_user_id)

    return jsonify({'unread_count': unread_count})


@chat_bp.route('/conversations', methods=['GET'])
@require_auth
def get_conversations():
    """Get all conversations for the current user"""
    current_user_id = session['user']['id']
    user_service = get_user_service()

    # Get all conversations where user is participant
    conversations = conversation_service.get_user_conversations(current_user_id)

    result = []
    for conv in conversations:
        # Determine the other user
        other_user_id = None
        if conv.get('user1_id') == current_user_id:
            other_user_id = conv.get('user2_id')
        elif conv.get('user2_id') == current_user_id:
            other_user_id = conv.get('user1_id')
        elif conv.get('buyer_id') == current_user_id:
            other_user_id = conv.get('seller_id') or conv.get('deliverer_id')
        elif conv.get('seller_id') == current_user_id:
            other_user_id = conv.get('buyer_id') or conv.get('deliverer_id')
        elif conv.get('deliverer_id') == current_user_id:
            other_user_id = conv.get('buyer_id') or conv.get('seller_id')

        if other_user_id:
            other_user = user_service.get(other_user_id)
            other_user_name = other_user.get('name') or other_user.get('email') if other_user else 'Unknown'

            result.append({
                'id': conv['id'],
                'other_user_name': other_user_name,
                'other_user_id': other_user_id,
                'chat_type': conv.get('chat_type', 'buyer_seller'),
                'transaction_id': conv.get('transaction_id'),
                'last_message': conv.get('last_message', ''),
                'last_message_at': conv.get('last_message_at'),
                'created_at': conv.get('created_at')
            })

    return jsonify(result)


@chat_bp.route('/widget/<seller_handle>', methods=['GET'])
def chat_widget(seller_handle):
    """
    Render chat widget for buyer-seller communication
    (Embedded on seller shop page)
    """
    if 'user' not in session:
        return "Please login to chat", 401

    # Get seller by handle
    seller = seller_service.get_by_handle(seller_handle)
    if not seller:
        return "Seller not found", 404

    current_user = session['user']

    # Find existing conversation between buyer and seller
    db = get_firestore_db()
    conversations_ref = db.collection('conversations')

    # Try to find existing conversation
    conversation_id = None
    existing_convs = conversations_ref.where('buyer_id', '==', current_user['id']).where('seller_id', '==', seller['id']).limit(1).stream()
    for conv in existing_convs:
        conversation_id = conv.id
        break

    return render_template('chat/chat_widget.html',
                         conversation_id=conversation_id,
                         recipient_id=seller['id'],
                         transaction_id=None,
                         chat_type='buyer_seller',
                         recipient_name=seller.get('name', 'Seller'),
                         recipient_role='seller')
