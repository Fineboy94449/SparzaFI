# SparzaFI Test Suite

This directory contains all test files for the SparzaFI platform.

## Test Files

### Authentication & Dashboard Tests

#### `test_dashboard_login.py`
Tests user authentication and dashboard access.

```bash
# From project root
python tests/test_dashboard_login.py
```

**Tests:**
- Login functionality
- Session management
- Dashboard access control

### Deliverer Tests

#### `test_deliverer_dashboard.py`
Tests deliverer dashboard features.

```bash
python tests/test_deliverer_dashboard.py
```

**Tests:**
- Deliverer dashboard loading
- Assigned deliveries display
- Status updates

#### `test_deliverer_deep.py`
Deep testing of deliverer functionality.

```bash
python tests/test_deliverer_deep.py
```

**Tests:**
- Advanced deliverer features
- Delivery workflow
- Performance metrics

#### `test_deliverer_features.py`
Comprehensive deliverer feature testing.

```bash
python tests/test_deliverer_features.py
```

**Tests:**
- All deliverer-specific features
- Integration with order system
- Pickup/delivery codes

### Chat System Tests

#### `test_chat_system.py`
Complete chat system testing.

```bash
python tests/test_chat_system.py
```

**Tests:**
- Message sending/receiving
- Real-time updates
- Message filtering
- User-to-user chat
- Seller-buyer chat

#### `test_chat_integration.py`
Tests chat integration with other systems.

```bash
python tests/test_chat_integration.py
```

**Tests:**
- Marketplace chat integration
- Order-related messaging
- Notification system

### Marketplace Tests

#### `test_marketplace_features.py`
Tests marketplace functionality.

```bash
python tests/test_marketplace_features.py
```

**Tests:**
- Product listings
- Shopping cart
- Order placement
- Search and filters

#### `test_features_detailed.py`
Detailed testing of various platform features.

```bash
python tests/test_features_detailed.py
```

**Tests:**
- Comprehensive feature coverage
- Edge cases
- Error handling

### Transaction Explorer Tests

#### `test_transaction_explorer.py`
Comprehensive transaction explorer testing.

```bash
python tests/test_transaction_explorer.py
```

**Tests:**
- Transaction code generation
- Hash generation and integrity
- Immutable timestamp locking
- Verification logging
- Seller/Buyer/Driver explorers
- Admin explorer
- Public explorer (anonymized)
- Pickup/delivery code verification
- Security and access controls

## Running All Tests

### Using the Test Script

```bash
# Run all 5 test rounds
./scripts/run_5_tests.sh
```

### Manual Test Execution

```bash
# From project root
python tests/test_dashboard_login.py
python tests/test_deliverer_features.py
python tests/test_chat_system.py
python tests/test_marketplace_features.py
python tests/test_transaction_explorer.py
```

## Test Requirements

All tests require:
1. **Active virtual environment**
   ```bash
   source .venv/bin/activate
   ```

2. **Firebase credentials**
   ```bash
   export FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json
   ```

3. **Seeded database**
   ```bash
   python scripts/seed_firebase.py
   ```

4. **Running Flask application** (for integration tests)
   ```bash
   flask run
   ```

## Test Environment Setup

### One-Time Setup

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed test data
FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json python scripts/seed_firebase.py
```

### Before Each Test Run

```bash
# Set Firebase credentials
export FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json

# Start Flask app (in separate terminal)
flask run
```

## Test Structure

Each test file follows this structure:

```python
# 1. Import modules with sys.path adjustment
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Import required services
from firebase_config import initialize_firebase
from firebase_db import get_user_service

# 3. Initialize Firebase
initialize_firebase()

# 4. Run tests
def test_feature():
    # Test implementation
    pass

# 5. Main execution
if __name__ == '__main__':
    test_feature()
```

## Writing New Tests

When adding new tests:

1. **Create test file** in this directory
2. **Name convention**: `test_*.py`
3. **Add sys.path adjustment**:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
4. **Import required modules** from parent directory
5. **Initialize Firebase** before tests
6. **Document in this README**

## Test Results

Test results are documented in:
- **[../docs/CHAT_SYSTEM_FINAL_TEST_REPORT.md](../docs/CHAT_SYSTEM_FINAL_TEST_REPORT.md)**
- **[../docs/TRANSACTION_EXPLORER_TEST_RESULTS.md](../docs/TRANSACTION_EXPLORER_TEST_RESULTS.md)**
- **[../docs/APP_RUNNING_REPORT.md](../docs/APP_RUNNING_REPORT.md)**

## Continuous Testing

For development, use the 5-round test script:

```bash
./scripts/run_5_tests.sh
```

This runs:
1. Round 1: Basic functionality
2. Round 2: Chat integration
3. Round 3: Deliverer features
4. Round 4: Marketplace features
5. Round 5: Transaction explorer

## See Also

- **[../docs/QUICK_START.md](../docs/QUICK_START.md)** - Application setup
- **[../scripts/README.md](../scripts/README.md)** - Available scripts
- **[../README.md](../README.md)** - Project overview
