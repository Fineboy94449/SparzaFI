# SparzaFI Project Structure

This document provides a comprehensive overview of the SparzaFI project structure.

## Directory Organization

```
SparzaFI main app/
├── admin/                          # Admin module
│   ├── __init__.py
│   ├── routes.py                   # Admin routes and views
│   └── utils.py                    # Admin utilities
│
├── api/                            # API module for mobile/fintech
│   ├── __init__.py
│   ├── routes.py                   # API endpoints
│   └── utils.py                    # API utilities
│
├── auth/                           # Authentication module
│   ├── __init__.py
│   ├── forms.py                    # Login/registration forms
│   ├── routes.py                   # Auth routes
│   └── utils.py                    # Auth utilities
│
├── chat/                           # Chat system module
│   ├── __init__.py
│   ├── message_filter.py           # Message filtering
│   └── routes.py                   # Chat routes
│
├── deliverer/                      # Deliverer module
│   ├── __init__.py
│   ├── firebase_verification_codes.py
│   ├── routes.py                   # Deliverer routes
│   └── utils.py                    # Deliverer utilities
│
├── docs/                           # All documentation
│   ├── README.md                   # Documentation index
│   ├── QUICK_START.md              # Quick start guide
│   ├── API_DOCS.md                 # API documentation
│   ├── FIREBASE_*.md               # Firebase guides
│   ├── CHAT_*.md                   # Chat system docs
│   ├── TRANSACTION_*.md            # Transaction docs
│   └── ... (all markdown files)
│
├── marketplace/                    # Marketplace module
│   ├── __init__.py
│   ├── routes.py                   # Marketplace routes
│   └── utils.py                    # Marketplace utilities
│
├── scripts/                        # Utility scripts
│   ├── README.md                   # Scripts documentation
│   ├── run.sh                      # Quick start script
│   ├── run_app.sh                  # App runner
│   ├── run_5_tests.sh              # Test runner
│   ├── seed_firebase.py            # Database seeding
│   └── migrate_transactions_enhanced.py
│
├── seller/                         # Seller module
│   ├── __init__.py
│   ├── routes.py                   # Seller routes
│   └── utils.py                    # Seller utilities
│
├── shared/                         # Shared components
│   ├── __init__.py
│   ├── chat_utils.py               # Chat utilities
│   ├── components.py               # Shared UI components
│   ├── firebase_chat_utils.py      # Firebase chat utils
│   └── utils.py                    # General utilities
│
├── static/                         # Static assets
│   ├── css/                        # Stylesheets
│   ├── js/                         # JavaScript files
│   ├── images/                     # Images
│   └── fonts/                      # Custom fonts
│
├── templates/                      # Jinja2 templates
│   ├── admin/                      # Admin templates
│   ├── auth/                       # Auth templates
│   ├── chat/                       # Chat templates
│   ├── marketplace/                # Marketplace templates
│   ├── seller/                     # Seller templates
│   ├── shared/                     # Shared templates
│   └── user/                       # User templates
│
├── tests/                          # Test suite
│   ├── README.md                   # Testing documentation
│   ├── __init__.py
│   ├── test_dashboard_login.py
│   ├── test_chat_system.py
│   ├── test_deliverer_*.py
│   ├── test_marketplace_features.py
│   └── test_transaction_explorer.py
│
├── transaction_explorer/           # Transaction explorer module
│   ├── __init__.py
│   ├── routes.py                   # Explorer routes
│   └── service.py                  # Explorer services
│
├── user/                           # User module
│   ├── __init__.py
│   ├── buyer_dashboard.py          # Buyer dashboard
│   ├── routes.py                   # User routes
│   └── utils.py                    # User utilities
│
├── .venv/                          # Virtual environment (git ignored)
├── extensions/                     # Firebase extensions config
├── instance/                       # Instance-specific files
├── node_modules/                   # NPM packages (git ignored)
│
├── app.py                          # Main application entry
├── config.py                       # Configuration
├── firebase_config.py              # Firebase configuration
├── firebase_db.py                  # Firebase database service
├── firebase_service.py             # Firebase services
│
├── .env                            # Environment variables (git ignored)
├── .env.example                    # Example environment file
├── .gitignore                      # Git ignore rules
├── firebase.json                   # Firebase config
├── firestore.indexes.json          # Firestore indexes
├── firestore.rules                 # Firestore security rules
├── storage.rules                   # Storage security rules
│
├── package.json                    # Node.js dependencies
├── requirements.txt                # Python dependencies
├── runtime.txt                     # Python version
├── Procfile                        # Deployment config
│
├── README.md                       # Project overview
└── PROJECT_STRUCTURE.md            # This file
```

## Module Descriptions

### Core Modules

#### `admin/`
Admin dashboard and management features:
- User management
- Platform analytics
- System configuration
- Transaction monitoring

#### `api/`
RESTful API for mobile apps and third-party integrations:
- User endpoints
- Product endpoints
- Transaction endpoints
- Authentication endpoints

#### `auth/`
User authentication and authorization:
- Login/logout
- Registration
- Password management
- Session management
- Google OAuth integration

#### `marketplace/`
Main marketplace functionality:
- Product browsing
- Shopping cart
- Product search and filters
- Categories

#### `seller/`
Seller dashboard and tools:
- Product management
- Order management
- Sales analytics
- Inventory tracking

#### `deliverer/`
Deliverer (driver) management:
- Delivery assignments
- Route optimization
- Delivery tracking
- Verification codes

#### `user/`
User account management:
- Profile management
- Order history
- Wallet/balance
- Settings

#### `chat/`
Real-time chat system:
- User-to-user messaging
- Seller-buyer communication
- Order-related chat
- Message filtering

#### `transaction_explorer/`
Advanced transaction analysis:
- Transaction tracking
- Code generation
- Hash verification
- Immutable timestamps
- Analytics and reporting

### Support Directories

#### `shared/`
Shared utilities and components used across modules:
- Common UI components
- Utility functions
- Firebase helpers
- Chat utilities

#### `static/`
Static assets served directly:
- CSS stylesheets
- JavaScript files
- Images and icons
- Custom fonts

#### `templates/`
Jinja2 HTML templates:
- Organized by module
- Shared base templates
- Component templates

#### `docs/`
All project documentation:
- Setup guides
- Feature documentation
- API documentation
- Testing reports
- Firebase guides

#### `scripts/`
Utility and maintenance scripts:
- Application runners
- Database scripts
- Migration tools
- Test runners

#### `tests/`
Test suite for quality assurance:
- Unit tests
- Integration tests
- Feature tests
- System tests

## Configuration Files

### Python Configuration
- **`app.py`** - Main Flask application
- **`config.py`** - Application configuration
- **`requirements.txt`** - Python dependencies
- **`runtime.txt`** - Python version specification

### Firebase Configuration
- **`firebase_config.py`** - Firebase initialization
- **`firebase_db.py`** - Database service layer
- **`firebase_service.py`** - Firebase services
- **`firebase.json`** - Firebase project config
- **`firestore.indexes.json`** - Database indexes
- **`firestore.rules`** - Security rules for Firestore
- **`storage.rules`** - Security rules for Storage
- **`firebase-service-account.json`** - Service account (git ignored)

### Node.js Configuration
- **`package.json`** - Node.js dependencies
- **`package-lock.json`** - Locked versions

### Environment Configuration
- **`.env`** - Environment variables (git ignored)
- **`.env.example`** - Example environment template

### Deployment Configuration
- **`Procfile`** - Heroku/cloud deployment config
- **`app.yaml`** - Google App Engine config

## Import Structure

### Standard Import Pattern

For modules in root directory:
```python
from flask import Flask
from config import config
from firebase_db import get_user_service
```

For modules in subdirectories (tests/, scripts/):
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now can import from root
from firebase_config import initialize_firebase
from transaction_explorer.service import get_transaction_explorer_service
```

### Blueprint Registration

In `app.py`:
```python
from auth import auth_bp
from marketplace import marketplace_bp
from seller import seller_bp
from deliverer import deliverer_bp
from admin import admin_bp
from user import user_bp
from api import api_bp
from chat import chat_bp
from transaction_explorer.routes import explorer_bp

app.register_blueprint(auth_bp)
app.register_blueprint(marketplace_bp, url_prefix='/marketplace')
# ... etc
```

## File Naming Conventions

### Python Files
- **Module initialization**: `__init__.py`
- **Route definitions**: `routes.py`
- **Utility functions**: `utils.py`
- **Service layer**: `service.py`
- **Form definitions**: `forms.py`
- **Test files**: `test_*.py`
- **Scripts**: `*_script.py` or `.sh` for shell

### Documentation
- **Markdown files**: `UPPERCASE_WITH_UNDERSCORES.md`
- **README files**: `README.md`

### Templates
- **HTML templates**: `lowercase_with_underscores.html`
- **Base templates**: `base.html`
- **Component templates**: `_component_name.html` (prefix with `_`)

## Best Practices

### Module Organization
1. Each module should be self-contained
2. Use `__init__.py` to expose public API
3. Keep related functionality together
4. Avoid circular imports

### Documentation
1. Keep documentation up-to-date
2. Document all public APIs
3. Include usage examples
4. Maintain changelog

### Testing
1. Test coverage for all features
2. Integration tests for workflows
3. Regular test execution
4. Document test results

### Version Control
1. Use meaningful commit messages
2. Keep `.gitignore` updated
3. Don't commit secrets or credentials
4. Regular commits and pushes

## See Also

- **[README.md](README.md)** - Project overview
- **[docs/README.md](docs/README.md)** - Documentation index
- **[scripts/README.md](scripts/README.md)** - Scripts documentation
- **[tests/README.md](tests/README.md)** - Testing guide
