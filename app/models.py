from . import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

class User(UserMixin, db.Model):
    # tabelul pentru utilizatori
    __tablename__ = 'user'
    # coloana de identificare unica
    id = db.Column(db.Integer, primary_key=True)    
    
    # Using private attributes with properties for case normalization
    _email = db.Column('email', db.String(120), unique=True, nullable=False)
    _username = db.Column('username', db.String(64), unique=True, nullable=False)
    
    # parola criptata
    password = db.Column(db.String(128), nullable=False)
    # data crearii contului
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # relatia cu tranzactiile (one-to-many)
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    # relatia cu categoriile (one-to-many)
    categories = db.relationship('Category', backref='user', lazy='dynamic')
    # relatia cu bugetele (one-to-many)
    budgets = db.relationship('Budget', backref='user', lazy='dynamic')

    @hybrid_property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        self._email = email.lower()

    @hybrid_property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username.lower()

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    # tabelul pentru categorii de tranzactii
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    # utilizatorul care a creat categoria
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    # tipul categoriei: 'income' sau 'expense'
    type = db.Column(db.String(10), nullable=False)
    # culoarea pentru afisare in grafice
    color = db.Column(db.String(7), default='#3498db')  # format hex: #RRGGBB
    # relatia cu tranzactiile (one-to-many)
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    # relatia cu bugetele (one-to-many)
    budgets = db.relationship('Budget', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name} ({self.type})>'

class Transaction(db.Model):
    # tabelul pentru tranzactii (venituri si cheltuieli)
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    # utilizatorul care a creat tranzactia
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # categoria tranzactiei
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    # descrierea tranzactiei
    description = db.Column(db.String(255))
    # suma (pozitiva pentru venituri, negativa pentru cheltuieli)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    # tipul tranzactiei: 'income' sau 'expense'
    type = db.Column(db.String(10), nullable=False)
    # data tranzactiei
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    # data si ora crearii in sistem
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.description}: {self.amount} ({self.type})>'

class Budget(db.Model):
    # tabelul pentru bugete
    __tablename__ = 'budget'
    id = db.Column(db.Integer, primary_key=True)
    # utilizatorul care a creat bugetul
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # categoria pentru care este setat bugetul
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    # suma alocata
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    # data de inceput a bugetului
    start_date = db.Column(db.Date, nullable=False)
    # data de sfarsit a bugetului
    end_date = db.Column(db.Date, nullable=False)
    # data crearii bugetului
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Budget for {self.user_id} on Cat {self.category_id}: {self.amount}>'
