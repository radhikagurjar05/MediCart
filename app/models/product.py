from datetime import datetime, timezone
from ..extensions import db


class ProductImage(db.Model):
    """Images associated with a product."""
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Product(db.Model):
    """Product listing model."""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Pricing/Exchange
    price = db.Column(db.Numeric(10, 2), nullable=True)  # Null if only for exchange
    is_exchangeable = db.Column(db.Boolean, default=False, nullable=False)
    exchange_preferences = db.Column(db.String(200), nullable=True)
    
    # Condition: 'new', 'like_new', 'good', 'fair', 'poor'
    condition = db.Column(db.String(20), nullable=False)
    
    # Status: 'active', 'sold', 'exchanged', 'delisted'
    status = db.Column(db.String(20), default='active', nullable=False)
    
    # Metrics
    views = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    seller = db.relationship('User', backref=db.backref('products', lazy=True))
    images = db.relationship('ProductImage', backref='product', lazy='joined', cascade="all, delete-orphan")
    wishlisted_by = db.relationship('Wishlist', backref='product', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def primary_image(self):
        """Get the primary image URL or a placeholder if none exists."""
        if not self.images:
            return '/static/images/product-placeholder.jpg'
        primary = next((img for img in self.images if img.is_primary), self.images[0])
        return primary.image_url
        
    @property
    def is_available(self):
        return self.status == 'active'

    def __repr__(self):
        return f'<Product {self.id}: {self.title}>'
