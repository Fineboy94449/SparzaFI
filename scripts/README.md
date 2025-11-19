# SparzaFI Scripts

This directory contains all utility scripts for the SparzaFI platform.

## Available Scripts

### Application Runners

#### `run.sh`
Quick start script for running the Flask application.

```bash
cd /path/to/SparzaFI\ main\ app
./scripts/run.sh
```

**What it does:**
- Activates virtual environment
- Runs Flask development server

#### `run_app.sh`
Alternative application runner with additional configuration options.

```bash
./scripts/run_app.sh
```

### Testing

#### `run_5_tests.sh`
Runs the comprehensive test suite including 5 rounds of testing.

```bash
./scripts/run_5_tests.sh
```

**Tests included:**
- Dashboard login tests
- Deliverer feature tests
- Chat system tests
- Marketplace feature tests
- Transaction explorer tests

### Database Scripts

#### `seed_firebase.py`
Seeds the Firebase Firestore database with initial demo data.

```bash
# From project root
python scripts/seed_firebase.py
```

**What it seeds:**
- Demo users (admin, sellers, buyers, deliverers)
- Sample products
- Test transactions
- Sample reviews

#### `migrate_transactions_enhanced.py`
Migration script to add enhanced transaction fields.

```bash
# From project root
FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json python scripts/migrate_transactions_enhanced.py
```

**Adds:**
- Transaction codes (SPZ-XXXXXX-XXXXXXXX-YYYYMMDD)
- Transaction hashes for integrity verification
- Immutable timestamps
- Verification logs
- Pickup and delivery codes

## Usage Notes

### Running from Root Directory

All scripts should be run from the project root directory:

```bash
cd /home/fineboy94449/Documents/SparzaFI/SparzaFI\ main\ app
./scripts/run.sh
```

### Making Scripts Executable

If you get "Permission denied" errors:

```bash
chmod +x scripts/*.sh
```

### Environment Variables

Some scripts require environment variables:

```bash
# For Firebase scripts
export FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json

# Or pass inline
FIREBASE_SERVICE_ACCOUNT=./firebase-service-account.json python scripts/seed_firebase.py
```

## Script Dependencies

All Python scripts require:
- Active virtual environment
- Installed requirements (see `requirements.txt`)
- Firebase credentials (for database scripts)

## Adding New Scripts

When adding new scripts:
1. Place them in this directory
2. Make shell scripts executable (`chmod +x`)
3. Add parent directory to Python path if needed:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
4. Update this README

## See Also

- **[../docs/QUICK_START.md](../docs/QUICK_START.md)** - Application setup guide
- **[../docs/FIREBASE_INTEGRATION_GUIDE.md](../docs/FIREBASE_INTEGRATION_GUIDE.md)** - Firebase setup
- **[../tests/README.md](../tests/README.md)** - Testing documentation
