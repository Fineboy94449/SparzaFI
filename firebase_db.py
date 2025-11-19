"""
Firebase Database Helper for SparzaFI
Replaces database_seed.py with Firebase Firestore operations
Provides backward-compatible wrappers for existing code migration
"""

from firebase_config import get_firestore_db
from firebase_service import (
    ProductService, OrderService, UserService,
    DeliveryService, NotificationService, StorageService
)
from google.cloud import firestore


# ==================== SERVICE INSTANCES ====================

# Singleton service instances
_user_service = None
_product_service = None
_order_service = None
_delivery_service = None
_notification_service = None
_storage_service = None


def get_user_service():
    """Get UserService instance"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service


def get_product_service():
    """Get ProductService instance"""
    global _product_service
    if _product_service is None:
        _product_service = ProductService()
    return _product_service


def get_order_service():
    """Get OrderService instance"""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service


def get_delivery_service():
    """Get DeliveryService instance"""
    global _delivery_service
    if _delivery_service is None:
        _delivery_service = DeliveryService()
    return _delivery_service


def get_notification_service():
    """Get NotificationService instance"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def get_storage_service():
    """Get StorageService instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


# ==================== BACKWARD COMPATIBILITY ====================

def get_db():
    """
    Get Firestore database client (replaces SQLite get_db())
    For backward compatibility during migration
    """
    return get_firestore_db()


def get_db_connection():
    """
    Get Firestore database client (replaces SQLite get_db_connection())
    For backward compatibility during migration
    """
    return get_firestore_db()


def init_db(app=None):
    """
    Initialize Firebase (replaces SQLite init_db())
    For backward compatibility during migration

    Note: Firebase doesn't need schema initialization like SQLite
    Collections are created automatically when documents are added
    """
    from firebase_config import initialize_firebase

    if app:
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT')
    else:
        service_account_path = None

    initialize_firebase(service_account_path)
    print("✓ Firebase initialized successfully")


# ==================== ADDITIONAL SERVICES ====================

class SellerService:
    """Seller-specific operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('sellers')

    def create(self, data, doc_id=None):
        """Create a seller profile"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, seller_id):
        """Get seller by ID"""
        doc = self.collection.document(seller_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_by_user_id(self, user_id):
        """Get seller by user_id"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        docs = self.collection.where(filter=FieldFilter('user_id', '==', user_id)).limit(1).stream()
        for doc in docs:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_by_handle(self, handle):
        """Get seller by handle"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        docs = self.collection.where(filter=FieldFilter('handle', '==', handle)).limit(1).stream()
        for doc in docs:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def update(self, seller_id, data):
        """Update seller"""
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        self.collection.document(seller_id).update(data)
        return True

    def get_all_sellers(self, limit=None, order_by='created_at'):
        """Get all sellers"""
        query = self.collection.order_by(order_by)
        if limit:
            query = query.limit(limit)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class ReviewService:
    """Review operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('reviews')

    def create(self, data, doc_id=None):
        """Create a review"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_product_reviews(self, product_id, limit=50):
        """Get reviews for a product"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('product_id', '==', product_id))
        # Note: Sorting in Python to avoid composite index requirement
        # query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        reviews = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort in Python instead of Firestore to avoid needing composite index
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Apply limit after sorting
        return reviews[:limit] if limit else reviews

    def get_seller_reviews(self, seller_id, limit=50):
        """Get reviews for a seller"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('seller_id', '==', seller_id))
        # Note: Sorting in Python to avoid composite index requirement
        # query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        reviews = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort in Python instead of Firestore to avoid needing composite index
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Apply limit after sorting
        return reviews[:limit] if limit else reviews


class TransactionService:
    """SPZ Token transaction operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('transactions')

    def create(self, data, doc_id=None):
        """Create a transaction"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['status'] = data.get('status', 'completed')

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_user_transactions(self, user_id, limit=100):
        """Get transactions for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        # Get transactions where user is sender or recipient
        query1 = self.collection.where(filter=FieldFilter('from_user_id', '==', user_id))
        query2 = self.collection.where(filter=FieldFilter('to_user_id', '==', user_id))

        transactions = []
        for doc in query1.stream():
            transactions.append({**doc.to_dict(), 'id': doc.id})
        for doc in query2.stream():
            transactions.append({**doc.to_dict(), 'id': doc.id})

        # Sort by created_at
        transactions.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return transactions[:limit] if limit else transactions


class WithdrawalService:
    """Withdrawal request operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('withdrawals')

    def create(self, data, doc_id=None):
        """Create a withdrawal request"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['status'] = data.get('status', 'pending')

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_user_withdrawals(self, user_id):
        """Get withdrawal requests for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('user_id', '==', user_id))
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def update_status(self, withdrawal_id, status, processed_by=None, rejection_reason=None):
        """Update withdrawal status"""
        update_data = {
            'status': status,
            'processed_at': firestore.SERVER_TIMESTAMP
        }

        if processed_by:
            update_data['processed_by'] = processed_by

        if rejection_reason:
            update_data['rejection_reason'] = rejection_reason

        self.collection.document(withdrawal_id).update(update_data)
        return True


class VideoService:
    """Video operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('videos')

    def create(self, data, doc_id=None):
        """Create a video"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, video_id):
        """Get video by ID"""
        doc = self.collection.document(video_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_seller_videos(self, seller_id):
        """Get videos for a seller ordered by video type"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('seller_id', '==', seller_id))
        query = query.where(filter=FieldFilter('is_active', '==', True))

        docs = query.stream()
        videos = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort by video type (intro, detailed, conclusion)
        video_type_order = {'intro': 1, 'detailed': 2, 'conclusion': 3}
        videos.sort(key=lambda v: video_type_order.get(v.get('video_type', 'detailed'), 2))

        return videos

    def increment_likes(self, video_id):
        """Increment video likes count"""
        self.collection.document(video_id).update({
            'likes_count': firestore.Increment(1)
        })

    def decrement_likes(self, video_id):
        """Decrement video likes count"""
        self.collection.document(video_id).update({
            'likes_count': firestore.Increment(-1)
        })


class FollowService:
    """Follow/unfollow operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('follows')

    def follow(self, user_id, seller_id):
        """Follow a seller"""
        doc_id = f"{user_id}_{seller_id}"
        self.collection.document(doc_id).set({
            'user_id': user_id,
            'seller_id': seller_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True

    def unfollow(self, user_id, seller_id):
        """Unfollow a seller"""
        doc_id = f"{user_id}_{seller_id}"
        self.collection.document(doc_id).delete()
        return True

    def is_following(self, user_id, seller_id):
        """Check if user is following seller"""
        doc_id = f"{user_id}_{seller_id}"
        doc = self.collection.document(doc_id).get()
        return doc.exists

    def get_user_follows(self, user_id):
        """Get all sellers that user follows"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('user_id', '==', user_id))
        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class LikeService:
    """Like operations for sellers and videos"""

    def __init__(self):
        self.db = get_firestore_db()
        self.seller_likes = self.db.collection('seller_likes')
        self.video_likes = self.db.collection('video_likes')

    def like_seller(self, user_id, seller_id):
        """Like a seller"""
        doc_id = f"{user_id}_{seller_id}"
        self.seller_likes.document(doc_id).set({
            'user_id': user_id,
            'seller_id': seller_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True

    def unlike_seller(self, user_id, seller_id):
        """Unlike a seller"""
        doc_id = f"{user_id}_{seller_id}"
        self.seller_likes.document(doc_id).delete()
        return True

    def is_seller_liked(self, user_id, seller_id):
        """Check if user has liked seller"""
        doc_id = f"{user_id}_{seller_id}"
        doc = self.seller_likes.document(doc_id).get()
        return doc.exists

    def like_video(self, user_id, video_id):
        """Like a video"""
        doc_id = f"{user_id}_{video_id}"
        self.video_likes.document(doc_id).set({
            'user_id': user_id,
            'video_id': video_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True

    def unlike_video(self, user_id, video_id):
        """Unlike a video"""
        doc_id = f"{user_id}_{video_id}"
        self.video_likes.document(doc_id).delete()
        return True

    def is_video_liked(self, user_id, video_id):
        """Check if user has liked video"""
        doc_id = f"{user_id}_{video_id}"
        doc = self.video_likes.document(doc_id).get()
        return doc.exists


class DeliveryTrackingService:
    """Delivery tracking operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('delivery_tracking')

    def create(self, data, doc_id=None):
        """Create a tracking event"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_transaction_tracking(self, transaction_id):
        """Get all tracking events for a transaction"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('transaction_id', '==', transaction_id))
        query = query.order_by('created_at')

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class ConversationService:
    """Conversation operations for chat"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('conversations')

    def create(self, data, doc_id=None):
        """Create a conversation"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['last_message_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, conversation_id):
        """Get conversation by ID"""
        doc = self.collection.document(conversation_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_user_conversations(self, user_id):
        """Get all conversations for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        # Get conversations where user is participant (user1 or user2)
        query1 = self.collection.where(filter=FieldFilter('user1_id', '==', user_id))
        query2 = self.collection.where(filter=FieldFilter('user2_id', '==', user_id))

        conversations = []
        for doc in query1.stream():
            conversations.append({**doc.to_dict(), 'id': doc.id})
        for doc in query2.stream():
            conversations.append({**doc.to_dict(), 'id': doc.id})

        # Also check by role-specific IDs (buyer_id, seller_id, deliverer_id)
        query3 = self.collection.where(filter=FieldFilter('buyer_id', '==', user_id))
        query4 = self.collection.where(filter=FieldFilter('seller_id', '==', user_id))
        query5 = self.collection.where(filter=FieldFilter('deliverer_id', '==', user_id))

        for doc in query3.stream():
            conv_dict = {**doc.to_dict(), 'id': doc.id}
            if conv_dict not in conversations:
                conversations.append(conv_dict)
        for doc in query4.stream():
            conv_dict = {**doc.to_dict(), 'id': doc.id}
            if conv_dict not in conversations:
                conversations.append(conv_dict)
        for doc in query5.stream():
            conv_dict = {**doc.to_dict(), 'id': doc.id}
            if conv_dict not in conversations:
                conversations.append(conv_dict)

        # Sort by last_message_at
        conversations.sort(key=lambda x: x.get('last_message_at', ''), reverse=True)
        return conversations

    def get_or_create_conversation(self, user1_id, user2_id, transaction_id=None, chat_type='buyer_seller'):
        """
        Get existing conversation or create new one

        Args:
            user1_id: First user ID
            user2_id: Second user ID
            transaction_id: Optional transaction ID for order-specific chats
            chat_type: Type of chat (buyer_seller, buyer_deliverer, seller_deliverer)
        """
        from google.cloud.firestore_v1.base_query import FieldFilter

        # For transaction-based chats, find by transaction_id
        if transaction_id:
            query = self.collection.where(filter=FieldFilter('transaction_id', '==', transaction_id))
            query = query.where(filter=FieldFilter('chat_type', '==', chat_type))

            for doc in query.stream():
                return {**doc.to_dict(), 'id': doc.id}

        # For general chats, find by user IDs
        query = self.collection.where(filter=FieldFilter('user1_id', '==', user1_id))
        query = query.where(filter=FieldFilter('user2_id', '==', user2_id))

        for doc in query.stream():
            # If no transaction_id specified, return any match
            if not transaction_id:
                return {**doc.to_dict(), 'id': doc.id}

        # Try reverse
        query = self.collection.where(filter=FieldFilter('user1_id', '==', user2_id))
        query = query.where(filter=FieldFilter('user2_id', '==', user1_id))

        for doc in query.stream():
            if not transaction_id:
                return {**doc.to_dict(), 'id': doc.id}

        # Create new conversation
        conversation_data = {
            'user1_id': user1_id,
            'user2_id': user2_id,
            'chat_type': chat_type,
        }

        if transaction_id:
            conversation_data['transaction_id'] = transaction_id

        conv_id = self.create(conversation_data)
        return self.get(conv_id)

    def get_transaction_conversations(self, transaction_id):
        """Get all conversations for a transaction"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('transaction_id', '==', transaction_id))
        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def update_last_message(self, conversation_id, message_preview=None):
        """Update last message timestamp and preview"""
        update_data = {'last_message_at': firestore.SERVER_TIMESTAMP}

        if message_preview:
            # Truncate to 50 chars for preview
            update_data['last_message'] = message_preview[:50]

        self.collection.document(conversation_id).update(update_data)


class MessageService:
    """
    Message operations for chat

    Supports transaction-based messaging with sender_role tracking.
    Messages include: conversation_id, sender_id, recipient_id, sender_role,
    transaction_id (optional), message_text, is_read, created_at
    """

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('messages')

    def create(self, data, doc_id=None):
        """
        Create a message with role tracking

        Args:
            data: Message data including sender_role (buyer/seller/deliverer)
            doc_id: Optional custom document ID

        Returns:
            Document ID
        """
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['is_read'] = data.get('is_read', False)

        # Ensure sender_role is set (defaults to 'buyer' if not provided)
        if 'sender_role' not in data:
            data['sender_role'] = 'buyer'

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_conversation_messages(self, conversation_id, limit=100):
        """Get all messages for a conversation"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('conversation_id', '==', conversation_id))
        # Note: Sorting in Python to avoid composite index requirement
        # query = query.order_by('created_at')

        docs = query.stream()
        messages = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort in Python instead of Firestore to avoid needing composite index
        messages.sort(key=lambda x: x.get('created_at', ''))

        # Apply limit after sorting
        return messages[:limit] if limit else messages

    def get_transaction_messages(self, transaction_id, limit=100):
        """Get all messages for a transaction (all chat types)"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('transaction_id', '==', transaction_id))

        docs = query.stream()
        messages = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort by created_at
        messages.sort(key=lambda x: x.get('created_at', ''))

        return messages[:limit] if limit else messages

    def mark_as_read(self, conversation_id, user_id):
        """Mark all messages in conversation as read for user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('conversation_id', '==', conversation_id))
        query = query.where(filter=FieldFilter('is_read', '==', False))

        batch = self.db.batch()
        for doc in query.stream():
            # Only mark as read if current user is not the sender
            if doc.to_dict().get('sender_id') != user_id:
                batch.update(doc.reference, {
                    'is_read': True,
                    'read_at': firestore.SERVER_TIMESTAMP
                })

        batch.commit()

    def get_unread_count(self, user_id):
        """Get count of unread messages for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('recipient_id', '==', user_id))
        query = query.where(filter=FieldFilter('is_read', '==', False))

        docs = query.stream()
        return sum(1 for _ in docs)

    def get_messages_by_sender_role(self, conversation_id, sender_role, limit=100):
        """
        Get messages filtered by sender_role (buyer/seller/deliverer)

        Args:
            conversation_id: Conversation ID
            sender_role: Role to filter by ('buyer', 'seller', 'deliverer')
            limit: Maximum number of messages to return

        Returns:
            List of messages from the specified role
        """
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('conversation_id', '==', conversation_id))
        query = query.where(filter=FieldFilter('sender_role', '==', sender_role))

        docs = query.stream()
        messages = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort by created_at
        messages.sort(key=lambda x: x.get('created_at', ''))

        return messages[:limit] if limit else messages


class DelivererService:
    """Deliverer operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('deliverers')

    def create(self, data, doc_id=None):
        """Create a deliverer profile"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, deliverer_id):
        """Get deliverer by ID"""
        doc = self.collection.document(deliverer_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_by_user_id(self, user_id):
        """Get deliverer by user_id"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        docs = self.collection.where(filter=FieldFilter('user_id', '==', user_id)).limit(1).stream()
        for doc in docs:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def update(self, deliverer_id, data):
        """Update deliverer"""
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        self.collection.document(deliverer_id).update(data)
        return True

    def get_all_deliverers(self, is_active=None, is_available=None):
        """Get all deliverers with optional filters"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection

        if is_active is not None:
            query = query.where(filter=FieldFilter('is_active', '==', is_active))

        if is_available is not None:
            query = query.where(filter=FieldFilter('is_available', '==', is_available))

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


class DeliveryRouteService:
    """Delivery route operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('delivery_routes')

    def create(self, data, doc_id=None):
        """Create a delivery route"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, route_id):
        """Get route by ID"""
        doc = self.collection.document(route_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_deliverer_routes(self, deliverer_id):
        """Get all routes for a deliverer"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('deliverer_id', '==', deliverer_id))
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def get_active_routes(self, deliverer_id=None):
        """Get active routes, optionally filtered by deliverer"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('is_active', '==', True))

        if deliverer_id:
            query = query.where(filter=FieldFilter('deliverer_id', '==', deliverer_id))

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def update(self, route_id, data):
        """Update route"""
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        self.collection.document(route_id).update(data)
        return True

    def delete(self, route_id):
        """Delete route"""
        self.collection.document(route_id).delete()
        return True


class VerificationSubmissionService:
    """Verification submission operations for admin"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('verification_submissions')

    def create(self, data, doc_id=None):
        """Create a verification submission"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['status'] = data.get('status', 'pending')

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, submission_id):
        """Get submission by ID"""
        doc = self.collection.document(submission_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def get_pending_submissions(self):
        """Get all pending verification submissions"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('status', '==', 'pending'))

        docs = query.stream()
        submissions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]
        # Sort by created_at in Python (avoids need for composite index)
        submissions.sort(key=lambda x: x.get('created_at') or '', reverse=False)
        return submissions

    def update_status(self, submission_id, status, reviewed_by=None):
        """Update verification status"""
        update_data = {
            'status': status,
            'reviewed_at': firestore.SERVER_TIMESTAMP
        }

        if reviewed_by:
            update_data['reviewed_by'] = reviewed_by

        self.collection.document(submission_id).update(update_data)
        return True


class SellerBadgeService:
    """Seller badge operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('seller_badges')

    def create(self, data, doc_id=None):
        """Create a seller badge"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_seller_badges(self, seller_id):
        """Get all badges for a seller"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('seller_id', '==', seller_id))

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def award_badge(self, seller_id, badge_name, badge_description=None):
        """Award a badge to a seller"""
        # Check if badge already exists
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('seller_id', '==', seller_id))
        query = query.where(filter=FieldFilter('badge_name', '==', badge_name))

        for doc in query.stream():
            return doc.id  # Badge already exists

        # Create new badge
        badge_data = {
            'seller_id': seller_id,
            'badge_name': badge_name,
            'badge_description': badge_description or badge_name
        }
        return self.create(badge_data)


class AddressService:
    """User address operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('addresses')

    def create(self, data, doc_id=None):
        """Create an address"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get_user_addresses(self, user_id):
        """Get all addresses for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('user_id', '==', user_id))
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def get(self, address_id):
        """Get address by ID"""
        doc = self.collection.document(address_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def update(self, address_id, data):
        """Update address"""
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        self.collection.document(address_id).update(data)
        return True

    def delete(self, address_id):
        """Delete address"""
        self.collection.document(address_id).delete()
        return True


class NotificationService:
    """Notification operations"""

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection('notifications')

    def create(self, user_id, data, doc_id=None):
        """Create a notification for a user"""
        import uuid
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        data['user_id'] = user_id
        data['is_read'] = data.get('is_read', False)
        data['created_at'] = data.get('created_at', firestore.SERVER_TIMESTAMP)

        self.collection.document(doc_id).set(data)
        return doc_id

    def create_notification(self, user_id, title, message, notification_type='general', data=None):
        """Create a notification (simplified method)"""
        notification_data = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'is_read': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        if data:
            notification_data['data'] = data

        return self.create(user_id, notification_data)

    def get_by_user(self, user_id, limit=50):
        """Get notifications for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('user_id', '==', user_id))
        # Sort in Python to avoid composite index requirement
        docs = query.stream()
        notifications = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort by created_at descending
        notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return notifications[:limit] if limit else notifications

    def mark_as_read(self, notification_id):
        """Mark a notification as read"""
        self.collection.document(notification_id).update({
            'is_read': True,
            'read_at': firestore.SERVER_TIMESTAMP
        })
        return True

    def mark_all_read(self, user_id):
        """Mark all notifications as read for a user"""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.collection.where(filter=FieldFilter('user_id', '==', user_id))
        query = query.where(filter=FieldFilter('is_read', '==', False))

        docs = query.stream()
        for doc in docs:
            doc.reference.update({
                'is_read': True,
                'read_at': firestore.SERVER_TIMESTAMP
            })

        return True

    def delete(self, notification_id):
        """Delete a notification"""
        self.collection.document(notification_id).delete()
        return True


# Create service instances
seller_service = SellerService()
review_service = ReviewService()
transaction_service = TransactionService()
withdrawal_service = WithdrawalService()
video_service = VideoService()
follow_service = FollowService()
like_service = LikeService()
delivery_tracking_service = DeliveryTrackingService()
conversation_service = ConversationService()
message_service = MessageService()
deliverer_service = DelivererService()
delivery_route_service = DeliveryRouteService()
verification_submission_service = VerificationSubmissionService()
seller_badge_service = SellerBadgeService()
address_service = AddressService()
notification_service = NotificationService()


# Export all services
__all__ = [
    'get_db',
    'get_db_connection',
    'init_db',
    'get_user_service',
    'get_product_service',
    'get_order_service',
    'get_delivery_service',
    'get_notification_service',
    'get_storage_service',
    'seller_service',
    'review_service',
    'transaction_service',
    'withdrawal_service',
    'video_service',
    'follow_service',
    'like_service',
    'delivery_tracking_service',
    'conversation_service',
    'message_service',
    'deliverer_service',
    'delivery_route_service',
    'verification_submission_service',
    'seller_badge_service',
    'address_service',
]
