from ..extensions import db

class Category(db.Model):
    """Category model for classifying products."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    icon = db.Column(db.String(50), nullable=True)  # Lucide icon name
    description = db.Column(db.String(200), nullable=True)

    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'
