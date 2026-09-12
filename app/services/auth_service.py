from ..extensions import db
from ..models.user import User
from ..utils.validators import is_valid_campus_email, validate_password_strength

class AuthService:
    @staticmethod
    def register_user(name, email, password):
        """Registers a new user via email and password."""
        # Validate email domain
        if not is_valid_campus_email(email):
            return False, "Registration is restricted to Medi-Caps University emails (@medicaps.ac.in)."
            
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return False, "Email address already registered."
            
        # Validate password
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            return False, msg
            
        # Create user
        new_user = User(
            name=name,
            email=email,
            auth_provider='local'
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return True, new_user
        except Exception as e:
            db.session.rollback()
            return False, f"An error occurred during registration: {str(e)}"
            
    @staticmethod
    def login_user(email, password):
        """Authenticates a user via email and password."""
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return False, "Invalid email or password."
            
        if user.is_banned:
            return False, "This account has been suspended. Please contact support."
            
        if user.auth_provider != 'local':
            return False, f"Please log in using your {user.auth_provider.capitalize()} account."
            
        if not user.check_password(password):
            return False, "Invalid email or password."
            
        return True, user
        
    @staticmethod
    def get_or_create_oauth_user(email, name, provider='google'):
        """Handles user creation/login from OAuth providers."""
        if not is_valid_campus_email(email):
            return False, "Access restricted to Medi-Caps University emails (@medicaps.ac.in)."
            
        user = User.query.filter_by(email=email).first()
        
        if user:
            if user.is_banned:
                return False, "This account has been suspended."
            # If user exists but registered via local, let them log in via OAuth 
            # and update their provider if needed, but for security, usually 
            # we keep the original provider. Let's just log them in.
            return True, user
            
        # Create new OAuth user
        new_user = User(
            name=name,
            email=email,
            auth_provider=provider
        )
        # No password needed for OAuth
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return True, new_user
        except Exception as e:
            db.session.rollback()
            return False, f"An error occurred during OAuth login: {str(e)}"
