from flask import Blueprint, render_template, request
from ..services.product_service import ProductService
from ..models.category import Category

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page with hero, categories, featured listings, and how-it-works."""
    categories = Category.query.all()
    # Fetch latest 8 products for the feed
    recent_products = ProductService.get_all_active_products(per_page=8).items
    return render_template('main/index.html', categories=categories, recent_products=recent_products)

@main_bp.route('/explore')
def explore():
    """Advanced search, filtering, and browsing."""
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    cat_slug = request.args.get('category', '')
    condition = request.args.get('condition', '')
    is_exchangeable = request.args.get('exchange', type=bool)
    
    # Handle min/max price specifically handling empty strings from the form
    min_price_str = request.args.get('min_price', '')
    max_price_str = request.args.get('max_price', '')
    
    min_price = float(min_price_str) if min_price_str else None
    max_price = float(max_price_str) if max_price_str else None

    products_pagination = ProductService.get_all_active_products(
        category_slug=cat_slug,
        search_query=q,
        min_price=min_price,
        max_price=max_price,
        condition=condition,
        is_exchangeable=is_exchangeable,
        page=page,
        per_page=12
    )
    
    categories = Category.query.all()
    return render_template('main/explore.html', 
                           products=products_pagination, 
                           categories=categories,
                           request_args=request.args)


@main_bp.route('/about')
def about():
    """About MediCart page."""
    return render_template('main/about.html')


@main_bp.app_errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return render_template('main/404.html'), 404
