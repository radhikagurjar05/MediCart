import os
from flask import Flask
from .config import config
from .extensions import db, login_manager


def create_app(config_name=None):
    """Application Factory: creates and configures the Flask app."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure upload directories exist
    uploads_path = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(os.path.join(uploads_path, 'products'), exist_ok=True)
    os.makedirs(os.path.join(uploads_path, 'avatars'), exist_ok=True)

    # Register user loader
    from .models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.product import product_bp
    from .routes.wishlist import wishlist_bp
    from .routes.profile import profile_bp
    from .routes.dashboard import dashboard_bp
    from .routes.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    
    # Configure Google OAuth if credentials exist
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        from flask_dance.contrib.google import make_google_blueprint
        
        # We need to set OAUTHLIB_INSECURE_TRANSPORT in dev for HTTP
        if app.config.get('DEBUG'):
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
            
        google_bp = make_google_blueprint(
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            scope=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"
            ],
            redirect_to="auth.google_login_callback"
        )
        app.register_blueprint(google_bp, url_prefix="/auth/login")

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
