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
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def get_seller_reviews(self, seller_id, limit=50):
        """Get reviews for a seller"""
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter('seller_id', '==', seller_id))
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


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


# Create service instances
seller_service = SellerService()
review_service = ReviewService()
transaction_service = TransactionService()
withdrawal_service = WithdrawalService()


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
]
