from app import create_app, db
from app.models import User, Category, Transaction, Budget
from werkzeug.security import generate_password_hash
import datetime

def init_db():
    """Inițializează baza de date cu date inițiale"""
    app = create_app()
    
    with app.app_context():
        # Recreează toate tabelele (șterge dacă există)
        db.drop_all()
        db.create_all()
        
        # Create a default admin user for testing purposes (optional)
        # You can comment this out if you don't want a default user
        admin_user = User(
            username='admin',
            email='admin@test.com',
            password=generate_password_hash('admin123')
        )
        db.session.add(admin_user)
        db.session.commit()
        
        # Create default categories for the admin user
        default_categories = [
            # Expense categories
            {'name': 'Alimente', 'type': 'expense', 'color': '#e74c3c'},
            {'name': 'Transport', 'type': 'expense', 'color': '#f39c12'},
            {'name': 'Utilități', 'type': 'expense', 'color': '#3498db'},
            {'name': 'Chirie/Rate', 'type': 'expense', 'color': '#9b59b6'},
            {'name': 'Îmbrăcăminte', 'type': 'expense', 'color': '#1abc9c'},
            {'name': 'Sănătate', 'type': 'expense', 'color': '#2ecc71'},
            {'name': 'Educație', 'type': 'expense', 'color': '#34495e'},
            {'name': 'Distracție', 'type': 'expense', 'color': '#e67e22'},
            # Income categories
            {'name': 'Salariu', 'type': 'income', 'color': '#27ae60'},
            {'name': 'Freelancing', 'type': 'income', 'color': '#2980b9'},
            {'name': 'Investiții', 'type': 'income', 'color': '#f39c12'},
            {'name': 'Cadouri', 'type': 'income', 'color': '#9b59b6'}
        ]
        
        categories = []
        for cat_data in default_categories:
            category = Category(
                name=cat_data['name'],
                type=cat_data['type'],
                color=cat_data['color'],
                user_id=admin_user.id  # Associate with the admin user
            )
            categories.append(category)
        
        db.session.add_all(categories)
        db.session.commit()
        
        print("Baza de date a fost inițializată cu succes!")
        print(f"Utilizator admin creat: admin@test.com / admin123")
        print(f"Au fost create {len(categories)} categorii implicite pentru utilizatorul admin.")
        print("Utilizatorii noi vor putea crea propriile categorii după înregistrare.")
        
if __name__ == "__main__":
    init_db()
