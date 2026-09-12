from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.user import User
from ..models.product import Product

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/<int:user_id>')
def view(user_id):
    """Public profile view showing user stats and active listings."""
    user = User.query.get_or_404(user_id)
    
    active_listings = Product.query.filter_by(seller_id=user.id, status='active').order_by(Product.created_at.desc()).all()
    total_sold = Product.query.filter_by(seller_id=user.id, status='sold').count()
    
    return render_template('profile/view.html', user=user, active_listings=active_listings, total_sold=total_sold)

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Edit user profile and avatar."""
    if request.method == 'POST':
        from ..services.user_service import UserService
        avatar = request.files.get('avatar')
        success, message = UserService.update_profile(current_user.id, request.form, avatar)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('profile.view', user_id=current_user.id))
        else:
            flash(message, 'error')
            
    return render_template('profile/edit.html')

@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User account settings (password, dark mode)."""
    if request.method == 'POST':
        from ..services.user_service import UserService
        success, message = UserService.update_settings(current_user.id, request.form)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('profile.settings'))
        else:
            flash(message, 'error')
            
    return render_template('profile/settings.html')

@profile_bp.route('/delete', methods=['POST'])
@login_required
def delete_account():
    """Delete user account."""
    from ..services.user_service import UserService
    from flask_login import logout_user
    
    success, message = UserService.delete_account(current_user.id)
    if success:
        logout_user()
        flash('Your account has been successfully deleted.', 'success')
        return redirect(url_for('main.index'))
    else:
        flash(message, 'error')
        return redirect(url_for('profile.settings'))
