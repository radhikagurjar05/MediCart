from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class User(UserMixin, db.Model):
    """User model for students and admins."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for OAuth users
    avatar_url = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # Role: 'student' or 'admin'
    role = db.Column(db.String(20), nullable=False, default='student')

    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)

    # Authentication provider: 'local' or 'google'
    auth_provider = db.Column(db.String(20), nullable=False, default='local')

    # Preferences
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    wishlisted_items = db.relationship('Wishlist', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    # ---- Wishlist Helpers ----
    @property
    def wishlist_product_ids(self):
        """Set of product IDs wishlisted by this user (cached per request instance)."""
        if not hasattr(self, '_cached_wishlist_ids'):
            self._cached_wishlist_ids = {item.product_id for item in self.wishlisted_items.all()}
        return self._cached_wishlist_ids

    def has_wishlisted(self, product_id):
        """Check if user has wishlisted a product."""
        return product_id in self.wishlist_product_ids

    # ---- Password Methods ----
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify a password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # ---- Role Checks ----
    @property
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role == 'admin'

    @property
    def is_student(self):
        """Check if user is a regular student."""
        return self.role == 'student'

    # ---- Display Helpers ----
    @property
    def display_name(self):
        """Return the user's display name."""
        return self.name or self.email.split('@')[0]

    @property
    def initials(self):
        """Return initials for avatar placeholder."""
        parts = self.name.split() if self.name else [self.email[0]]
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][0].upper()

    @property
    def member_since(self):
        """Return a formatted join date string."""
        if self.created_at:
            return self.created_at.strftime('%B %Y')
        return 'Unknown'

    def __repr__(self):
        return f'<User {self.id}: {self.email}>'
