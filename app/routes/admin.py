from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ..utils.decorators import admin_required
from ..models.user import User
from ..models.product import Product
from ..models.report import Report
from ..extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@admin_required
def require_admin():
    """Ensure all routes in this blueprint require admin access."""
    pass

@admin_bp.route('/')
def index():
    """Admin dashboard stats."""
    stats = {
        'total_users': User.query.count(),
        'total_listings': Product.query.count(),
        'active_listings': Product.query.filter_by(status='active').count(),
        'pending_reports': Report.query.filter_by(status='pending').count()
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    return render_template('admin/index.html', stats=stats, recent_users=recent_users)

@admin_bp.route('/users')
def users():
    """Manage users."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle-ban', methods=['POST'])
def toggle_ban(user_id):
    """Ban or unban a user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot ban yourself.", "error")
        return redirect(url_for('admin.users'))
        
    user.is_banned = not user.is_banned
    db.session.commit()
    status = "banned" if user.is_banned else "unbanned"
    flash(f"User {user.display_name} has been {status}.", "success")
    return redirect(url_for('admin.users'))

@admin_bp.route('/listings')
def listings():
    """Manage all listings."""
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/listings.html', products=products)

@admin_bp.route('/listings/<int:product_id>/delete', methods=['POST'])
def delete_listing(product_id):
    """Admin forcefully delete a listing."""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Listing deleted by admin.', 'success')
    return redirect(url_for('admin.listings'))

@admin_bp.route('/reports')
def reports():
    """View and manage reports."""
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin/reports.html', reports=reports)

@admin_bp.route('/reports/<int:report_id>/dismiss', methods=['POST'])
def dismiss_report(report_id):
    """Dismiss a report."""
    report = Report.query.get_or_404(report_id)
    report.status = 'dismissed'
    db.session.commit()
    flash('Report dismissed.', 'success')
    return redirect(url_for('admin.reports'))
