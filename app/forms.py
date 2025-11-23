from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, DateField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Regexp
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import func

from .models import User, Category, Budget

class LoginForm(FlaskForm):
    """Formular pentru autentificarea utilizatorilor"""
    identifier = StringField('Email sau Nume utilizator', validators=[
        DataRequired(message='Câmpul pentru email sau nume utilizator este obligatoriu.')
    ])
    password = PasswordField('Parola', validators=[
        DataRequired(message='Câmpul pentru parolă este obligatoriu.')
    ])
    submit = SubmitField('Autentificare')

class RegistrationForm(FlaskForm):
    """Formular pentru înregistrarea utilizatorilor noi"""
    email = StringField('Email', validators=[
        DataRequired(message='Câmpul pentru email este obligatoriu.'), 
        Email(message='Adresa de email nu este validă.')
    ])
    username = StringField('Nume utilizator', validators=[
        DataRequired(message='Câmpul pentru nume utilizator este obligatoriu.'),
        Length(min=3, max=64, message='Numele de utilizator trebuie să aibă între 3 și 64 de caractere.'),
        Regexp('^[A-Za-z0-9_.]+$', message='Numele de utilizator poate conține doar litere, cifre, underscore și punct.')
    ])
    password = PasswordField('Parola', validators=[
        DataRequired(message='Câmpul pentru parolă este obligatoriu.'),
        Length(min=8, message='Parola trebuie să aibă cel puțin 8 caractere.'),
        Regexp(r'(?=.*\d)(?=.*[a-z])(?=.*[A-Z])', message='Parola trebuie să conțină cel puțin o literă mică, o literă mare și o cifră.')
    ])
    password2 = PasswordField('Confirmă parola', validators=[
        DataRequired(message='Câmpul pentru confirmarea parolei este obligatoriu.'),
        EqualTo('password', message='Parolele trebuie să coincidă.')
    ])
    submit = SubmitField('Înregistrare')
    
    def validate_email(self, email):
        """Validare pentru unicitatea adresei de email"""
        user = User.query.filter_by(_email=email.data.lower()).first()
        if user:
            raise ValidationError('Această adresă de email este deja utilizată. Te rugăm să alegi alta.')
            
    def validate_username(self, username):
        """Validare pentru unicitatea numelui de utilizator"""
        user = User.query.filter_by(_username=username.data.lower()).first()
        if user:
            raise ValidationError('Acest nume de utilizator este deja utilizat. Te rugăm să alegi altul.')

class TransactionForm(FlaskForm):
    """Formular pentru adăugarea și editarea tranzacțiilor"""
    description = StringField('Descriere', validators=[
        DataRequired(message='Câmpul pentru descriere este obligatoriu.'), 
        Length(max=255, message='Descrierea nu poate depăși 255 caractere.')
    ])
    amount = DecimalField('Sumă', validators=[
        DataRequired(message='Câmpul pentru sumă este obligatoriu.'),
        NumberRange(min=Decimal('0.01'), message='Suma trebuie să fie mai mare de 0.')
    ], places=2)
    type = SelectField('Tip', choices=[('income', 'Venit'), ('expense', 'Cheltuială')], validators=[
        DataRequired(message='Trebuie să selectezi tipul tranzacției.')
    ])
    category_id = SelectField('Categorie', coerce=int, validators=[
        DataRequired(message='Trebuie să selectezi o categorie.')
    ])
    date = DateField('Data', validators=[
        DataRequired(message='Câmpul pentru dată este obligatoriu.')
    ], default=date.today)
    submit = SubmitField('Salvează')
    
    def validate_date(self, field):
        """Validare pentru data tranzacției"""
        if field.data > date.today():
            raise ValidationError('Data tranzacției nu poate fi în viitor.')
        
        # Verificăm și dacă data nu este exagerat de veche (ex: mai veche de 100 ani)
        min_date = date.today().replace(year=date.today().year - 100)
        if field.data < min_date:
            raise ValidationError('Data tranzacției este prea veche.')
    
    def validate_category_id(self, field):
        """Validare pentru potrivirea tipului de categorie cu tipul tranzacției"""
        category = Category.query.get(field.data)
        if not category:
            raise ValidationError('Categoria selectată nu există.')
        if category.type != self.type.data:
            raise ValidationError(f'Categoria selectată nu este de tipul {self.type.data}.')
    
    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        # Vom popula opțiunile pentru categorie în routes.py în funcție de tipul tranzacției

class CategoryForm(FlaskForm):
    """Formular pentru adăugarea și editarea categoriilor"""
    name = StringField('Nume', validators=[
        DataRequired(message='Câmpul pentru nume este obligatoriu.'), 
        Length(max=64, message='Numele nu poate depăși 64 caractere.')
    ])
    type = SelectField('Tip', choices=[('income', 'Venit'), ('expense', 'Cheltuială')], validators=[
        DataRequired(message='Trebuie să selectezi tipul categoriei.')
    ])
    color = StringField('Culoare (hex)', default='#3498db', validators=[
        DataRequired(message='Câmpul pentru culoare este obligatoriu.'),
        Length(min=7, max=7, message='Codul de culoare trebuie să aibă exact 7 caractere (format #RRGGBB).'),
        Regexp('^#[0-9A-Fa-f]{6}$', message='Codul de culoare trebuie să fie în format #RRGGBB (exemplu: #3498db).')
    ])
    submit = SubmitField('Salvează')
    
    def validate_name(self, field):
        """Validare pentru unicitatea numelui categoriei"""
        category = Category.query.filter(func.lower(Category.name) == field.data.lower()).first()
        if category and (not hasattr(self, '_obj') or category.id != self._obj.id):
            raise ValidationError('Acest nume de categorie există deja. Te rugăm să alegi altul.')

class BudgetForm(FlaskForm):
    """Formular pentru setarea bugetelor"""
    category_id = SelectField('Categorie', coerce=int, validators=[
        DataRequired(message='Trebuie să selectezi o categorie.')
    ])
    amount = DecimalField('Suma alocată', validators=[
        DataRequired(message='Câmpul pentru sumă este obligatoriu.'),
        NumberRange(min=Decimal('0.01'), message='Suma trebuie să fie mai mare de 0.')
    ], places=2)
    start_date = DateField('Data de început', validators=[
        DataRequired(message='Câmpul pentru data de început este obligatoriu.')
    ], default=date.today)
    end_date = DateField('Data de sfârșit', validators=[
        DataRequired(message='Câmpul pentru data de sfârșit este obligatoriu.')
    ])
    submit = SubmitField('Setează buget')
    
    def validate_category_id(self, field):
        """Validare pentru tipul categoriei (doar expense)"""
        category = Category.query.get(field.data)
        if not category:
            raise ValidationError('Categoria selectată nu există.')
        if category.type != 'expense':
            raise ValidationError('Bugetele pot fi setate doar pentru categorii de cheltuieli.')
    
    def validate_start_date(self, field):
        """Validare pentru data de început"""
        # Restricționăm bugetele la perioada rezonabilă (max 5 ani în trecut)
        min_date = date.today().replace(year=date.today().year - 5)
        if field.data < min_date:
            raise ValidationError('Data de început nu poate fi mai veche de 5 ani.')
    
    def validate_end_date(self, field):
        """Validare pentru data de sfârșit a bugetului"""
        if not self.start_date.data:
            return
            
        # Verificăm dacă există dată de început setată
        if field.data < self.start_date.data:
            raise ValidationError('Data de sfârșit trebuie să fie după data de început.')
            
        # Restricționăm durata bugetelor (max 5 ani)
        max_duration = 365 * 5  # 5 ani
        if (field.data - self.start_date.data).days > max_duration:
            raise ValidationError('Durata bugetului nu poate depăși 5 ani.')
            
        # Verificăm dacă data de sfârșit nu este prea mult în viitor (max 3 ani)
        max_future = date.today().replace(year=date.today().year + 3)
        if field.data > max_future:
            raise ValidationError('Data de sfârșit nu poate fi mai departe de 3 ani în viitor.')
    
    def validate(self):
        """Validare pentru suprapunerea bugetelor"""
        if not super(BudgetForm, self).validate():
            return False
        
        # Verifică suprapunerea cu alte bugete pentru aceeași categorie
        from flask_login import current_user
        overlapping_budgets = Budget.query.filter(
            Budget.user_id == current_user.id,
            Budget.category_id == self.category_id.data,
            Budget.start_date <= self.end_date.data,
            Budget.end_date >= self.start_date.data
        ).all()
        
        # Dacă edităm un buget existent, excludem bugetul curent
        if hasattr(self, '_obj') and self._obj:
            overlapping_budgets = [b for b in overlapping_budgets if b.id != self._obj.id]
        
        if overlapping_budgets:
            self.category_id.errors.append('Există deja un buget pentru această categorie în perioada selectată.')
            return False
        
        return True
    
    def __init__(self, *args, **kwargs):
        super(BudgetForm, self).__init__(*args, **kwargs)
        # Vom popula opțiunile pentru categorie în routes.py (doar categorii de cheltuieli)

class ImportTransactionsForm(FlaskForm):
    """Formular pentru importarea tranzacțiilor din CSV"""
    file = FileField('Fișier CSV', validators=[
        DataRequired(message='Trebuie să selectezi un fișier CSV pentru import.')
    ])
    submit = SubmitField('Importă')
    
    def validate_file(self, field):
        """Validare pentru formatul fișierului"""
        if not field.data.filename.endswith('.csv'):
            raise ValidationError('Fișierul trebuie să fie în format CSV.')