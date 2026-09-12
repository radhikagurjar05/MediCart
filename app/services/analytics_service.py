from ..extensions import db
from ..models.product import Product
from ..models.wishlist import Wishlist
from sqlalchemy import func

class AnalyticsService:
    @staticmethod
    def get_seller_stats(user_id):
        """Retrieve dashboard statistics for a specific seller."""
        
        # Total active listings
        active_listings_count = Product.query.filter_by(seller_id=user_id, status='active').count()
        
        # Total sold/exchanged
        sold_listings_count = Product.query.filter(Product.seller_id == user_id, Product.status.in_(['sold', 'exchanged'])).count()
        
        # Total views across all products by this seller
        total_views = db.session.query(func.sum(Product.views)).filter_by(seller_id=user_id).scalar() or 0
        
        # Total times items have been wishlisted
        wishlist_saves = db.session.query(func.count(Wishlist.id)).join(Product).filter(Product.seller_id == user_id).scalar() or 0
        
        return {
            'active_listings': active_listings_count,
            'sold_listings': sold_listings_count,
            'total_views': int(total_views),
            'wishlist_saves': wishlist_saves
        }
