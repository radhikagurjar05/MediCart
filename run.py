import os
from urllib.parse import urlparse
import sqlalchemy as sa
from dotenv import load_dotenv
from app import create_app
from seed import seed_categories

# Load environment variables first
load_dotenv()

# Create the Flask application instance
app = create_app()

def initialize_database():
    """Automatically verify MySQL/Postgres connection and seed initial data if needed."""
    db_url = os.environ.get('DATABASE_URL')
    
    # Only attempt MySQL auto-creation for local MySQL databases
    if db_url and db_url.startswith('mysql'):
        parsed = urlparse(db_url)
        db_name = parsed.path.lstrip('/')
        server_url = f"{parsed.scheme}://{parsed.netloc}/"
        try:
            engine = sa.create_engine(server_url)
            with engine.connect() as conn:
                conn.execute(sa.text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
                print(f"[*] Verified MySQL database '{db_name}' exists.")
        except Exception as e:
            print(f"[!] MySQL notice: {e}")
            
    # Run seed logic safely
    try:
        seed_categories(app)
    except Exception as e:
        print(f"[!] Notice during initial seed: {e}")

# Run database setup within app context
with app.app_context():
    initialize_database()

if __name__ == '__main__':
    from app.extensions import socketio
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
