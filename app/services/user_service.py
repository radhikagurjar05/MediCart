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
            # Delete previous avatar if exists
            if user.avatar_url:
                ImageService.delete_image(user.avatar_url)
            
            avatar_url = ImageService.process_and_save_avatar(avatar_file, user.id)
            if avatar_url:
                user.avatar_url = avatar_url
            else:
                return False, "Failed to process and upload avatar image."
                
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
