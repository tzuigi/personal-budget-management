import os
import unittest
from datetime import datetime, date, timedelta
from app import create_app, db
from app.models import User, Category, Transaction, Budget
from werkzeug.security import generate_password_hash
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # Folosim o bază de date SQLite în memorie pentru teste
    WTF_CSRF_ENABLED = False

class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_creation(self):
        """Test pentru crearea unui utilizator nou"""
        u = User(username='test_user', email='test@example.com', 
                 password=generate_password_hash('password123'))
        db.session.add(u)
        db.session.commit()
        
        user = User.query.filter_by(email='test@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'test_user')
    
    def test_user_transaction_relationship(self):
        """Test pentru relația one-to-many între User și Transaction"""
        u = User(username='test_user', email='test@example.com', 
                 password=generate_password_hash('password123'))
        db.session.add(u)
        
        c = Category(name='Test Category', type='income', color='#FF0000')
        db.session.add(c)
        db.session.commit()
        
        t1 = Transaction(user_id=u.id, category_id=c.id, description='Test Transaction 1',
                        amount=100, type='income', date=date.today())
        t2 = Transaction(user_id=u.id, category_id=c.id, description='Test Transaction 2',
                        amount=200, type='income', date=date.today())
        
        db.session.add_all([t1, t2])
        db.session.commit()
        
        self.assertEqual(u.transactions.count(), 2)
        self.assertEqual(u.transactions.first().description, 'Test Transaction 1')

class CategoryModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_category_creation(self):
        """Test pentru crearea unei categorii noi"""
        c = Category(name='Test Category', type='income', color='#FF0000')
        db.session.add(c)
        db.session.commit()
        
        category = Category.query.filter_by(name='Test Category').first()
        self.assertIsNotNone(category)
        self.assertEqual(category.type, 'income')
        self.assertEqual(category.color, '#FF0000')
    
    def test_category_transaction_relationship(self):
        """Test pentru relația one-to-many între Category și Transaction"""
        u = User(username='test_user', email='test@example.com', 
                 password=generate_password_hash('password123'))
        db.session.add(u)
        
        c = Category(name='Test Category', type='income', color='#FF0000')
        db.session.add(c)
        db.session.commit()
        
        t1 = Transaction(user_id=u.id, category_id=c.id, description='Test Transaction 1',
                        amount=100, type='income', date=date.today())
        t2 = Transaction(user_id=u.id, category_id=c.id, description='Test Transaction 2',
                        amount=200, type='income', date=date.today())
        
        db.session.add_all([t1, t2])
        db.session.commit()
        
        self.assertEqual(c.transactions.count(), 2)
        transaction_descriptions = [t.description for t in c.transactions]
        self.assertIn('Test Transaction 1', transaction_descriptions)
        self.assertIn('Test Transaction 2', transaction_descriptions)

class TransactionModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user and category
        self.user = User(username='test_user', email='test@example.com', 
                        password=generate_password_hash('password123'))
        self.category = Category(name='Test Category', type='expense', color='#FF0000')
        db.session.add_all([self.user, self.category])
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_transaction_creation(self):
        """Test pentru crearea unei tranzacții noi"""
        t = Transaction(user_id=self.user.id, category_id=self.category.id,
                       description='Test Transaction', amount=100, 
                       type='expense', date=date.today())
        db.session.add(t)
        db.session.commit()
        
        transaction = Transaction.query.filter_by(description='Test Transaction').first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.type, 'expense')
        self.assertEqual(transaction.user_id, self.user.id)
        self.assertEqual(transaction.category_id, self.category.id)
    
    def test_transaction_relationships(self):
        """Test pentru relațiile many-to-one cu User și Category"""
        t = Transaction(user_id=self.user.id, category_id=self.category.id,
                       description='Test Transaction', amount=100, 
                       type='expense', date=date.today())
        db.session.add(t)
        db.session.commit()
        
        transaction = Transaction.query.filter_by(description='Test Transaction').first()
        self.assertEqual(transaction.user.username, 'test_user')
        self.assertEqual(transaction.category.name, 'Test Category')

class BudgetModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user and category
        self.user = User(username='test_user', email='test@example.com', 
                        password=generate_password_hash('password123'))
        self.category = Category(name='Test Category', type='expense', color='#FF0000')
        db.session.add_all([self.user, self.category])
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_budget_creation(self):
        """Test pentru crearea unui buget nou"""
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        b = Budget(user_id=self.user.id, category_id=self.category.id,
                  amount=1000, start_date=start_date, end_date=end_date)
        db.session.add(b)
        db.session.commit()
        
        budget = Budget.query.first()
        self.assertIsNotNone(budget)
        self.assertEqual(budget.amount, 1000)
        self.assertEqual(budget.user_id, self.user.id)
        self.assertEqual(budget.category_id, self.category.id)
        self.assertEqual(budget.start_date, start_date)
        self.assertEqual(budget.end_date, end_date)
    
    def test_budget_relationships(self):
        """Test pentru relațiile many-to-one cu User și Category"""
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        b = Budget(user_id=self.user.id, category_id=self.category.id,
                  amount=1000, start_date=start_date, end_date=end_date)
        db.session.add(b)
        db.session.commit()
        
        budget = Budget.query.first()
        self.assertEqual(budget.user.username, 'test_user')
        self.assertEqual(budget.category.name, 'Test Category')

if __name__ == '__main__':
    unittest.main()
