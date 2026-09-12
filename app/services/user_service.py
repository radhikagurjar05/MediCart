import os
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.user import User
from .image_service import ImageService
from flask import current_app

class UserService:
    @staticmethod
    def update_profile(user_id, data, avatar_file=None):
        """Update user profile information and optional avatar."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"
            
        user.name = data.get('name', user.name)
        user.bio = data.get('bio', user.bio)
        user.phone = data.get('phone', user.phone)
        
        if avatar_file and avatar_file.filename:
            # Process avatar via ImageService
            try:
                # We can reuse ImageService but we might want a different path.
                # However, ImageService currently hardcodes the 'products' path.
                # Let's write a direct avatar processing here or add it to ImageService.
                # For simplicity, we'll do it manually here for avatars.
                from PIL import Image
                import uuid
                
                filename = f"{uuid.uuid4().hex}.webp"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars', str(user.id))
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                
                # Open, convert to RGB, resize and save as WebP
                img = Image.open(avatar_file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Crop to square for avatars
                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                img = img.crop((left, top, right, bottom))
                img = img.resize((300, 300), Image.Resampling.LANCZOS)
                
                img.save(filepath, 'WEBP', quality=85)
                
                # Set URL
                user.avatar_url = f"/static/uploads/avatars/{user.id}/{filename}"
            except Exception as e:
                return False, f"Failed to upload avatar: {str(e)}"
                
        try:
            db.session.commit()
            return True, "Profile updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def update_settings(user_id, data):
        """Update settings including password and dark mode."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"
            
        # Update Dark Mode
        user.dark_mode = data.get('dark_mode') == 'on'
        
        # Update Password (if provided and user is local auth)
        if user.auth_provider == 'local':
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            if current_password or new_password:
                if not current_password:
                    return False, "Current password is required to set a new password."
                if not user.check_password(current_password):
                    return False, "Incorrect current password."
                if new_password != confirm_password:
                    return False, "New passwords do not match."
                if len(new_password) < 8:
                    return False, "New password must be at least 8 characters long."
                    
                user.set_password(new_password)
                
        try:
            db.session.commit()
            return True, "Settings updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
            
    @staticmethod
    def delete_account(user_id):
        """Delete user account and all associated data."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"
            
        try:
            db.session.delete(user)
            db.session.commit()
            return True, "Account deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete account: {str(e)}"
