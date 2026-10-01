import os
import uuid
import re
import io
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.utils
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False


class ImageService:
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

    @staticmethod
    def is_cloudinary_configured():
        """Check if Cloudinary credentials are provided and configure the SDK."""
        if not CLOUDINARY_AVAILABLE:
            return False
        
        c_url = current_app.config.get('CLOUDINARY_URL') or os.getenv('CLOUDINARY_URL')
        if c_url:
            cloudinary.config(cloudinary_url=c_url, secure=True)
            return True

        cloud_name = current_app.config.get('CLOUDINARY_CLOUD_NAME') or os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = current_app.config.get('CLOUDINARY_API_KEY') or os.getenv('CLOUDINARY_API_KEY')
        api_secret = current_app.config.get('CLOUDINARY_API_SECRET') or os.getenv('CLOUDINARY_API_SECRET')

        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            return True
        return False

    @staticmethod
    def process_and_save_product_image(file):
        """
        Processes and stores an uploaded product image:
        - If Cloudinary is configured, uploads directly to Cloudinary with optimization.
        - Otherwise, optimizes with Pillow and saves to local static uploads directory.
        Returns the persistent image URL if successful, None otherwise.
        """
        if not file or not file.filename:
            return None
            
        if not ImageService.allowed_file(file.filename):
            return None

        # 1. Cloudinary upload if configured
        if ImageService.is_cloudinary_configured():
            try:
                # Reset file stream position
                file.seek(0)
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="medicart/products",
                    resource_type="image",
                    transformation=[
                        {"width": 1200, "height": 1200, "crop": "limit"},
                        {"quality": "auto"},
                        {"fetch_format": "auto"}
                    ]
                )
                return upload_result.get('secure_url')
            except Exception as e:
                current_app.logger.error(f"Cloudinary product image upload failed: {str(e)}")
                # Fall back to local storage on error

        # 2. Local filesystem storage fallback
        try:
            file.seek(0)
            img = Image.open(file)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            ext = 'webp'
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, unique_filename)
            img.save(file_path, 'WEBP', quality=85, optimize=True)
            
            return f"/static/uploads/products/{unique_filename}"
            
        except Exception as e:
            current_app.logger.error(f"Local image processing failed: {str(e)}")
            return None

    @staticmethod
    def process_and_save_avatar(file, user_id):
        """
        Processes and stores a user avatar:
        - If Cloudinary is configured, uploads to Cloudinary with face detection crop.
        - Otherwise, crops/resizes with Pillow and saves to local avatar directory.
        """
        if not file or not file.filename:
            return None

        # 1. Cloudinary upload if configured
        if ImageService.is_cloudinary_configured():
            try:
                file.seek(0)
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="medicart/avatars",
                    resource_type="image",
                    transformation=[
                        {"width": 300, "height": 300, "crop": "fill", "gravity": "face"},
                        {"quality": "auto"},
                        {"fetch_format": "auto"}
                    ]
                )
                return upload_result.get('secure_url')
            except Exception as e:
                current_app.logger.error(f"Cloudinary avatar upload failed: {str(e)}")

        # 2. Local filesystem storage fallback
        try:
            file.seek(0)
            img = Image.open(file)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            img = img.crop((left, top, right, bottom))
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            
            filename = f"{uuid.uuid4().hex}.webp"
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars', str(user_id))
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, filename)
            img.save(filepath, 'WEBP', quality=85)
            
            return f"/static/uploads/avatars/{user_id}/{filename}"
        except Exception as e:
            current_app.logger.error(f"Local avatar processing failed: {str(e)}")
            return None

    @staticmethod
    def delete_image(image_url):
        """Deletes an image file from Cloudinary or local filesystem."""
        if not image_url:
            return False

        # If Cloudinary image URL
        if 'cloudinary.com' in image_url and ImageService.is_cloudinary_configured():
            try:
                match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[a-zA-Z0-9]+)?$', image_url)
                if match:
                    public_id = match.group(1)
                    cloudinary.uploader.destroy(public_id)
                    return True
            except Exception as e:
                current_app.logger.error(f"Failed to delete Cloudinary image {image_url}: {str(e)}")
                return False

        # If local static URL
        if image_url.startswith('/static/'):
            try:
                rel_path = image_url.lstrip('/')
                full_path = os.path.join(current_app.root_path, rel_path.replace('static/', 'static/', 1))
                if os.path.exists(full_path):
                    os.remove(full_path)
                return True
            except Exception as e:
                current_app.logger.error(f"Failed to delete local image {image_url}: {str(e)}")
                return False

        return False
