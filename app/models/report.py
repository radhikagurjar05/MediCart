from datetime import datetime, timezone
from ..extensions import db

class Report(db.Model):
    """Reports for flagged listings."""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, reviewed, dismissed
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    reporter = db.relationship('User', backref='reports_filed')
    product = db.relationship('Product', backref='reports')

    def __repr__(self):
        return f'<Report {self.id} on Product {self.product_id}>'
