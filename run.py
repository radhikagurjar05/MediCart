import os
from urllib.parse import urlparse
import sqlalchemy as sa
from dotenv import load_dotenv
from app import create_app
from seed import seed_categories

# Load environment variables first
load_dotenv()

def initialize_database():
    """Automatically create the database if it doesn't exist and run seeds."""
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url and db_url.startswith('mysql'):
        parsed = urlparse(db_url)
        db_name = parsed.path.lstrip('/')
        
        # Create a connection URL to the server (without the specific database)
        server_url = f"{parsed.scheme}://{parsed.netloc}/"
        
        try:
            # Connect to MySQL server to ensure database exists
            engine = sa.create_engine(server_url)
            with engine.connect() as conn:
                conn.execute(sa.text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
                print(f"[*] Verified MySQL database '{db_name}' exists.")
        except Exception as e:
            print(f"[!] CRITICAL: Could not connect to MySQL. Access Denied or server offline.")
            print(f"[!] Please ensure your DATABASE_URL in .env is completely correct.")
            print(f"[!] Error Details: {e}")
            import sys
            sys.exit(1)
            
    # Run the seed logic (which creates tables via db.create_all() and adds initial data)
    print("[*] Ensuring database tables and default data exist...")
    seed_categories()

# 1. First, automatically initialize/verify the database
initialize_database()

# 2. Then, create the Flask app for serving
app = create_app()

if __name__ == '__main__':
    from app.extensions import socketio
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
