from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models.wishlist import Wishlist
from ..models.product import Product

wishlist_bp = Blueprint('wishlist', __name__, url_prefix='/wishlist')

@wishlist_bp.route('/')
@login_required
def index():
    """Render the user's wishlist page."""
    # Get all products the user has wishlisted
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).order_by(Wishlist.created_at.desc()).all()
    products = [item.product for item in wishlist_items]
    return render_template('wishlist/index.html', products=products)


@wishlist_bp.route('/toggle/<int:product_id>', methods=['POST'])
def toggle(product_id):
    """Toggle a product in the user's wishlist via AJAX."""
    if not current_user.is_authenticated:
        return jsonify({'status': 'unauthorized', 'message': 'Please log in to save items to your wishlist'}), 401

    product = Product.query.get_or_404(product_id)
    
    # Check if already wishlisted
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    try:
        if existing:
            # Remove from wishlist
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'status': 'removed', 'message': 'Removed from wishlist'})
        else:
            # Add to wishlist
            new_wishlist = Wishlist(user_id=current_user.id, product_id=product_id)
            db.session.add(new_wishlist)
            db.session.commit()
            return jsonify({'status': 'added', 'message': 'Added to wishlist'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
