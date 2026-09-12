from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from ..services.product_service import ProductService
from ..models.category import Category

product_bp = Blueprint('product', __name__, url_prefix='/p')

@product_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new product listing."""
    if request.method == 'POST':
        success, result = ProductService.create_product(
            seller_id=current_user.id,
            data=request.form,
            files=request.files
        )
        
        if success:
            flash('Your listing has been published!', 'success')
            return redirect(url_for('product.detail', product_id=result))
        else:
            flash(result, 'error')
            
    categories = Category.query.all()
    return render_template('product/create.html', categories=categories)


@product_bp.route('/<int:product_id>')
def detail(product_id):
    """View a single product listing."""
    product = ProductService.get_product(product_id)
    if not product:
        flash('Listing not found.', 'error')
        return redirect(url_for('main.index'))
        
    # Increment views
    from ..extensions import db
    product.views += 1
    db.session.commit()
    
    is_wishlisted = False
    if current_user.is_authenticated:
        from ..models.wishlist import Wishlist
        is_wishlisted = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first() is not None
        
    return render_template('product/detail.html', product=product, is_wishlisted=is_wishlisted)


@product_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    """Edit an existing product listing."""
    product = ProductService.get_product(product_id)
    if not product:
        flash('Listing not found.', 'error')
        return redirect(url_for('main.index'))
        
    if product.seller_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this listing.', 'error')
        return redirect(url_for('product.detail', product_id=product_id))
        
    if request.method == 'POST':
        success, msg = ProductService.update_product(
            product_id=product_id,
            user_id=current_user.id,
            data=request.form,
            is_admin=current_user.is_admin
        )
        
        if success:
            flash(msg, 'success')
            return redirect(url_for('product.detail', product_id=product_id))
        else:
            flash(msg, 'error')
            
    categories = Category.query.all()
    return render_template('product/edit.html', product=product, categories=categories)





@product_bp.route('/<int:product_id>/status', methods=['POST'])
@login_required
def update_status(product_id):
    """Update listing status."""
    new_status = request.form.get('status')
    success, msg = ProductService.update_status(
        product_id=product_id, 
        user_id=current_user.id, 
        new_status=new_status,
        is_admin=current_user.is_admin
    )
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
        
    return redirect(url_for('product.detail', product_id=product_id))


@product_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
def delete(product_id):
    """Delete a listing."""
    success, msg = ProductService.delete_product(
        product_id=product_id, 
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )
    
    if success:
        flash(msg, 'success')
        return redirect(url_for('main.index'))
    else:
        flash(msg, 'error')
        return redirect(url_for('product.detail', product_id=product_id))
