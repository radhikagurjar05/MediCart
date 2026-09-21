from datetime import datetime, timezone
import sqlalchemy as sa
from ..extensions import db
from ..models.conversation import Conversation, Message
from ..models.product import Product


class ChatService:
    """Service handling conversation management, messages, and unread notifications."""

    @staticmethod
    def get_or_create_conversation(listing_id, buyer_id):
        """
        Get an existing conversation for listing + buyer, or create a new one.
        Returns (conversation, error_message).
        """
        product = Product.query.get(listing_id)
        if not product:
            return None, "Listing not found."

        if product.seller_id == buyer_id:
            return None, "You cannot contact yourself regarding your own listing."

        # Check for existing conversation
        conversation = Conversation.query.filter_by(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=product.seller_id
        ).first()

        if conversation:
            return conversation, None

        # Create new conversation
        conversation = Conversation(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=product.seller_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        try:
            db.session.add(conversation)
            db.session.commit()
            return conversation, None
        except Exception as e:
            db.session.rollback()
            return None, f"Could not create conversation: {str(e)}"

    @staticmethod
    def get_user_conversations(user_id):
        """
        Get all conversations where user is buyer or seller, ordered by recent activity.
        """
        return Conversation.query.filter(
            sa.or_(
                Conversation.buyer_id == user_id,
                Conversation.seller_id == user_id
            )
        ).order_by(Conversation.updated_at.desc()).all()

    @staticmethod
    def get_conversation(conversation_id, user_id):
        """
        Retrieve a conversation and verify that user_id is a participant.
        Returns (conversation, error_message).
        """
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return None, "Conversation not found."

        if user_id != conversation.buyer_id and user_id != conversation.seller_id:
            return None, "Unauthorized access to this conversation."

        return conversation, None

    @staticmethod
    def send_message(conversation_id, sender_id, text):
        """
        Send a message in a conversation.
        Returns (message, error_message).
        """
        if not text or not text.strip():
            return None, "Message cannot be empty."

        clean_text = text.strip()
        if len(clean_text) > 3000:
            return None, "Message is too long (maximum 3000 characters)."

        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return None, "Conversation not found."

        if sender_id != conversation.buyer_id and sender_id != conversation.seller_id:
            return None, "Unauthorized: you are not a participant in this conversation."

        now = datetime.now(timezone.utc)
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            message=clean_text,
            created_at=now,
            is_read=False
        )
        conversation.updated_at = now

        try:
            db.session.add(message)
            db.session.commit()
            return message, None
        except Exception as e:
            db.session.rollback()
            return None, f"Could not send message: {str(e)}"

    @staticmethod
    def mark_messages_as_read(conversation_id, user_id):
        """
        Mark all messages in the conversation sent by the other user as read.
        Returns number of updated messages.
        """
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return 0

        if user_id != conversation.buyer_id and user_id != conversation.seller_id:
            return 0

        unread_messages = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != user_id,
            Message.is_read == False
        ).all()

        if not unread_messages:
            return 0

        for msg in unread_messages:
            msg.is_read = True

        try:
            db.session.commit()
            return len(unread_messages)
        except Exception:
            db.session.rollback()
            return 0

    @staticmethod
    def get_unread_count_for_user(user_id):
        """
        Get the total unread message count across all active conversations for user_id.
        """
        try:
            count = Message.query.join(Conversation).filter(
                sa.or_(
                    Conversation.buyer_id == user_id,
                    Conversation.seller_id == user_id
                ),
                Message.sender_id != user_id,
                Message.is_read == False
            ).count()
            return count
        except Exception:
            return 0
