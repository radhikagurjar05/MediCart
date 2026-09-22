from app import create_app, db
from app.models.category import Category

CATEGORIES = [
    {'name': 'Textbooks', 'slug': 'textbooks', 'icon': 'book-open'},
    {'name': 'Electronics', 'slug': 'electronics', 'icon': 'laptop'},
    {'name': 'Furniture', 'slug': 'furniture', 'icon': 'sofa'},
    {'name': 'Clothing', 'slug': 'clothing', 'icon': 'shirt'},
    {'name': 'Stationery', 'slug': 'stationery', 'icon': 'pen-tool'},
    {'name': 'Sports', 'slug': 'sports', 'icon': 'activity'},
    {'name': 'Cycles', 'slug': 'cycles', 'icon': 'bike'},
    {'name': 'Miscellaneous', 'slug': 'misc', 'icon': 'box'},
]

def seed_categories(app_instance=None):
    app = app_instance or create_app()
    with app.app_context():
        # Ensure all tables exist
        db.create_all()
        
        for cat_data in CATEGORIES:
            existing = Category.query.filter_by(slug=cat_data['slug']).first()
            if not existing:
                category = Category(**cat_data)
                db.session.add(category)
                print(f"Added category: {cat_data['name']}")
            else:
                print(f"Category already exists: {cat_data['name']}")
                
        # Create Admin User
        from app.models.user import User
        admin_email = 'admin@medicaps.ac.in'
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                name='Platform Admin',
                role='admin',
                auth_provider='local'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            print(f"Created default Admin user: {admin_email} (Password: admin123)")
        else:
            print("Admin user already exists.")
                
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_categories()
