"""
Firebase-based Chat Utilities
Wrapper functions for chat functionality using Firebase services
"""

from firebase_db import conversation_service, message_service, get_product_service, seller_service
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore


def can_user_access_chat(user_id, conversation_id):
    """
    Check if user has access to a conversation
    Returns: Boolean
    """
    conversation = conversation_service.get(conversation_id)

    if not conversation:
        return False

    # Check if user is a participant
    return user_id in [conversation.get('user1_id'), conversation.get('user2_id')]


def get_chat_messages(conversation_id, limit=100):
    """
    Get all messages for a conversation
    Returns: List of message dictionaries
    """
    messages = message_service.get_conversation_messages(conversation_id, limit=limit)
    return messages


def get_unread_count(user_id, conversation_id=None):
    """
    Get count of unread messages for a user
    If conversation_id is provided, get count for that conversation only
    Returns: Integer count
    """
    db = get_firestore_db()
    messages_ref = db.collection('messages')

    if conversation_id:
        # Get unread count for specific conversation
        query = messages_ref.where(filter=FieldFilter('conversation_id', '==', conversation_id)) \
                           .where(filter=FieldFilter('is_read', '==', False))

        count = 0
        for doc in query.stream():
            msg = doc.to_dict()
            # Only count if current user is not the sender
            if msg.get('sender_id') != user_id:
                count += 1
        return count
    else:
        # Get total unread count across all conversations
        # First get all user's conversations
        conversations = conversation_service.get_user_conversations(user_id)

        total_unread = 0
        for conv in conversations:
            conv_id = conv.get('id')
            query = messages_ref.where(filter=FieldFilter('conversation_id', '==', conv_id)) \
                               .where(filter=FieldFilter('is_read', '==', False))

            for doc in query.stream():
                msg = doc.to_dict()
                # Only count if current user is not the sender
                if msg.get('sender_id') != user_id:
                    total_unread += 1

        return total_unread


def mark_messages_as_read(conversation_id, user_id):
    """
    Mark all messages in a conversation as read for the user
    Returns: Success boolean
    """
    try:
        message_service.mark_as_read(conversation_id, user_id)
        return True
    except Exception as e:
        print(f"Error marking messages as read: {e}")
        return False


def send_chat_message(conversation_id, sender_id, message_text, message_type='text', metadata=None):
    """
    Send a chat message
    Returns: Message ID
    """
    message_data = {
        'conversation_id': conversation_id,
        'sender_id': sender_id,
        'message': message_text,
        'message_type': message_type,
        'metadata': metadata or {},
        'is_read': False
    }

    message_id = message_service.create(message_data)

    # Update conversation's last message timestamp
    conversation_service.update_last_message(conversation_id)

    return message_id


def send_system_message(conversation_id, message_text):
    """
    Send a system message to conversation
    Returns: Message ID
    """
    return send_chat_message(
        conversation_id=conversation_id,
        sender_id='system',
        message_text=message_text,
        message_type='system'
    )


def flag_message(message_id, flagged_by, reason=''):
    """
    Flag a message for moderation
    Returns: Success boolean
    """
    db = get_firestore_db()

    try:
        message_ref = db.collection('messages').document(message_id)
        message = message_ref.get()

        if not message.exists:
            return False

        message_ref.update({
            'is_flagged': True,
            'flagged_by': flagged_by,
            'flag_reason': reason,
            'flagged_at': firestore.SERVER_TIMESTAMP
        })

        return True
    except Exception as e:
        print(f"Error flagging message: {e}")
        return False


def get_user_active_chats(user_id):
    """
    Get all active conversations for a user with enriched data
    Returns: List of conversation dictionaries with participant info and last message
    """
    conversations = conversation_service.get_user_conversations(user_id)

    enriched_conversations = []
    for conv in conversations:
        # Get the other participant's ID
        other_user_id = conv.get('user2_id') if conv.get('user1_id') == user_id else conv.get('user1_id')

        # Try to get participant info (could be seller, deliverer, or regular user)
        participant_name = 'Unknown'
        participant_type = 'user'

        # Check if it's a seller
        seller = seller_service.get(other_user_id)
        if seller:
            participant_name = seller.get('name', 'Seller')
            participant_type = 'seller'
        else:
            # Could add more checks for deliverers, etc.
            participant_name = other_user_id[:8] + '...'  # Fallback to truncated ID

        # Get last message
        messages = message_service.get_conversation_messages(conv.get('id'), limit=1)
        last_message = messages[-1] if messages else None

        # Get unread count for this conversation
        unread_count = get_unread_count(user_id, conv.get('id'))

        enriched_conversations.append({
            **conv,
            'other_user_id': other_user_id,
            'participant_name': participant_name,
            'participant_type': participant_type,
            'last_message': last_message,
            'unread_count': unread_count
        })

    return enriched_conversations


def create_product_inquiry_chat(buyer_id, seller_id, product_id):
    """
    Create a chat conversation for product inquiry
    Returns: Conversation ID
    """
    product_service = get_product_service()

    # Get or create conversation between buyer and seller
    conversation = conversation_service.get_or_create_conversation(buyer_id, seller_id)
    conversation_id = conversation.get('id')

    # Get product details
    product = product_service.get(product_id)
    product_name = product.get('name', 'Product') if product else 'Product'

    # Send initial system message about the product
    send_system_message(
        conversation_id,
        f"Chat started about: {product_name}"
    )

    return conversation_id


def get_conversation_participants(conversation_id):
    """
    Get participant IDs from a conversation
    Returns: dict with user1_id and user2_id
    """
    conversation = conversation_service.get(conversation_id)

    if not conversation:
        return None

    return {
        'user1_id': conversation.get('user1_id'),
        'user2_id': conversation.get('user2_id')
    }
