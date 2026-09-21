"""
MediCart Chat — Socket.IO Event Handlers

Rooms:
  user_<user_id>           → personal room for global unread badge updates
  conversation_<conv_id>   → per-chat room for real-time messaging
"""
from flask import request
from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from ..extensions import socketio, db
from ..models.conversation import Conversation, Message
from ..services.chat_service import ChatService


# ------------------------------------------------------------------ #
# Helper: ensure the connected socket belongs to an authenticated user
# ------------------------------------------------------------------ #
def _authenticated_user():
    """Return the current_user if authenticated, else None."""
    if current_user and current_user.is_authenticated:
        return current_user
    return None


def _verify_conversation_access(conversation_id, user_id):
    """Return the Conversation if user is a participant, else None."""
    conv = Conversation.query.get(conversation_id)
    if not conv:
        return None
    if user_id != conv.buyer_id and user_id != conv.seller_id:
        return None
    return conv


# ------------------------------------------------------------------ #
# Connection events
# ------------------------------------------------------------------ #
@socketio.on('connect')
def on_connect():
    user = _authenticated_user()
    if user:
        # Auto-join personal room so we can push unread count updates at any time
        join_room(f'user_{user.id}')


@socketio.on('disconnect')
def on_disconnect():
    pass  # Rooms are cleaned up automatically by Socket.IO


# ------------------------------------------------------------------ #
# Explicit personal room join (called from any page to receive badges)
# ------------------------------------------------------------------ #
@socketio.on('join_user')
def on_join_user():
    user = _authenticated_user()
    if not user:
        return
    join_room(f'user_{user.id}')
    # Send current unread count immediately
    count = ChatService.get_unread_count_for_user(user.id)
    emit('unread_update', {'count': count})


# ------------------------------------------------------------------ #
# Join / Leave a specific chat room
# ------------------------------------------------------------------ #
@socketio.on('join_chat')
def on_join_chat(data):
    user = _authenticated_user()
    if not user:
        emit('error', {'message': 'Authentication required.'})
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        emit('error', {'message': 'conversation_id required.'})
        return

    conv = _verify_conversation_access(conversation_id, user.id)
    if not conv:
        emit('error', {'message': 'Conversation not found or access denied.'})
        return

    room = f'conversation_{conversation_id}'
    join_room(room)

    # Mark other user's messages as read now that we've opened the chat
    updated = ChatService.mark_messages_as_read(conversation_id, user.id)
    if updated > 0:
        # Notify the sender that their messages were read
        other = conv.other_user(user.id)
        emit('messages_read', {
            'conversation_id': conversation_id,
            'read_by': user.id
        }, to=f'user_{other.id}')

    # Push updated unread count to the viewer's personal room
    count = ChatService.get_unread_count_for_user(user.id)
    emit('unread_update', {'count': count}, to=f'user_{user.id}')


@socketio.on('leave_chat')
def on_leave_chat(data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        leave_room(f'conversation_{conversation_id}')


# ------------------------------------------------------------------ #
# Send a real-time message
# ------------------------------------------------------------------ #
@socketio.on('send_message')
def on_send_message(data):
    user = _authenticated_user()
    if not user:
        emit('error', {'message': 'Authentication required.'})
        return

    conversation_id = data.get('conversation_id')
    text = (data.get('message') or '').strip()

    if not conversation_id or not text:
        emit('error', {'message': 'conversation_id and message are required.'})
        return

    # Validate access
    conv = _verify_conversation_access(conversation_id, user.id)
    if not conv:
        emit('error', {'message': 'Conversation not found or access denied.'})
        return

    # Persist the message
    message, error = ChatService.send_message(conversation_id, user.id, text)
    if error:
        emit('error', {'message': error})
        return

    # Emit to the chat room (both participants)
    msg_data = message.to_dict()
    room = f'conversation_{conversation_id}'
    emit('new_message', msg_data, to=room)

    # Push unread badge update to the RECIPIENT's personal room
    other = conv.other_user(user.id)
    recipient_unread = ChatService.get_unread_count_for_user(other.id)
    emit('unread_update', {'count': recipient_unread}, to=f'user_{other.id}')


# ------------------------------------------------------------------ #
# Mark messages as read via socket (when conversation is already open)
# ------------------------------------------------------------------ #
@socketio.on('mark_as_read')
def on_mark_as_read(data):
    user = _authenticated_user()
    if not user:
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return

    conv = _verify_conversation_access(conversation_id, user.id)
    if not conv:
        return

    updated = ChatService.mark_messages_as_read(conversation_id, user.id)
    if updated > 0:
        other = conv.other_user(user.id)
        emit('messages_read', {
            'conversation_id': conversation_id,
            'read_by': user.id
        }, to=f'user_{other.id}')

    # Update viewer's own count
    count = ChatService.get_unread_count_for_user(user.id)
    emit('unread_update', {'count': count}, to=f'user_{user.id}')
