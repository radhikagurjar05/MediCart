import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

class ImageService:
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

    @staticmethod
    def process_and_save_product_image(file):
        """
        Processes an uploaded product image:
        - Validates extension
        - Generates secure, unique UUID filename
        - Resizes to max 1200px width/height while maintaining aspect ratio
        - Converts to WebP format for optimal web delivery
        - Saves to product uploads directory
        Returns relative URL path if successful, None otherwise.
        """
        if not file or not file.filename:
            return None
            
        if not ImageService.allowed_file(file.filename):
            return None

        try:
            # Open image with Pillow
            img = Image.open(file)
            
            # Convert to RGB if needed (e.g. PNG with transparency to WebP)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Resize logic (max 1200px on longest side)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Generate unique filename
            ext = 'webp'
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            
            # Ensure upload directory exists
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save as optimized WebP
            img.save(file_path, 'WEBP', quality=85, optimize=True)
            
            # Return URL path
            return f"/static/uploads/products/{unique_filename}"
            
        except Exception as e:
            current_app.logger.error(f"Image processing failed: {str(e)}")
            return None

    @staticmethod
    def delete_image(image_url):
        """Deletes an image file from the filesystem."""
        if not image_url or not image_url.startswith('/static/'):
            return False
            
        try:
            # Extract relative path without leading slash
            rel_path = image_url.lstrip('/')
            full_path = os.path.join(current_app.root_path, rel_path.replace('static/', 'static/', 1))
            
            if os.path.exists(full_path):
                os.remove(full_path)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to delete image {image_url}: {str(e)}")
            return False
