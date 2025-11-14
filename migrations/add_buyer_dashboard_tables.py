"""
Buyer Dashboard Database Migration
Adds tables for: buyer addresses, return requests, and security action logs
"""

import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_seed import get_db_connection

def migrate():
    """Run migration to add buyer dashboard tables"""
    conn = get_db_connection()

    try:
        # 1. Buyer Addresses Table (for multiple delivery addresses)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS buyer_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                label TEXT NOT NULL,  -- 'Home', 'Work', 'Other'
                full_address TEXT NOT NULL,
                city TEXT,
                postal_code TEXT,
                phone_number TEXT,
                delivery_instructions TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # 2. Return Requests Table (for return & refund management)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS return_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                reason TEXT NOT NULL,  -- 'damaged', 'wrong_item', 'not_as_described', 'other'
                description TEXT,
                images TEXT,  -- JSON array of evidence images
                status TEXT DEFAULT 'PENDING' CHECK(status IN (
                    'PENDING', 'APPROVED', 'REJECTED', 'PICKUP_SCHEDULED',
                    'PICKED_UP', 'REFUND_PROCESSED', 'COMPLETED'
                )),
                refund_amount REAL,
                admin_notes TEXT,
                pickup_scheduled_at DATETIME,
                picked_up_at DATETIME,
                refund_processed_at DATETIME,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (seller_id) REFERENCES sellers (id)
            )
        """)

        # 3. Security Action Logs (for two-step confirmation tracking)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS buyer_security_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,  -- 'generate_code', 'approve_return', 'edit_profile'
                action_data TEXT,  -- JSON data related to the action
                ip_address TEXT,
                user_agent TEXT,
                confirmation_code TEXT,  -- 6-digit OTP for sensitive actions
                confirmed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 4. Add indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_buyer_addresses_user ON buyer_addresses(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_return_requests_transaction ON return_requests(transaction_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_return_requests_user ON return_requests(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_return_requests_status ON return_requests(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_actions_user ON buyer_security_actions(user_id)")

        conn.commit()
        print("✅ Buyer dashboard tables created successfully!")

        # Verify tables were created
        tables = ['buyer_addresses', 'return_requests', 'buyer_security_actions']
        for table in tables:
            result = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
            if result:
                print(f"   ✓ {table} table created")
            else:
                print(f"   ✗ {table} table creation failed")

        return True

    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    print("Running buyer dashboard migration...")
    success = migrate()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n⚠️  Migration failed. Please check the errors above.")
