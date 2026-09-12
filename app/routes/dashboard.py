from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models.product import Product
from ..services.analytics_service import AnalyticsService

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Render the seller dashboard."""
    stats = AnalyticsService.get_seller_stats(current_user.id)
    
    # Get all listings (active, sold, etc) for the management table
    all_listings = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    
    # For the chart, we could pass historical view data, but for now we'll pass static or basic aggregated data 
    # to Chart.js. In a real app, this would be a time-series query from product_views table.
    # For Phase 6 MVP, we'll just mock the last 7 days of views for demonstration.
    chart_data = {
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'data': [12, 19, 15, 25, 22, 30, 28] 
    }
    
    return render_template('dashboard/index.html', stats=stats, listings=all_listings, chart_data=chart_data)
