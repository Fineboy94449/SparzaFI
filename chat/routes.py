"""
Chat Routes - API endpoints for messaging functionality
Migrated to use Firebase Firestore
"""
from flask import request, jsonify, session
from . import chat_bp

# Firebase imports
from firebase_db import (
    conversation_service,
    message_service,
    get_user_service,
    get_notification_service
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
        other_user_id = conv['user2_id'] if conv['user1_id'] == current_user_id else conv['user1_id']

        # Get other user's email
        other_user = user_service.get(other_user_id)
        other_user_email = other_user['email'] if other_user else 'Unknown'

        result.append({
            'id': conv['id'],
            'other_user_email': other_user_email,
            'other_user_id': other_user_id,
            'last_message_at': conv.get('last_message_at'),
            'created_at': conv.get('created_at')
        })

    return jsonify(result)


@chat_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
@require_auth
def get_messages(conversation_id):
    """Get all messages for a specific conversation"""
    current_user_id = session['user']['id']
    user_service = get_user_service()

    # Verify user is part of this conversation
    conversation = conversation_service.get(conversation_id)

    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    if conversation['user1_id'] != current_user_id and conversation['user2_id'] != current_user_id:
        return jsonify({'error': 'Not authorized'}), 403

    # Get all messages in this conversation
    messages = message_service.get_conversation_messages(conversation_id)

    # Mark messages as read
    message_service.mark_as_read(conversation_id, current_user_id)

    result = []
    for msg in messages:
        # Get sender email
        sender = user_service.get(msg['sender_id'])
        sender_email = sender['email'] if sender else 'Unknown'

        result.append({
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'sender_email': sender_email,
            'content': msg.get('message_text', ''),
            'timestamp': msg.get('created_at'),
            'is_read': msg.get('is_read', False)
        })

    return jsonify(result)


@chat_bp.route('/messages', methods=['POST'])
@require_auth
def send_message():
    """Send a message to a user, creating a conversation if needed"""
    current_user_id = session['user']['id']
    data = request.get_json()

    recipient_id = data.get('recipient_id')
    content = data.get('content')

    if not recipient_id or not content:
        return jsonify({'error': 'Recipient and content are required'}), 400

    if recipient_id == current_user_id:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    # Verify recipient exists
    user_service = get_user_service()
    recipient = user_service.get(recipient_id)

    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    # Find or create conversation (always store with lower ID as user1)
    user1_id = min(current_user_id, recipient_id) if isinstance(current_user_id, int) and isinstance(recipient_id, int) else current_user_id
    user2_id = max(current_user_id, recipient_id) if isinstance(current_user_id, int) and isinstance(recipient_id, int) else recipient_id

    conversation = conversation_service.get_or_create_conversation(user1_id, user2_id)
    conversation_id = conversation['id']

    # Create message
    message_data = {
        'conversation_id': conversation_id,
        'sender_id': current_user_id,
        'recipient_id': recipient_id,
        'message_text': content,
        'is_read': False
    }

    message_id = message_service.create(message_data)

    # Update conversation last message timestamp
    conversation_service.update_last_message(conversation_id)

    # Create notification for recipient
    notification_service = get_notification_service()
    notification_service.create_notification(
        user_id=recipient_id,
        title='New Message',
        message=f'You have a new message from {session["user"]["email"]}',
        notification_type='message',
        data={'conversation_id': conversation_id}
    )

    return jsonify({
        'status': 'Message sent',
        'conversation_id': conversation_id,
        'message_id': message_id
    }), 201


@chat_bp.route('/unread-count', methods=['GET'])
@require_auth
def get_unread_count():
    """Get count of unread messages for current user"""
    current_user_id = session['user']['id']

    # Get all conversations for user
    conversations = conversation_service.get_user_conversations(current_user_id)

    # Count unread messages across all conversations
    unread_count = 0
    for conv in conversations:
        messages = message_service.get_conversation_messages(conv['id'])
        # Count messages where current user is NOT the sender and message is not read
        for msg in messages:
            if msg.get('sender_id') != current_user_id and not msg.get('is_read', False):
                unread_count += 1

    return jsonify({'unread_count': unread_count})
