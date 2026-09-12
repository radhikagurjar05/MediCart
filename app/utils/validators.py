import re

def is_valid_campus_email(email):
    """
    Validate that the email belongs to Medi-Caps University (@medicaps.ac.in).
    Example: EN23CS301712@medicaps.ac.in
    """
    if not email or '@' not in email:
        return False
    email = email.lower().strip()
    parts = email.split('@')
    if len(parts) != 2:
        return False
    username, domain = parts
    if not username:
        return False
    return domain == 'medicaps.ac.in'


def validate_password_strength(password):
    """
    Ensure password meets minimum criteria:
    - At least 8 characters
    - At least one letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-zA-Z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""
