"""
SparzaFI Transaction Explorer Service

Comprehensive transaction management with:
- Unique transaction codes (SPZ-TXID-HASH-TIMESTAMP)
- Immutable timestamps
- Integrity hashing
- Verification logging
- Role-based access control
"""

import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from google.cloud import firestore
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter


class TransactionExplorerService:
    """
    Comprehensive transaction explorer with full security and tracking
    """

    def __init__(self):
        self.db = get_firestore_db()
        self.transactions = self.db.collection('transactions')
        self.verification_logs = self.db.collection('verification_logs')

    # ==================== TRANSACTION CODE GENERATION ====================

    def generate_transaction_code(self, transaction_id: str, timestamp: str) -> str:
        """
        Generate unique transaction code: SPZ-<TX-ID>-<8-digit-hash>-<timestamp-fragment>

        Args:
            transaction_id: Unique transaction ID
            timestamp: ISO timestamp string

        Returns:
            Transaction code (e.g., SPZ-000145-AF94B21C-20251119)
        """
        # Extract numeric ID (try to parse or use hash)
        try:
            # If transaction_id contains numbers, extract them
            numeric_id = ''.join(filter(str.isdigit, transaction_id))
            if not numeric_id:
                # If no numbers, use hash
                numeric_id = str(int(hashlib.md5(transaction_id.encode()).hexdigest()[:6], 16))
            tx_num = str(int(numeric_id[-6:])).zfill(6)
        except:
            # Fallback: use random 6 digits
            tx_num = str(int(hashlib.md5(transaction_id.encode()).hexdigest()[:6], 16))[:6].zfill(6)

        # Generate 8-digit hash from transaction_id + timestamp
        hash_input = f"{transaction_id}{timestamp}".encode()
        hash_8digit = hashlib.sha256(hash_input).hexdigest()[:8].upper()

        # Extract date fragment from timestamp (YYYYMMDD)
        try:
            if 'T' in timestamp:
                date_part = timestamp.split('T')[0].replace('-', '')[:8]
            else:
                date_part = datetime.utcnow().strftime('%Y%m%d')
        except:
            date_part = datetime.utcnow().strftime('%Y%m%d')

        return f"SPZ-{tx_num}-{hash_8digit}-{date_part}"

    def generate_transaction_hash(self, transaction_data: Dict) -> str:
        """
        Generate integrity hash for transaction

        Args:
            transaction_data: Transaction dictionary

        Returns:
            SHA-256 hash hex string
        """
        # Create hash from critical fields
        hash_components = [
            str(transaction_data.get('id', '')),
            str(transaction_data.get('user_id', '')),
            str(transaction_data.get('seller_id', '')),
            str(transaction_data.get('total_amount', '')),
            str(transaction_data.get('timestamp', '')),
        ]

        hash_string = '|'.join(hash_components)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def generate_pickup_code(self, transaction_id: str) -> str:
        """Generate 6-digit pickup code"""
        hash_input = f"PICKUP-{transaction_id}-{datetime.utcnow().isoformat()}".encode()
        code = hashlib.sha256(hash_input).hexdigest()[:6].upper()
        return code

    def generate_delivery_code(self, transaction_id: str) -> str:
        """Generate 6-digit delivery code"""
        hash_input = f"DELIVERY-{transaction_id}-{datetime.utcnow().isoformat()}".encode()
        code = hashlib.sha256(hash_input).hexdigest()[:6].upper()
        return code

    # ==================== TRANSACTION CREATION & UPDATE ====================

    def create_transaction_with_metadata(self, transaction_data: Dict) -> str:
        """
        Create transaction with full metadata (code, hash, timestamp)

        Args:
            transaction_data: Transaction data dictionary

        Returns:
            Transaction ID
        """
        # Generate transaction ID if not provided
        transaction_id = transaction_data.get('id', str(uuid.uuid4()))

        # Generate timestamp
        timestamp = datetime.utcnow().isoformat()

        # Add metadata
        transaction_data['id'] = transaction_id
        transaction_data['timestamp'] = timestamp
        transaction_data['created_at'] = firestore.SERVER_TIMESTAMP
        transaction_data['immutable_timestamp'] = None  # Set when completed
        transaction_data['timestamp_locked'] = False

        # Generate transaction code
        transaction_data['transaction_code'] = self.generate_transaction_code(transaction_id, timestamp)

        # Generate integrity hash
        transaction_data['transaction_hash'] = self.generate_transaction_hash(transaction_data)

        # Generate pickup and delivery codes
        transaction_data['pickup_code'] = self.generate_pickup_code(transaction_id)
        transaction_data['delivery_code'] = self.generate_delivery_code(transaction_id)

        # Initialize verification logs array
        transaction_data['verification_logs'] = []

        # Initialize status history
        if 'status_history' not in transaction_data:
            transaction_data['status_history'] = []

        # Save to Firestore
        self.transactions.document(transaction_id).set(transaction_data)

        # Log creation
        self.log_verification(
            transaction_id=transaction_id,
            action='TRANSACTION_CREATED',
            user_id=transaction_data.get('user_id', 'system'),
            details={'status': transaction_data.get('status', 'pending')}
        )

        return transaction_id

    def lock_timestamp(self, transaction_id: str) -> bool:
        """
        Lock timestamp permanently (called when transaction is completed)

        Args:
            transaction_id: Transaction ID

        Returns:
            Success boolean
        """
        transaction_ref = self.transactions.document(transaction_id)
        transaction = transaction_ref.get()

        if not transaction.exists:
            return False

        data = transaction.to_dict()

        # Only lock if not already locked
        if data.get('timestamp_locked'):
            return False

        # Set immutable timestamp and lock it
        immutable_timestamp = datetime.utcnow().isoformat()

        transaction_ref.update({
            'immutable_timestamp': immutable_timestamp,
            'timestamp_locked': True,
            'locked_at': firestore.SERVER_TIMESTAMP
        })

        # Log the lock
        self.log_verification(
            transaction_id=transaction_id,
            action='TIMESTAMP_LOCKED',
            user_id='system',
            details={'immutable_timestamp': immutable_timestamp}
        )

        return True

    # ==================== VERIFICATION LOGGING ====================

    def log_verification(self, transaction_id: str, action: str, user_id: str,
                        details: Optional[Dict] = None, ip_address: Optional[str] = None) -> str:
        """
        Log verification action for audit trail

        Args:
            transaction_id: Transaction ID
            action: Action type (PICKUP_VERIFIED, DELIVERY_VERIFIED, etc.)
            user_id: User who performed action
            details: Additional details
            ip_address: IP address (optional)

        Returns:
            Log entry ID
        """
        log_id = str(uuid.uuid4())
        timestamp_iso = datetime.utcnow().isoformat()

        # Create log data for verification_logs collection (with SERVER_TIMESTAMP)
        log_data_for_collection = {
            'id': log_id,
            'transaction_id': transaction_id,
            'action': action,
            'user_id': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'timestamp_iso': timestamp_iso,
            'details': details or {},
        }

        if ip_address:
            log_data_for_collection['ip_address'] = ip_address

        # Create log data for transaction array (without SERVER_TIMESTAMP - use ISO string instead)
        log_data_for_array = {
            'id': log_id,
            'transaction_id': transaction_id,
            'action': action,
            'user_id': user_id,
            'timestamp_iso': timestamp_iso,
            'details': details or {},
        }

        if ip_address:
            log_data_for_array['ip_address'] = ip_address

        # Save to verification_logs collection
        self.verification_logs.document(log_id).set(log_data_for_collection)

        # Also append to transaction's verification_logs array (using ISO timestamp)
        transaction_ref = self.transactions.document(transaction_id)
        transaction_ref.update({
            'verification_logs': firestore.ArrayUnion([log_data_for_array])
        })

        return log_id

    def verify_pickup_code(self, transaction_id: str, code: str, user_id: str,
                          ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify pickup code

        Args:
            transaction_id: Transaction ID
            code: Pickup code entered by driver
            user_id: Driver user ID
            ip_address: IP address

        Returns:
            (success, message) tuple
        """
        transaction_ref = self.transactions.document(transaction_id)
        transaction = transaction_ref.get()

        if not transaction.exists:
            return False, "Transaction not found"

        data = transaction.to_dict()
        correct_code = data.get('pickup_code')

        if not correct_code:
            return False, "No pickup code set"

        if code.upper() == correct_code.upper():
            # Code is correct - log success
            self.log_verification(
                transaction_id=transaction_id,
                action='PICKUP_VERIFIED',
                user_id=user_id,
                details={'code': code, 'result': 'success'},
                ip_address=ip_address
            )

            # Update transaction status
            transaction_ref.update({
                'status': 'PICKED_UP',
                'pickup_verified_at': firestore.SERVER_TIMESTAMP,
                'pickup_verified_by': user_id
            })

            return True, "Pickup verified successfully"
        else:
            # Code is incorrect - log failure
            self.log_verification(
                transaction_id=transaction_id,
                action='PICKUP_VERIFICATION_FAILED',
                user_id=user_id,
                details={'code_entered': code, 'result': 'failed'},
                ip_address=ip_address
            )

            return False, "Invalid pickup code"

    def verify_delivery_code(self, transaction_id: str, code: str, user_id: str,
                            ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify delivery code

        Args:
            transaction_id: Transaction ID
            code: Delivery code entered by buyer
            user_id: Buyer user ID
            ip_address: IP address

        Returns:
            (success, message) tuple
        """
        transaction_ref = self.transactions.document(transaction_id)
        transaction = transaction_ref.get()

        if not transaction.exists:
            return False, "Transaction not found"

        data = transaction.to_dict()
        correct_code = data.get('delivery_code')

        if not correct_code:
            return False, "No delivery code set"

        if code.upper() == correct_code.upper():
            # Code is correct - log success
            self.log_verification(
                transaction_id=transaction_id,
                action='DELIVERY_VERIFIED',
                user_id=user_id,
                details={'code': code, 'result': 'success'},
                ip_address=ip_address
            )

            # Update transaction status and lock timestamp
            transaction_ref.update({
                'status': 'DELIVERED',
                'delivery_verified_at': firestore.SERVER_TIMESTAMP,
                'delivery_verified_by': user_id
            })

            # Lock timestamp when delivery is complete
            self.lock_timestamp(transaction_id)

            return True, "Delivery verified successfully"
        else:
            # Code is incorrect - log failure
            self.log_verification(
                transaction_id=transaction_id,
                action='DELIVERY_VERIFICATION_FAILED',
                user_id=user_id,
                details={'code_entered': code, 'result': 'failed'},
                ip_address=ip_address
            )

            return False, "Invalid delivery code"

    # ==================== TRANSACTION QUERIES ====================

    def get_transaction_by_code(self, transaction_code: str) -> Optional[Dict]:
        """
        Get transaction by transaction code

        Args:
            transaction_code: Transaction code (SPZ-XXXXXX-XXXXXXXX-YYYYMMDD)

        Returns:
            Transaction dict or None
        """
        query = self.transactions.where(
            filter=FieldFilter('transaction_code', '==', transaction_code)
        ).limit(1)

        for doc in query.stream():
            return {**doc.to_dict(), 'id': doc.id}

        return None

    def search_seller_transactions(self, seller_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search transactions for a seller with filters

        Filters:
            - transaction_code: str
            - buyer_address: str (partial match)
            - date_start: str (ISO date)
            - date_end: str (ISO date)
            - status: str
            - payment_method: str
            - limit: int (default 50)
        """
        # Base query
        query = self.transactions.where(filter=FieldFilter('seller_id', '==', seller_id))

        filters = filters or {}

        # Apply status filter
        if filters.get('status'):
            query = query.where(filter=FieldFilter('status', '==', filters['status']))

        # Apply payment method filter
        if filters.get('payment_method'):
            query = query.where(filter=FieldFilter('payment_method', '==', filters['payment_method']))

        # Get results
        docs = query.stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Apply Python-side filters (to avoid composite indexes)
        if filters.get('transaction_code'):
            transactions = [
                t for t in transactions
                if filters['transaction_code'].upper() in t.get('transaction_code', '').upper()
            ]

        if filters.get('buyer_address'):
            transactions = [
                t for t in transactions
                if filters['buyer_address'].lower() in t.get('delivery_address', '').lower()
            ]

        if filters.get('date_start'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') >= filters['date_start']
            ]

        if filters.get('date_end'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') <= filters['date_end']
            ]

        # Sort by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply limit
        limit = filters.get('limit', 50)
        return transactions[:limit]

    def search_buyer_transactions(self, buyer_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search transactions for a buyer with filters

        Filters:
            - transaction_code: str
            - date_start: str (ISO date)
            - date_end: str (ISO date)
            - status: str
            - delivery_method: str
            - seller_name: str
            - limit: int (default 50)
        """
        # Base query
        query = self.transactions.where(filter=FieldFilter('user_id', '==', buyer_id))

        filters = filters or {}

        # Apply status filter
        if filters.get('status'):
            query = query.where(filter=FieldFilter('status', '==', filters['status']))

        # Apply delivery method filter
        if filters.get('delivery_method'):
            query = query.where(filter=FieldFilter('delivery_method', '==', filters['delivery_method']))

        # Get results
        docs = query.stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Apply Python-side filters
        if filters.get('transaction_code'):
            transactions = [
                t for t in transactions
                if filters['transaction_code'].upper() in t.get('transaction_code', '').upper()
            ]

        if filters.get('seller_name'):
            transactions = [
                t for t in transactions
                if filters['seller_name'].lower() in t.get('seller_name', '').lower()
            ]

        if filters.get('date_start'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') >= filters['date_start']
            ]

        if filters.get('date_end'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') <= filters['date_end']
            ]

        # Sort by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply limit
        limit = filters.get('limit', 50)
        return transactions[:limit]

    def search_driver_transactions(self, driver_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search transactions for a driver/deliverer with filters

        Filters:
            - transaction_code: str
            - date_start: str (ISO date)
            - date_end: str (ISO date)
            - seller_name: str
            - status: str
            - limit: int (default 50)
        """
        # Base query
        query = self.transactions.where(filter=FieldFilter('deliverer_id', '==', driver_id))

        filters = filters or {}

        # Apply status filter
        if filters.get('status'):
            query = query.where(filter=FieldFilter('status', '==', filters['status']))

        # Get results
        docs = query.stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Apply Python-side filters
        if filters.get('transaction_code'):
            transactions = [
                t for t in transactions
                if filters['transaction_code'].upper() in t.get('transaction_code', '').upper()
            ]

        if filters.get('seller_name'):
            transactions = [
                t for t in transactions
                if filters['seller_name'].lower() in t.get('seller_name', '').lower()
            ]

        if filters.get('date_start'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') >= filters['date_start']
            ]

        if filters.get('date_end'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') <= filters['date_end']
            ]

        # Sort by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply limit
        limit = filters.get('limit', 50)
        return transactions[:limit]

    def search_admin_transactions(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search ALL transactions (admin access) with advanced filters

        Filters:
            - transaction_code: str
            - transaction_id: str
            - driver_id: str
            - seller_id: str
            - buyer_id: str
            - date_start: str (ISO date)
            - date_end: str (ISO date)
            - delivery_method: str
            - payment_method: str
            - status: str
            - seller_name: str
            - buyer_email: str
            - driver_email: str
            - limit: int (default 100)
        """
        filters = filters or {}

        # Start with base query or filtered query
        query = self.transactions

        # Apply Firestore filters where possible
        if filters.get('seller_id'):
            query = query.where(filter=FieldFilter('seller_id', '==', filters['seller_id']))
        elif filters.get('buyer_id'):
            query = query.where(filter=FieldFilter('user_id', '==', filters['buyer_id']))
        elif filters.get('driver_id'):
            query = query.where(filter=FieldFilter('deliverer_id', '==', filters['driver_id']))
        elif filters.get('status'):
            query = query.where(filter=FieldFilter('status', '==', filters['status']))
        elif filters.get('payment_method'):
            query = query.where(filter=FieldFilter('payment_method', '==', filters['payment_method']))

        # Get all matching documents
        docs = query.stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Apply Python-side filters
        if filters.get('transaction_code'):
            transactions = [
                t for t in transactions
                if filters['transaction_code'].upper() in t.get('transaction_code', '').upper()
            ]

        if filters.get('transaction_id'):
            transactions = [
                t for t in transactions
                if filters['transaction_id'] in t.get('id', '')
            ]

        if filters.get('date_start'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') >= filters['date_start']
            ]

        if filters.get('date_end'):
            transactions = [
                t for t in transactions
                if t.get('timestamp', '') <= filters['date_end']
            ]

        # Sort by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply limit
        limit = filters.get('limit', 100)
        return transactions[:limit]

    def get_public_transactions(self, limit: int = 50) -> List[Dict]:
        """
        Get anonymized transactions for public explorer

        Returns transactions with:
        - Hashed buyer ID (e.g., Buyer-003)
        - Transaction hash
        - Timestamp
        - Amount
        - Delivery method
        - Status

        NOT visible:
        - Addresses
        - User details
        - Pickup or delivery codes
        """
        # Get recent completed transactions
        query = self.transactions.where(
            filter=FieldFilter('status', '==', 'COMPLETED')
        ).limit(limit)

        docs = query.stream()
        transactions = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Anonymize data
        public_transactions = []
        for t in transactions:
            # Create anonymized version
            public_tx = {
                'transaction_hash': t.get('transaction_hash', ''),
                'timestamp': t.get('immutable_timestamp') or t.get('timestamp', ''),
                'amount': t.get('total_amount', 0),
                'delivery_method': t.get('delivery_method', 'unknown'),
                'status': t.get('status', 'unknown'),
                'buyer_id_hash': hashlib.md5(str(t.get('user_id', '')).encode()).hexdigest()[:8],
                'seller_id_hash': hashlib.md5(str(t.get('seller_id', '')).encode()).hexdigest()[:8],
            }
            public_transactions.append(public_tx)

        # Sort by timestamp
        public_transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return public_transactions

    def get_transaction_verification_logs(self, transaction_id: str) -> List[Dict]:
        """
        Get all verification logs for a transaction

        Args:
            transaction_id: Transaction ID

        Returns:
            List of verification log entries
        """
        query = self.verification_logs.where(
            filter=FieldFilter('transaction_id', '==', transaction_id)
        )

        docs = query.stream()
        logs = [{**doc.to_dict(), 'id': doc.id} for doc in docs]

        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp_iso', ''))

        return logs


# Create singleton instance
_transaction_explorer_service = None

def get_transaction_explorer_service() -> TransactionExplorerService:
    """Get singleton instance of TransactionExplorerService"""
    global _transaction_explorer_service
    if _transaction_explorer_service is None:
        _transaction_explorer_service = TransactionExplorerService()
    return _transaction_explorer_service
