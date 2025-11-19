"""
SparzaFi - Community Marketplace Platform
Main application entry point with Blueprint architecture
Using Firebase Firestore for database
"""

import os
from flask import Flask, g
from config import config

def create_app(config_name='development'):
    """Application factory pattern"""
    import jinja2

    # Create app with custom template loader
    app = Flask(__name__,
                template_folder='templates')

    # Add additional template folders
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader([
            'templates',
            'shared/templates',
        ]),
    ])
    app.jinja_loader = my_loader

    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure instance folder exists
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Firebase (required - replaces SQLite)
    try:
        from firebase_config import initialize_firebase
        initialize_firebase(app.config.get('FIREBASE_SERVICE_ACCOUNT'))
        print("✓ Firebase initialized - SparzaFI is using Firestore database")
    except Exception as e:
        print(f"✗ CRITICAL: Firebase initialization failed: {e}")
        print("SparzaFI requires Firebase to run. Please configure Firebase credentials.")
        raise
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)

    # Note: Firebase handles connection pooling automatically
    # No teardown needed unlike SQLite

    return app


def register_blueprints(app):
    """Register all application blueprints"""
    
    # Authentication
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Marketplace
    from marketplace import marketplace_bp
    app.register_blueprint(marketplace_bp, url_prefix='/marketplace')
    
    # Seller
    from seller import seller_bp
    app.register_blueprint(seller_bp, url_prefix='/seller')
    
    # Deliverer (formerly Driver)
    from deliverer import deliverer_bp
    app.register_blueprint(deliverer_bp, url_prefix='/deliverer')
    
    # Admin
    from admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # User
    from user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    
    # API (for mobile/fintech)
    from api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Chat
    from chat import chat_bp
    app.register_blueprint(chat_bp)

    # Transaction Explorer
    from transaction_explorer_routes import explorer_bp
    app.register_blueprint(explorer_bp)


def register_error_handlers(app):
    """Register custom error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('shared/error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('shared/error.html', 
                             error_code=403, 
                             error_message="Access forbidden"), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        # Firebase transactions are atomic - no manual rollback needed

        return render_template('shared/error.html',
                             error_code=500,
                             error_message="Internal server error"), 500


def register_context_processors(app):
    """Register context processors for templates"""
    
    @app.context_processor
    def inject_common_data():
        """Make common data available to all templates"""
        from flask import session
        
        # Calculate cart count
        cart_count = 0
        if 'cart' in session:
            cart_count = sum(item['quantity'] for item in session['cart'].values())
        
        return {
            'GOOGLE_MAPS_API_KEY': app.config['GOOGLE_MAPS_API_KEY'],
            'TOKEN_SYMBOL': app.config['TOKEN_SYMBOL'],
            'TOKEN_NAME': app.config['TOKEN_NAME'],
            'cart_count': cart_count,
            'current_user': session.get('user'),
            'platform_name': 'SparzaFi'
        }


# Create the application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))


if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )