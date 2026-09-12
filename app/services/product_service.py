from ..extensions import db
from ..models.product import Product, ProductImage
from ..models.category import Category
from .image_service import ImageService

class ProductService:
    @staticmethod
    def create_product(seller_id, data, files):
        """Creates a new product listing with images."""
        try:
            # Basic validation
            category = Category.query.get(data.get('category_id'))
            if not category:
                return False, "Invalid category selected."
                
            # Parse price correctly
            price = data.get('price')
            if price == '':
                price = None
            elif price is not None:
                try:
                    price = float(price)
                    if price < 0:
                        return False, "Price cannot be negative."
                except ValueError:
                    return False, "Invalid price format."
                    
            is_exchangeable = data.get('is_exchangeable') == 'on'
            
            if price is None and not is_exchangeable:
                return False, "You must provide a price or mark it as exchangeable."

            # Create product record
            product = Product(
                seller_id=seller_id,
                category_id=category.id,
                title=data.get('title'),
                description=data.get('description'),
                price=price,
                is_exchangeable=is_exchangeable,
                exchange_preferences=data.get('exchange_preferences'),
                condition=data.get('condition', 'good'),
                status='active'
            )
            
            db.session.add(product)
            db.session.flush() # Get product ID
            
            # Process and attach images
            images = files.getlist('images')
            primary_set = False
            
            for file in images:
                if file and file.filename:
                    image_url = ImageService.process_and_save_product_image(file)
                    if image_url:
                        prod_img = ProductImage(
                            product_id=product.id,
                            image_url=image_url,
                            is_primary=not primary_set
                        )
                        db.session.add(prod_img)
                        primary_set = True
                        
            db.session.commit()
            return True, product.id
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating listing: {str(e)}"
            
    @staticmethod
    def get_product(product_id):
        """Retrieve a single active product by ID."""
        return Product.query.get(product_id)
        
    @staticmethod
    def get_all_active_products(
        category_slug=None, 
        search_query=None, 
        min_price=None,
        max_price=None,
        condition=None,
        is_exchangeable=None,
        page=1, 
        per_page=12
    ):
        """Retrieve active products with advanced filters and pagination."""
        query = Product.query.filter_by(status='active')
        
        if category_slug:
            query = query.join(Category).filter(Category.slug == category_slug)
            
        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Product.title.ilike(search) | Product.description.ilike(search))
            
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
            
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
            
        if condition:
            query = query.filter(Product.condition == condition)
            
        if is_exchangeable:
            query = query.filter(Product.is_exchangeable == True)
            
        return query.order_by(Product.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
    @staticmethod
    def update_product(product_id, user_id, data, is_admin=False):
        """Update a product listing."""
        product = Product.query.get(product_id)
        if not product:
            return False, "Product not found."
            
        if product.seller_id != user_id and not is_admin:
            return False, "Permission denied."
            
        try:
            # Basic validation
            category = Category.query.get(data.get('category_id'))
            if not category:
                return False, "Invalid category selected."
                
            price = data.get('price')
            if price == '':
                price = None
            elif price is not None:
                try:
                    price = float(price)
                    if price < 0:
                        return False, "Price cannot be negative."
                except ValueError:
                    return False, "Invalid price format."
                    
            is_exchangeable = data.get('is_exchangeable') == 'on'
            if price is None and not is_exchangeable:
                return False, "You must provide a price or mark it as exchangeable."

            # Update fields
            product.category_id = category.id
            product.title = data.get('title')
            product.description = data.get('description')
            product.price = price
            product.is_exchangeable = is_exchangeable
            product.exchange_preferences = data.get('exchange_preferences')
            product.condition = data.get('condition', product.condition)
            
            db.session.commit()
            return True, "Listing updated successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating listing: {str(e)}"

    @staticmethod
    def delete_product(product_id, user_id, is_admin=False):
        """Delete a product and its images."""
        product = Product.query.get(product_id)
        if not product:
            return False, "Product not found."
            
        if product.seller_id != user_id and not is_admin:
            return False, "You do not have permission to delete this listing."
            
        try:
            # Delete physical image files
            for img in product.images:
                ImageService.delete_image(img.image_url)
                
            db.session.delete(product)
            db.session.commit()
            return True, "Listing deleted successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting listing: {str(e)}"
            
    @staticmethod
    def update_status(product_id, user_id, new_status, is_admin=False):
        """Update product status (e.g. mark as sold)."""
        valid_statuses = ['active', 'sold', 'exchanged', 'delisted']
        if new_status not in valid_statuses:
            return False, "Invalid status."
            
        product = Product.query.get(product_id)
        if not product:
            return False, "Product not found."
            
        if product.seller_id != user_id and not is_admin:
            return False, "You do not have permission to modify this listing."
            
        try:
            product.status = new_status
            db.session.commit()
            return True, f"Listing marked as {new_status}."
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating status: {str(e)}"
