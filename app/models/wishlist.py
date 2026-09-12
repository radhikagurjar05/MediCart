from datetime import datetime, timezone
from ..extensions import db

class Wishlist(db.Model):
    """Many-to-many junction table for User <-> Product wishlists."""
    __tablename__ = 'wishlists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Ensures a user can only wishlist a specific product once
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='uq_user_product_wishlist'),)

    def __repr__(self):
        return f'<Wishlist User:{self.user_id} Product:{self.product_id}>'
