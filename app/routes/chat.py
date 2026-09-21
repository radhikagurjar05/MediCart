from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from ..services.chat_service import ChatService
from ..models.conversation import Conversation

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/contact-seller/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def contact_seller(listing_id):
    """Create or retrieve a conversation for a listing, then redirect to it."""
    from ..models.product import Product
    product = Product.query.get(listing_id)
    if not product:
        flash('Listing not found.', 'error')
        return redirect(url_for('main.index'))

    # Prevent seller contacting themselves
    if product.seller_id == current_user.id:
        flash('You cannot contact yourself regarding your own listing.', 'warning')
        return redirect(url_for('product.detail', product_id=listing_id))

    conversation, error = ChatService.get_or_create_conversation(
        listing_id=listing_id,
        buyer_id=current_user.id
    )

    if error:
        flash(error, 'error')
        return redirect(url_for('product.detail', product_id=listing_id))

    return redirect(url_for('chat.chat_view', conversation_id=conversation.id))


@chat_bp.route('/messages')
@login_required
def messages():
    """Show all conversations for the current user."""
    conversations = ChatService.get_user_conversations(current_user.id)
    return render_template('chat/messages.html', conversations=conversations)


@chat_bp.route('/chat/<int:conversation_id>')
@login_required
def chat_view(conversation_id):
    """Show the real-time chat interface for a specific conversation."""
    conversation, error = ChatService.get_conversation(conversation_id, current_user.id)
    if error:
        if 'Unauthorized' in error:
            abort(403)
        flash(error, 'error')
        return redirect(url_for('chat.messages'))

    # Mark messages as read on page load
    ChatService.mark_messages_as_read(conversation_id, current_user.id)

    other_user = conversation.other_user(current_user.id)
    return render_template(
        'chat/chat.html',
        conversation=conversation,
        other_user=other_user,
        messages=conversation.messages,
        current_user_id=current_user.id
    )


@chat_bp.route('/chat/<int:conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    """HTTP fallback endpoint for sending messages (no-JS or AJAX)."""
    conversation, error = ChatService.get_conversation(conversation_id, current_user.id)
    if error:
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 403 if 'Unauthorized' in error else 404
        abort(403 if 'Unauthorized' in error else 404)

    text = (request.form.get('message') or request.json.get('message', '') if request.is_json else '').strip()

    if not text:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Message cannot be empty.'}), 400
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('chat.chat_view', conversation_id=conversation_id))

    message, err = ChatService.send_message(conversation_id, current_user.id, text)
    if err:
        if request.is_json:
            return jsonify({'success': False, 'error': err}), 400
        flash(err, 'error')
        return redirect(url_for('chat.chat_view', conversation_id=conversation_id))

    if request.is_json:
        return jsonify({'success': True, 'message': message.to_dict()})

    return redirect(url_for('chat.chat_view', conversation_id=conversation_id))


@chat_bp.route('/chat/<int:conversation_id>/read', methods=['POST'])
@login_required
def mark_read(conversation_id):
    """Mark all messages in a conversation as read (called via AJAX)."""
    conversation, error = ChatService.get_conversation(conversation_id, current_user.id)
    if error:
        return jsonify({'success': False, 'error': error}), 403

    updated = ChatService.mark_messages_as_read(conversation_id, current_user.id)
    unread = ChatService.get_unread_count_for_user(current_user.id)
    return jsonify({'success': True, 'marked_read': updated, 'total_unread': unread})
