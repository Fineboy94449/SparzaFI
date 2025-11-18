"""
Firebase Service Layer for SparzaFI
Provides high-level database operations using Firestore
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from firebase_config import get_firestore_db, get_storage_bucket
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
import uuid


class FirebaseService:
    """Base service class for Firestore operations"""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.db = get_firestore_db()
        self.collection = self.db.collection(collection_name)

    def create(self, data: Dict, doc_id: Optional[str] = None) -> str:
        """
        Create a new document

        Args:
            data: Document data
            doc_id: Optional custom document ID (generates UUID if not provided)

        Returns:
            Document ID
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        # Add timestamps
        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(doc_id).set(data)
        return doc_id

    def get(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID"""
        doc = self.collection.document(doc_id).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def update(self, doc_id: str, data: Dict) -> bool:
        """Update a document"""
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        self.collection.document(doc_id).update(data)
        return True

    def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        self.collection.document(doc_id).delete()
        return True

    def get_all(self, limit: Optional[int] = None, order_by: Optional[str] = None) -> List[Dict]:
        """Get all documents in collection"""
        query = self.collection

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def query(self, filters: List[tuple], limit: Optional[int] = None, order_by: Optional[str] = None) -> List[Dict]:
        """
        Query documents with filters

        Args:
            filters: List of (field, operator, value) tuples
                    e.g., [('status', '==', 'active'), ('price', '>=', 100)]
            limit: Maximum number of results
            order_by: Field to order by

        Returns:
            List of matching documents
        """
        query = self.collection

        for field, operator, value in filters:
            query = query.where(filter=FieldFilter(field, operator, value))

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def count(self, filters: Optional[List[tuple]] = None) -> int:
        """Count documents (with optional filters)"""
        if filters:
            docs = self.query(filters)
            return len(docs)
        else:
            docs = self.collection.stream()
            return sum(1 for _ in docs)


class ProductService(FirebaseService):
    """Product-specific operations"""

    def __init__(self):
        super().__init__('products')

    def get_active_products(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get active products, optionally filtered by category"""
        filters = [('status', '==', 'active')]

        if category:
            filters.append(('category', '==', category))

        # Query without ordering to avoid composite index requirement
        products = self.query(filters)
        # Sort in Python instead of Firestore
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return products[:limit] if limit else products

    def search_products(self, search_term: str, limit: int = 20) -> List[Dict]:
        """
        Search products by name
        Note: Firestore doesn't support full-text search natively.
        For production, use Algolia or Elasticsearch.
        """
        # This is a basic implementation - prefix search only
        search_term_lower = search_term.lower()

        all_products = self.get_all()
        results = [
            p for p in all_products
            if search_term_lower in p.get('name', '').lower() or
               search_term_lower in p.get('description', '').lower()
        ]

        return results[:limit]

    def get_seller_products(self, seller_id: str) -> List[Dict]:
        """Get all products for a seller"""
        # Query without ordering to avoid composite index requirement
        products = self.query([('seller_id', '==', seller_id)])
        # Sort in Python instead of Firestore
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return products

    def increment_views(self, product_id: str):
        """Increment product view count"""
        doc_ref = self.collection.document(product_id)
        doc_ref.update({
            'view_count': firestore.Increment(1)
        })


class OrderService(FirebaseService):
    """Order-specific operations"""

    def __init__(self):
        super().__init__('orders')

    def get_user_orders(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Get orders for a user"""
        filters = [('user_id', '==', user_id)]

        if status:
            filters.append(('status', '==', status))

        # Query without ordering to avoid composite index requirement
        orders = self.query(filters)
        # Sort in Python instead of Firestore
        orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return orders

    def get_seller_orders(self, seller_id: str, status: Optional[str] = None) -> List[Dict]:
        """Get orders for a seller"""
        filters = [('seller_id', '==', seller_id)]

        if status:
            filters.append(('status', '==', status))

        # Query without ordering to avoid composite index requirement
        orders = self.query(filters)
        # Sort in Python instead of Firestore
        orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return orders

    def update_order_status(self, order_id: str, new_status: str, updated_by: str) -> bool:
        """Update order status with history tracking"""
        order = self.get(order_id)
        if not order:
            return False

        # Add status to history
        status_history = order.get('status_history', [])
        status_history.append({
            'status': new_status,
            'timestamp': datetime.utcnow().isoformat(),
            'updated_by': updated_by
        })

        self.update(order_id, {
            'status': new_status,
            'status_history': status_history
        })

        return True


class UserService(FirebaseService):
    """User-specific operations"""

    def __init__(self):
        super().__init__('users')

    def get_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        results = self.query([('email', '==', email)], limit=1)
        return results[0] if results else None

    def get_by_phone(self, phone: str) -> Optional[Dict]:
        """Get user by phone"""
        results = self.query([('phone', '==', phone)], limit=1)
        return results[0] if results else None

    def update_spz_balance(self, user_id: str, amount: float, transaction_type: str):
        """Update user SPZ balance"""
        doc_ref = self.collection.document(user_id)

        if transaction_type == 'credit':
            doc_ref.update({
                'spz_balance': firestore.Increment(amount),
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        elif transaction_type == 'debit':
            doc_ref.update({
                'spz_balance': firestore.Increment(-amount),
                'updated_at': firestore.SERVER_TIMESTAMP
            })


class DeliveryService(FirebaseService):
    """Delivery tracking operations"""

    def __init__(self):
        super().__init__('deliveries')

    def get_active_deliveries(self, deliverer_id: str) -> List[Dict]:
        """Get active deliveries for a deliverer"""
        return self.query([
            ('deliverer_id', '==', deliverer_id),
            ('status', 'in', ['assigned', 'picked_up', 'in_transit'])
        ], order_by='created_at')

    def update_location(self, delivery_id: str, latitude: float, longitude: float):
        """Update delivery location (real-time tracking)"""
        self.update(delivery_id, {
            'current_location': {
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
        })

    def get_delivery_history(self, delivery_id: str) -> List[Dict]:
        """Get location history for a delivery"""
        doc = self.get(delivery_id)
        return doc.get('location_history', []) if doc else []


class NotificationService(FirebaseService):
    """Notification operations"""

    def __init__(self):
        super().__init__('notifications')

    def create_notification(self, user_id: str, title: str, message: str, notification_type: str, data: Optional[Dict] = None):
        """Create a notification for a user"""
        notification_data = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'read': False,
            'data': data or {}
        }

        return self.create(notification_data)

    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict]:
        """Get notifications for a user"""
        filters = [('user_id', '==', user_id)]

        if unread_only:
            filters.append(('read', '==', False))

        return self.query(filters, order_by='created_at', limit=50)

    def mark_as_read(self, notification_id: str):
        """Mark notification as read"""
        self.update(notification_id, {'read': True})

    def mark_all_read(self, user_id: str):
        """Mark all user notifications as read"""
        notifications = self.get_user_notifications(user_id, unread_only=True)

        batch = self.db.batch()
        for notif in notifications:
            doc_ref = self.collection.document(notif['id'])
            batch.update(doc_ref, {'read': True, 'updated_at': firestore.SERVER_TIMESTAMP})

        batch.commit()


class StorageService:
    """Firebase Storage operations"""

    def __init__(self):
        self.bucket = get_storage_bucket()

    def upload_file(self, file_path: str, destination_path: str, content_type: Optional[str] = None) -> str:
        """
        Upload a file to Firebase Storage

        Args:
            file_path: Local file path
            destination_path: Path in Firebase Storage (e.g., 'products/image.jpg')
            content_type: MIME type

        Returns:
            Public URL of uploaded file
        """
        blob = self.bucket.blob(destination_path)

        if content_type:
            blob.upload_from_filename(file_path, content_type=content_type)
        else:
            blob.upload_from_filename(file_path)

        # Make public
        blob.make_public()

        return blob.public_url

    def upload_from_string(self, content: str, destination_path: str, content_type: str = 'text/plain') -> str:
        """Upload content from string"""
        blob = self.bucket.blob(destination_path)
        blob.upload_from_string(content, content_type=content_type)
        blob.make_public()
        return blob.public_url

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from Firebase Storage"""
        blob = self.bucket.blob(file_path)
        blob.delete()
        return True

    def get_file_url(self, file_path: str) -> str:
        """Get public URL for a file"""
        blob = self.bucket.blob(file_path)
        return blob.public_url


# Singleton instances for easy import
product_service = ProductService()
order_service = OrderService()
user_service = UserService()
delivery_service = DeliveryService()
notification_service = NotificationService()
storage_service = StorageService()
