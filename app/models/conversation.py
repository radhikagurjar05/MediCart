from datetime import datetime, timezone
from ..extensions import db


class Conversation(db.Model):
    """Conversation model associating a buyer, seller, and specific listing."""
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Relationships
    listing = db.relationship('Product', backref=db.backref('conversations', cascade='all, delete-orphan'))
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref=db.backref('buyer_conversations', lazy='dynamic'))
    seller = db.relationship('User', foreign_keys=[seller_id], backref=db.backref('seller_conversations', lazy='dynamic'))
    messages = db.relationship(
        'Message',
        backref='conversation',
        cascade='all, delete-orphan',
        order_by='Message.created_at.asc()',
        lazy='select'
    )

    __table_args__ = (
        db.UniqueConstraint('listing_id', 'buyer_id', 'seller_id', name='uq_listing_buyer_seller'),
    )

    def other_user(self, user_id):
        """Return the other participant in the conversation."""
        if self.buyer_id == user_id:
            return self.seller
        return self.buyer

    @property
    def last_message(self):
        """Return the most recent message in this conversation."""
        if self.messages:
            return self.messages[-1]
        return None

    def unread_count_for(self, user_id):
        """Count unread messages sent by the other participant."""
        return sum(1 for m in self.messages if m.sender_id != user_id and not m.is_read)

    def __repr__(self):
        return f'<Conversation {self.id}: Listing {self.listing_id} (Buyer: {self.buyer_id}, Seller: {self.seller_id})>'


class Message(db.Model):
    """Message model for direct chat messages."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')

    def to_dict(self):
        """Serialize message to dictionary for JSON and Socket.IO."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.display_name if self.sender else 'User',
            'sender_avatar': self.sender.avatar_url if self.sender else None,
            'sender_initials': self.sender.initials if self.sender else 'U',
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'formatted_time': self.created_at.strftime('%I:%M %p') if self.created_at else '',
            'formatted_date': self.created_at.strftime('%b %d, %Y') if self.created_at else '',
            'is_read': self.is_read
        }

    def __repr__(self):
        return f'<Message {self.id}: Conv {self.conversation_id} from User {self.sender_id}>'
