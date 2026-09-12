from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from ..services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, result = AuthService.register_user(name, email, password)
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result, 'error')
            
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'
        
        success, result = AuthService.login_user(email, password)
        
        if success:
            login_user(result, remember=remember)
            flash('Logged in successfully.', 'success')
            
            # Secure redirect back
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash(result, 'error')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/google/callback')
def google_login_callback():
    """Handle Google OAuth callback."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    try:
        from flask_dance.contrib.google import google
    except ImportError:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))
        
    if not google.authorized:
        flash('Google authentication failed or was cancelled.', 'error')
        return redirect(url_for('auth.login'))
        
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash('Failed to fetch user info from Google.', 'error')
            return redirect(url_for('auth.login'))
            
        user_info = resp.json()
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        success, result = AuthService.get_or_create_oauth_user(email, name, provider='google')
        
        if success:
            login_user(result)
            
            # If they have a picture from google, we could optionally save it to their profile.
            if user_info.get('picture') and not result.avatar_url:
                result.avatar_url = user_info['picture']
                from ..extensions import db
                db.session.commit()
                
            flash('Logged in successfully via Google.', 'success')
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash(result, 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('auth.login'))
