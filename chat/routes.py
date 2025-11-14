"""
Chat Routes - API endpoints for messaging functionality
"""
from flask import request, jsonify, session, g
from datetime import datetime
from . import chat_bp
from database_seed import get_db_connection
import sqlite3


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

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all conversations where user is participant
    cursor.execute("""
        SELECT DISTINCT c.id, c.user1_id, c.user2_id, c.last_message_at, c.created_at,
               CASE
                   WHEN c.user1_id = ? THEN u2.email
                   ELSE u1.email
               END as other_user_email,
               CASE
                   WHEN c.user1_id = ? THEN c.user2_id
                   ELSE c.user1_id
               END as other_user_id
        FROM conversations c
        LEFT JOIN users u1 ON c.user1_id = u1.id
        LEFT JOIN users u2 ON c.user2_id = u2.id
        WHERE c.user1_id = ? OR c.user2_id = ?
        ORDER BY c.last_message_at DESC, c.created_at DESC
    """, (current_user_id, current_user_id, current_user_id, current_user_id))

    conversations = cursor.fetchall()
    conn.close()

    result = []
    for conv in conversations:
        result.append({
            'id': conv['id'],
            'other_user_email': conv['other_user_email'],
            'other_user_id': conv['other_user_id'],
            'last_message_at': conv['last_message_at'],
            'created_at': conv['created_at']
        })

    return jsonify(result)


@chat_bp.route('/conversations/<int:conversation_id>/messages', methods=['GET'])
@require_auth
def get_messages(conversation_id):
    """Get all messages for a specific conversation"""
    current_user_id = session['user']['id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify user is part of this conversation
    cursor.execute("""
        SELECT id FROM conversations
        WHERE id = ? AND (user1_id = ? OR user2_id = ?)
    """, (conversation_id, current_user_id, current_user_id))

    conversation = cursor.fetchone()
    if not conversation:
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403

    # Get all messages in this conversation
    cursor.execute("""
        SELECT m.id, m.sender_id, m.message_text, m.created_at, m.is_read,
               u.email as sender_email
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.conversation_id = ?
        ORDER BY m.created_at ASC
    """, (conversation_id,))

    messages = cursor.fetchall()

    # Mark messages as read
    cursor.execute("""
        UPDATE messages
        SET is_read = 1, read_at = CURRENT_TIMESTAMP
        WHERE conversation_id = ? AND recipient_id = ? AND is_read = 0
    """, (conversation_id, current_user_id))

    conn.commit()
    conn.close()

    result = []
    for msg in messages:
        result.append({
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'sender_email': msg['sender_email'],
            'content': msg['message_text'],
            'timestamp': msg['created_at'],
            'is_read': bool(msg['is_read'])
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

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify recipient exists
    cursor.execute("SELECT id FROM users WHERE id = ?", (recipient_id,))
    recipient = cursor.fetchone()
    if not recipient:
        conn.close()
        return jsonify({'error': 'Recipient not found'}), 404

    # Find or create conversation (always store with lower ID as user1)
    user1_id = min(current_user_id, recipient_id)
    user2_id = max(current_user_id, recipient_id)

    cursor.execute("""
        SELECT id FROM conversations
        WHERE user1_id = ? AND user2_id = ?
    """, (user1_id, user2_id))

    conversation = cursor.fetchone()

    if not conversation:
        # Create new conversation
        cursor.execute("""
            INSERT INTO conversations (user1_id, user2_id, last_message_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user1_id, user2_id))
        conversation_id = cursor.lastrowid
    else:
        conversation_id = conversation['id']
        # Update last_message_at
        cursor.execute("""
            UPDATE conversations
            SET last_message_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (conversation_id,))

    # Create message
    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_id, recipient_id, message_text, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (conversation_id, current_user_id, recipient_id, content))

    message_id = cursor.lastrowid

    # Create notification for recipient
    cursor.execute("""
        INSERT INTO notifications (user_id, title, message, notification_type, related_id, created_at)
        VALUES (?, 'New Message', ?, 'message', ?, CURRENT_TIMESTAMP)
    """, (recipient_id, f'You have a new message from {session["user"]["email"]}', conversation_id))

    conn.commit()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM messages
        WHERE recipient_id = ? AND is_read = 0
    """, (current_user_id,))

    result = cursor.fetchone()
    conn.close()

    return jsonify({'unread_count': result['count']})
