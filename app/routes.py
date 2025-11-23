from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, current_app
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from .models import Category, Transaction, Budget, User
from .forms import LoginForm, RegistrationForm, CategoryForm, TransactionForm, BudgetForm, ImportTransactionsForm
from . import db, limiter
from datetime import datetime, date, timedelta
from sqlalchemy import func, Integer
import csv
import io
import decimal
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import calendar
import os
from .utils import S3Util
import re
import locale
from decimal import InvalidOperation

main_bp = Blueprint(
    'main',               # numele blueprint-ului
    __name__,             # import_name
    template_folder='templates'  # cale explicita catre sabloane
)

# Rutele pentru autentificare și înregistrare
@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Protecție împotriva atacurilor de tip brute-force
def login():
    # Dacă utilizatorul este deja autentificat, redirectionăm la pagina principală
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Convertim identificatorul la lowercase pentru comparație case-insensitivă
        identifier = form.identifier.data.lower() if form.identifier.data else None
        
        # Verificăm dacă identificatorul este un email sau un nume de utilizator
        user = User.query.filter((func.lower(User.email) == identifier) | 
                               (func.lower(User.username) == identifier)).first()
        
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            # Redirectare către pagina cerută inițial sau către dashboard
            return redirect(next_page or url_for('main.index'))
        flash('Email, nume utilizator sau parolă incorectă.', 'danger')
    
    return render_template('login.html', form=form)

@main_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute") # Limitare pentru înregistrări
def register():
    # Dacă utilizatorul este deja autentificat, redirectionăm la pagina principală
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            email=form.email.data,
            username=form.username.data,
            password=hashed_password
        )
        try:
            db.session.add(user)
            db.session.commit()
            flash('Contul a fost creat cu succes! Te poți autentifica acum.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la înregistrarea utilizatorului {form.email.data}: {str(e)}")
            flash(f'A apărut o eroare la crearea contului: {str(e)}', 'danger')
    
    return render_template('register.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Te-ai deconectat cu succes.', 'info')
    return redirect(url_for('main.login'))

# Rută pentru pagina principală (dashboard)
@main_bp.route('/')
@login_required
def index():
    # Calcularea soldului curent
    income = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='income').scalar() or 0
    expense = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='expense').scalar() or 0
    balance = income - expense
    
    # Preluarea ultimelor 5 tranzacții
    recent_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()
    
    # Date pentru grafice
    # Cheltuieli pe categorii pentru luna curentă
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    end_of_month = date(today.year, today.month, 
                        calendar.monthrange(today.year, today.month)[1])
    
    category_expenses = db.session.query(
        Category.name, Category.color, func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_of_month,
        Transaction.date <= end_of_month
    ).group_by(Category.name, Category.color).all()
    
    # Transformare pentru Chart.js
    category_labels = [item[0] for item in category_expenses]
    category_values = [item[2] for item in category_expenses]
    category_colors = [item[1] for item in category_expenses]
    
    # Tranzacții zilnice pentru ultimele 30 zile
    thirty_days_ago = today - timedelta(days=30)
    
    daily_transactions = db.session.query(
        func.date(Transaction.date).label('day'), 
        func.sum(Transaction.amount).label('income_sum')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= thirty_days_ago
    ).group_by(func.date(Transaction.date)).all()
    
    daily_expenses = db.session.query(
        func.date(Transaction.date).label('day'), 
        func.sum(Transaction.amount).label('expense_sum')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= thirty_days_ago
    ).group_by(func.date(Transaction.date)).all()
    
    # Preluarea alertelor pentru bugete depășite
    budget_alerts = []
    active_budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.start_date <= today,
        Budget.end_date >= today
    ).all()
    
    for budget in active_budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == budget.category_id,
            Transaction.date >= budget.start_date,
            Transaction.date <= budget.end_date
        ).scalar() or 0
        
        if spent > budget.amount:
            budget_alerts.append({
                'category': budget.category.name,
                'budget': budget.amount,
                'spent': spent,
                'overspent': spent - budget.amount
            })
    
    return render_template('index.html',
                          balance=balance,
                          income=income,
                          expense=expense,
                          recent_transactions=recent_transactions,
                          category_labels=category_labels,
                          category_values=category_values,
                          category_colors=category_colors,
                          budget_alerts=budget_alerts)

# Rute pentru gestionarea tranzacțiilor
@main_bp.route('/transactions')
@login_required
def transactions():
    # Parametri pentru filtrare
    type_filter = request.args.get('type', 'all')
    category_id = request.args.get('category_id', None)
    
    # Construim query-ul de bază
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Aplicăm filtrele
    if type_filter != 'all':
        query = query.filter_by(type=type_filter)
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    
    # Sortare și paginare
    transactions = query.order_by(Transaction.date.desc()).all()
    
    # Preluăm categoriile pentru filtrul dropdown
    categories = Category.query.all()
    
    return render_template('transactions.html', 
                          transactions=transactions, 
                          categories=categories,
                          type_filter=type_filter,
                          category_id=category_id)

@main_bp.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    
    # Populăm opțiunile de categorii (dinamice în funcție de tipul ales)
    categories = Category.query.filter(Category.user_id == current_user.id).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        transaction = Transaction(
            user_id=current_user.id,
            description=form.description.data,
            amount=form.amount.data,
            type=form.type.data,
            category_id=form.category_id.data,
            date=form.date.data
        )
        try:
            db.session.add(transaction)
            db.session.commit()
            flash('Tranzacție adăugată cu succes!', 'success')
            return redirect(url_for('main.transactions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la adăugarea tranzacției pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la adăugarea tranzacției: {str(e)}', 'danger')
        
    return render_template('add_transaction.html', form=form)

@main_bp.route('/edit_transaction/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    # Verificăm dacă utilizatorul are dreptul să editeze această tranzacție
    if transaction.user_id != current_user.id:
        flash('Nu ai permisiunea să editezi această tranzacție.', 'danger')
        return redirect(url_for('main.transactions'))
    
    form = TransactionForm(obj=transaction)
    
    # Populăm opțiunile de categorii
    categories = Category.query.filter(Category.user_id == current_user.id).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        transaction.description = form.description.data
        transaction.amount = form.amount.data
        transaction.type = form.type.data
        transaction.category_id = form.category_id.data
        transaction.date = form.date.data
        
        try:
            db.session.commit()
            flash('Tranzacție actualizată cu succes!', 'success')
            return redirect(url_for('main.transactions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la actualizarea tranzacției #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la actualizarea tranzacției: {str(e)}', 'danger')
        
    return render_template('edit_transaction.html', form=form, transaction=transaction)

@main_bp.route('/delete_transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    # Verificăm dacă utilizatorul are dreptul să șteargă această tranzacție
    if transaction.user_id != current_user.id:
        flash('Nu ai permisiunea să ștergi această tranzacție.', 'danger')
        return redirect(url_for('main.transactions'))
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        flash('Tranzacție ștearsă cu succes!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Eroare la ștergerea tranzacției #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
        flash(f'A apărut o eroare la ștergerea tranzacției: {str(e)}', 'danger')
    return redirect(url_for('main.transactions'))

# Rute pentru gestionarea categoriilor
@main_bp.route('/categories')
@login_required
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@main_bp.route('/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            type=form.type.data,
            color=form.color.data,
            user_id=current_user.id
        )
        try:
            db.session.add(category)
            db.session.commit()
            flash('Categorie adăugată cu succes!', 'success')
            return redirect(url_for('main.categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la adăugarea categoriei '{form.name.data}' pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la adăugarea categoriei: {str(e)}', 'danger')
        
    return render_template('add_category.html', form=form)

@main_bp.route('/edit_category/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    # Ensure user can only edit their own categories
    if category.user_id != current_user.id:
        flash('Nu aveți permisiunea să editați această categorie.', 'danger')
        return redirect(url_for('main.categories'))
        
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.type = form.type.data
        category.color = form.color.data
        
        try:
            db.session.commit()
            flash('Categorie actualizată cu succes!', 'success')
            return redirect(url_for('main.categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la actualizarea categoriei #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la actualizarea categoriei: {str(e)}', 'danger')
        
    return render_template('edit_category.html', form=form, category=category)

@main_bp.route('/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    # Ensure user can only delete their own categories
    if category.user_id != current_user.id:
        flash('Nu aveți permisiunea să ștergeți această categorie.', 'danger')
        return redirect(url_for('main.categories'))
    
    # Verificăm dacă există tranzacții sau bugete asociate acestei categorii
    transactions_count = Transaction.query.filter_by(category_id=id, user_id=current_user.id).count()
    budgets_count = Budget.query.filter_by(category_id=id, user_id=current_user.id).count()
    
    if transactions_count > 0 or budgets_count > 0:
        flash('Nu se poate șterge această categorie deoarece există tranzacții sau bugete asociate.', 'danger')
        return redirect(url_for('main.categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Categorie ștearsă cu succes!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Eroare la ștergerea categoriei #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
        flash(f'A apărut o eroare la ștergerea categoriei: {str(e)}', 'danger')
    return redirect(url_for('main.categories'))

# Rute pentru gestionarea bugetelor
@main_bp.route('/budgets')
@login_required
def budgets():
    active_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    # Calculăm cât s-a cheltuit din fiecare buget
    for budget in active_budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == budget.category_id,
            Transaction.date >= budget.start_date,
            Transaction.date <= budget.end_date
        ).scalar() or 0
        
        budget.spent = spent
        budget.percentage = (spent / budget.amount) * 100 if budget.amount > 0 else 0
        
    return render_template('budgets.html', budgets=active_budgets)

@main_bp.route('/add_budget', methods=['GET', 'POST'])
@login_required
def add_budget():
    form = BudgetForm()
    
    # Populăm opțiunile de categorii (doar cele de tip expense ale utilizatorului curent)
    expense_categories = Category.query.filter_by(type='expense', user_id=current_user.id).all()
    form.category_id.choices = [(c.id, c.name) for c in expense_categories]
    
    if form.validate_on_submit():
        budget = Budget(
            user_id=current_user.id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data
        )
        try:
            db.session.add(budget)
            db.session.commit()
            flash('Buget setat cu succes!', 'success')
            return redirect(url_for('main.budgets'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la adăugarea bugetului pentru categoria #{form.category_id.data} și utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la setarea bugetului: {str(e)}', 'danger')
            
    return render_template('add_budget.html', form=form)

@main_bp.route('/edit_budget/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_budget(id):
    budget = Budget.query.get_or_404(id)
    
    # Verificăm dacă utilizatorul are dreptul să editeze acest buget
    if budget.user_id != current_user.id:
        flash('Nu ai permisiunea să editezi acest buget.', 'danger')
        return redirect(url_for('main.budgets'))
    
    form = BudgetForm(obj=budget)
    
    # Populăm opțiunile de categorii (doar cele de tip expense ale utilizatorului curent)
    expense_categories = Category.query.filter_by(type='expense', user_id=current_user.id).all()
    form.category_id.choices = [(c.id, c.name) for c in expense_categories]
    
    if form.validate_on_submit():
        budget.category_id = form.category_id.data
        budget.amount = form.amount.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data
        
        try:
            db.session.commit()
            flash('Buget actualizat cu succes!', 'success')
            return redirect(url_for('main.budgets'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Eroare la actualizarea bugetului #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la actualizarea bugetului: {str(e)}', 'danger')
            
    return render_template('edit_budget.html', form=form, budget=budget)

@main_bp.route('/delete_budget/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    budget = Budget.query.get_or_404(id)
    
    # Verificăm dacă utilizatorul are dreptul să ștergă acest buget
    if budget.user_id != current_user.id:
        flash('Nu ai permisiunea să ștergi acest buget.', 'danger')
        return redirect(url_for('main.budgets'))
    
    try:
        db.session.delete(budget)
        db.session.commit()
        flash('Buget șters cu succes!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Eroare la ștergerea bugetului #{id} pentru utilizatorul #{current_user.id}: {str(e)}")
        flash(f'A apărut o eroare la ștergerea bugetului: {str(e)}', 'danger')
    return redirect(url_for('main.budgets'))

# Rută pentru rapoarte
@main_bp.route('/reports')
@login_required
def reports():
    # Determinăm perioada de raportare din parametrii URL sau folosim luna curentă
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Calculăm prima și ultima zi din lună
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    # Venituri și cheltuieli pe categorii pentru perioada selectată
    income_by_category = db.session.query(
        Category.name, Category.color, func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).group_by(Category.name, Category.color).all()
    
    expense_by_category = db.session.query(
        Category.name, Category.color, func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).group_by(Category.name, Category.color).all()
    
    # Date pentru Chart.js
    income_labels = [item[0] for item in income_by_category]
    income_values = [item[2] for item in income_by_category]
    income_colors = [item[1] for item in income_by_category]
    
    expense_labels = [item[0] for item in expense_by_category]
    expense_values = [item[2] for item in expense_by_category]
    expense_colors = [item[1] for item in expense_by_category]
      # Calculare totale
    total_income = sum(income_values) if income_values else 0
    total_expense = sum(expense_values) if expense_values else 0
    balance = total_income - total_expense
    
    # Generarea listei de luni pentru selector
    months = []
    for i in range(1, 13):
        months.append({
            'value': i,
            'name': calendar.month_name[i]
        })
    
    # Generarea listei de ani (ultimii 5 ani)
    current_year = datetime.now().year
    years = list(range(current_year - 4, current_year + 1))
    
    # Date zilnice pentru graficul de evoluție a soldului
    days_in_month = calendar.monthrange(year, month)[1]
    day_labels = [str(d) for d in range(1, days_in_month + 1)]
    
    # Inițializare cu zerouri
    day_incomes = [0] * days_in_month
    day_expenses = [0] * days_in_month
    day_balances = [0] * days_in_month
    
    # Obținerea tranzacțiilor zilnice pentru venituri
    daily_incomes = db.session.query(
        func.cast(func.strftime('%d', Transaction.date).label('day'), Integer), 
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        func.strftime('%Y', Transaction.date) == str(year),
        func.strftime('%m', Transaction.date) == str(month).zfill(2)
    ).group_by(func.strftime('%d', Transaction.date)).all()
    
    # Obținerea tranzacțiilor zilnice pentru cheltuieli
    daily_expenses = db.session.query(
        func.cast(func.strftime('%d', Transaction.date).label('day'), Integer), 
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        func.strftime('%Y', Transaction.date) == str(year),
        func.strftime('%m', Transaction.date) == str(month).zfill(2)
    ).group_by(func.strftime('%d', Transaction.date)).all()
    
    # Popularea listelor pentru venituri și cheltuieli
    for day, amount in daily_incomes:
        day_incomes[day - 1] = float(amount)
    
    for day, amount in daily_expenses:
        day_expenses[day - 1] = float(amount)
    
    # Calcularea soldului cumulativ
    running_balance = 0
    for i in range(days_in_month):
        running_balance += day_incomes[i] - day_expenses[i]
        day_balances[i] = running_balance
    
    return render_template('reports.html',
                          year=year,
                          month=month,
                          months=months,
                          years=years,
                          total_income=total_income,
                          total_expense=total_expense,
                          balance=balance,
                          income_labels=income_labels,
                          income_values=income_values,
                          income_colors=income_colors,
                          expense_labels=expense_labels,
                          expense_values=expense_values,
                          expense_colors=expense_colors,
                          day_labels=day_labels,
                          day_incomes=day_incomes,
                          day_expenses=day_expenses,
                          day_balances=day_balances)

# Rute pentru importul și exportul de date
@main_bp.route('/export_transactions_csv')
@login_required
def export_transactions_csv():
    # Preluare parametri de filtrare
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    try:
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if start_date > end_date: # Basic validation
                flash('Data de început nu poate fi după data de sfârșit. Se folosesc ultimele 30 de zile.', 'warning')
                end_date = date.today()
                start_date = end_date - timedelta(days=30)
        else:
            # Implicit: ultimele 30 de zile
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
    except ValueError:
        flash('Format dată invalid pentru export. Se folosesc ultimele 30 de zile.', 'warning')
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    # Preluare tranzacții pentru intervalul selectat
    transactions_query = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date.desc())
    
    transactions_list = transactions_query.all()
    
    # Creare fișier CSV în memorie
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Scriere antet
    writer.writerow(['ID', 'Data', 'Descriere', 'Categorie', 'Tip', 'Sumă'])
    
    # Scriere date
    for transaction_item in transactions_list: # Renamed to avoid conflict
        writer.writerow([
            transaction_item.id,
            transaction_item.date.strftime('%Y-%m-%d'),
            transaction_item.description,
            transaction_item.category.name if transaction_item.category else 'N/A',
            transaction_item.type,
            f"{transaction_item.amount:.2f}" # Ensure amount is formatted
        ])
    
    # Încercare încărcare în S3
    s3_upload_successful = False
    if current_app.config.get('AWS_ACCESS_KEY_ID') and current_app.config.get('AWS_SECRET_ACCESS_KEY') and current_app.config.get('S3_BUCKET'):
        try:
            output.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # Ensure 'exports' and user-specific directory exists for S3 object name convention
            s3_object_name = f"exports/{current_user.id}/transactions_{start_date}_{end_date}_{timestamp}.csv"
            
            # Convert StringIO to BytesIO for S3Util if it expects bytes
            csv_bytes = io.BytesIO(output.getvalue().encode('utf-8'))
            s3_url = S3Util.upload_file(csv_bytes, s3_object_name, public=True) # Assuming public for direct link
            
            if s3_url and s3_url.startswith('http'):
                flash(f'Fișierul CSV a fost exportat și încărcat în S3. Îl puteți descărca de aici: <a href="{s3_url}" target="_blank">{s3_object_name}</a>', 'success')
                s3_upload_successful = True
                return redirect(url_for('main.transactions')) # Redirect to transactions or another appropriate page
            else:
                current_app.logger.error(f"Încărcarea CSV în S3 a eșuat: URL invalid sau lipsă pentru utilizatorul #{current_user.id}")
                flash('Încărcarea în S3 a eșuat. Se încearcă descărcarea directă.', 'warning')
        except Exception as e:
            current_app.logger.error(f"Eroare S3 la exportul CSV pentru utilizatorul #{current_user.id}: {str(e)}")
            flash(f'A apărut o eroare la încărcarea în S3: {str(e)}. Se încearcă descărcarea directă.', 'danger')
    else:
        current_app.logger.info(f"Configurarea S3 lipsește, se folosește download direct pentru CSV, utilizator #{current_user.id}")
        flash('Configurația S3 lipsește. Fișierul va fi descărcat direct.', 'info')

    # Fallback to direct download if S3 is not configured or upload failed
    if not s3_upload_successful:
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=tranzactii_{start_date}_to_{end_date}.csv"}
        )
    # This part should ideally not be reached if s3_upload_successful is true due to redirect
    return redirect(url_for('main.transactions')) 

@main_bp.route('/get_categories_by_type/<type>')
@login_required
def get_categories_by_type(type):
    categories = Category.query.filter_by(type=type).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in categories])

@main_bp.route('/import_transactions', methods=['GET', 'POST'])
@login_required
def import_transactions():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nu a fost selectat niciun fișier.', 'error')
            return redirect(url_for('main.import_transactions'))
        
        file = request.files['file']
        if file.filename == '':
            flash('Nu a fost selectat niciun fișier.', 'error')
            return redirect(url_for('main.import_transactions'))
        
        processed_transactions = False
        if file:
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext == '.csv':
                file.stream.seek(0)  # Ensure stream is at the beginning
                reader = csv.reader(io.TextIOWrapper(file.stream, encoding='utf-8-sig'))
                transactions_to_add_models = []
                header_found_and_skipped = False
                date_regex = re.compile(r'^\d{2} [A-Za-zăâîșțĂÂÎȘȚ]+ \d{4}$')  # Accept capitalized months
                current_app.logger.info(f"Starting CSV import for user {current_user.id}, file: {filename}")
                # Log current locale for date parsing
                try:
                    current_time_locale = locale.getlocale(locale.LC_TIME)
                    current_app.logger.info(f"Current LC_TIME locale before processing rows: {current_time_locale}")
                except Exception as e:
                    current_app.logger.warning(f"Could not get LC_TIME locale: {e}")
                
                # Set Romanian locale for date parsing
                try:
                    current_app.logger.info("Attempting to set Romanian locale")
                    # Try multiple possible Romanian locale names
                    for loc in ['ro_RO.UTF-8', 'ro_RO.utf8', 'ro_RO', 'ro']:
                        try:
                            locale.setlocale(locale.LC_TIME, loc)
                            current_app.logger.info(f"Successfully set LC_TIME locale to {loc}")
                            break
                        except locale.Error:
                            continue
                except Exception as e:
                    current_app.logger.warning(f"Could not set Romanian locale: {e}")
                
                rows = list(reader)
                r_idx = 0
                while r_idx < len(rows):
                    row_list = rows[r_idx]
                    if not row_list:
                        r_idx += 1
                        continue
                    if not header_found_and_skipped:
                        if len(row_list) > 8 and row_list[1].strip() == "Data" and \
                           "Detalii tranzactie" in row_list[4] and \
                           "Debit" in row_list[7] and "Credit" in row_list[8]:
                            header_found_and_skipped = True
                            current_app.logger.info(f"ING CSV header found and skipped at row {r_idx}.")
                        r_idx += 1
                        continue
                    if not header_found_and_skipped:
                        r_idx += 1
                        continue
                    if len(row_list) > 8:
                        date_candidate = row_list[0].strip()
                        if date_regex.match(date_candidate):
                            current_app.logger.debug(f"Processing potential data row {r_idx}: {row_list[:9]}")
                            try:
                                date_str = date_candidate
                                detalii_str = row_list[4].strip() if len(row_list) > 4 else ''
                                debit_str_raw = row_list[6].strip()
                                credit_str_raw = row_list[8].strip()
                                current_app.logger.debug(f"Attempting to parse date: '{date_str}'")
                                try:
                                    parsed_date = datetime.strptime(date_str, '%d %B %Y').date()
                                    current_app.logger.debug(f"Successfully parsed date: {parsed_date}")
                                except ValueError:
                                    # Fallback: manual mapping for Romanian month names
                                    ro_months = {
                                        'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4,
                                        'mai': 5, 'iunie': 6, 'iulie': 7, 'august': 8,
                                        'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
                                    }
                                    parts = date_str.split()
                                    if len(parts) == 3:
                                        day = int(parts[0])
                                        month_name = parts[1].lower()
                                        year = int(parts[2])
                                        if month_name in ro_months:
                                            month_num = ro_months[month_name]
                                            parsed_date = date(year, month_num, day)
                                            current_app.logger.debug(f"Successfully parsed date using manual mapping: {parsed_date}")
                                        else:
                                            raise ValueError(f"Unknown month name: {month_name}")
                                    else:
                                        raise ValueError("Date string does not have 3 parts")
                                
                                amount = Decimal('0')
                                transaction_type = ''
                                debit_str_cleaned = debit_str_raw.replace('.', '').replace(',', '.')
                                credit_str_cleaned = credit_str_raw.replace('.', '').replace(',', '.')
                                current_app.logger.debug(f"Raw debit: '{debit_str_raw}', Cleaned: '{debit_str_cleaned}'")
                                current_app.logger.debug(f"Raw credit: '{credit_str_raw}', Cleaned: '{credit_str_cleaned}'")

                                if debit_str_cleaned:
                                    current_app.logger.debug(f"Attempting to parse debit amount: '{debit_str_cleaned}'")
                                    amount = Decimal(debit_str_cleaned)
                                    transaction_type = 'expense'
                                    current_app.logger.debug(f"Parsed debit amount: {amount}")
                                elif credit_str_cleaned:
                                    current_app.logger.debug(f"Attempting to parse credit amount: '{credit_str_cleaned}'")
                                    amount = Decimal(credit_str_cleaned)
                                    transaction_type = 'income'
                                    current_app.logger.debug(f"Parsed credit amount: {amount}")
                                else:
                                    current_app.logger.debug(f"Row {r_idx} skipped: No debit/credit value.")
                                    r_idx += 1
                                    continue
                        
                                if amount <= 0:
                                    current_app.logger.debug(f"Row {r_idx} skipped: Amount is zero or negative ({amount}).")
                                    r_idx += 1
                                    continue

                                # Extract the detalii_str from ANY column that might contain useful info
                                detalii_str = ''
                                # First check column 4 (index 3) - this is for expense transactions
                                if len(row_list) > 3 and row_list[3].strip():
                                    detalii_str = row_list[3].strip()

                                # For income transactions, check ALL columns for text starting with 'Detalii:'
                                if not detalii_str or detalii_str == 'Incasare':
                                    for col_idx in range(len(row_list)):
                                        if col_idx < len(row_list) and 'detalii:' in row_list[col_idx].lower():
                                            detalii_str = row_list[col_idx].strip()
                                            break
                                
                                # Define date_pattern here to avoid NameError
                                date_pattern = r'^\\d{1,2}\\s+[a-zA-Z]+\\s+\\d{4}$'  # Matches "DD month YYYY" format
                                
                                # Look for Terminal/Beneficiar/Ordonator info in any column
                                additional_info = ''
                                max_lookahead = min(r_idx + 6, len(rows))
                                
                                for i in range(r_idx + 1, max_lookahead):
                                    next_row = rows[i]
                                    if next_row and len(next_row) > 0 and next_row[0].strip() and re.match(date_pattern, next_row[0].strip()):
                                        break
                                    for col_idx in range(len(next_row)):
                                        if col_idx < len(next_row) and next_row[col_idx].strip():
                                            col_text = next_row[col_idx].strip().lower()
                                            if any(keyword in col_text for keyword in ['terminal:', 'beneficiar:', 'ordonator:']):
                                                additional_info = next_row[col_idx].strip()
                                                break
                                    if additional_info:
                                        break
                                
                                if detalii_str and additional_info:
                                    description_str = f"{detalii_str} | {additional_info}"
                                elif detalii_str:
                                    description_str = detalii_str
                                elif additional_info:
                                    description_str = additional_info
                                else:
                                    description_str = ''
                                
                                current_app.logger.debug(f"Final description: {description_str}")
                                transactions_to_add_models.append({
                                    'date': parsed_date,
                                    'amount': amount,
                                    'description': description_str,
                                    'type': transaction_type,
                                    'user_id': current_user.id
                                })
                                current_app.logger.info(f"Successfully processed and added transaction from row {r_idx}.")
                            except (ValueError, IndexError, InvalidOperation) as e:
                                current_app.logger.warning(f"Skipping CSV row {r_idx} due to error for user {current_user.id}: {row_list[:9]} - Error: {str(e)}")
                                # No explicit continue needed here, loop will naturally go to next r_idx
                        else:
                            current_app.logger.debug(f"Row {r_idx} skipped: '{date_candidate}' does not match date pattern.")
                    r_idx += 1
                
                if transactions_to_add_models:
                    current_app.logger.info(f"Processed {len(transactions_to_add_models)} potential transactions from CSV for user {current_user.id}.")
                    
                    income_transactions = [t for t in transactions_to_add_models if t['type'] == 'income']
                    expense_transactions = [t for t in transactions_to_add_models if t['type'] == 'expense']
                    
                    income_category = None
                    if income_transactions:
                        income_category = Category.query.filter_by(
                            user_id=current_user.id, name="Necategorisit (Import CSV)", type='income'
                        ).first()
                        if not income_category:
                            income_category = Category(
                                user_id=current_user.id, name="Necategorisit (Import CSV)", type='income', color="#888888"
                            )
                            db.session.add(income_category)
                        
                        for trans_data in income_transactions:
                            transaction = Transaction(
                                date=trans_data['date'], amount=trans_data['amount'],
                                description=trans_data['description'], type='income',
                                category_id=income_category.id, user_id=current_user.id
                            )
                            db.session.add(transaction)
                    
                    expense_category = None
                    if expense_transactions:
                        expense_category = Category.query.filter_by(
                            user_id=current_user.id, name="Necategorisit (Import CSV)", type='expense'
                        ).first()
                        if not expense_category:
                            expense_category = Category(
                                user_id=current_user.id, name="Necategorisit (Import CSV)", type='expense', color="#888888"
                            )
                            db.session.add(expense_category)
                        
                        for trans_data in expense_transactions:
                            transaction = Transaction(
                                date=trans_data['date'], amount=trans_data['amount'],
                                description=trans_data['description'], type='expense',
                                category_id=expense_category.id, user_id=current_user.id
                            )
                            db.session.add(transaction)
                            
                    categories_used = []
                    if income_category: categories_used.append(f"venituri ({len(income_transactions)} tranzacții)")
                    if expense_category: categories_used.append(f"cheltuieli ({len(expense_transactions)} tranzacții)")
                    
                    if categories_used:
                        categories_message = " și ".join(categories_used)
                        flash(f'Au fost importate {len(transactions_to_add_models)} tranzacții în categoria "Necategorisit (Import CSV)" pentru {categories_message}.', 'info')
                        processed_transactions = True
                
                elif header_found_and_skipped:
                     flash('Antetul CSV (format ING) a fost găsit, dar nu s-au putut extrage tranzacții valide.', 'warning')
                elif not header_found_and_skipped and r_idx > 0:
                    flash('Format CSV nerecunoscut sau fișier gol/invalid.', 'error')
            else:
                flash('Format de fișier neacceptat. Vă rugăm să încărcați un fișier CSV.', 'error')
                return redirect(url_for('main.import_transactions'))

            if processed_transactions:
                try:
                    db.session.commit()
                    flash('Tranzacțiile procesate au fost importate cu succes!', 'success')
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error saving imported transactions for user {current_user.id}: {str(e)}")
                    flash(f'Eroare la salvarea tranzacțiilor importate: {str(e)}', 'danger')
            
            return redirect(url_for('main.import_transactions'))
            
    return render_template('import_transactions.html')

@main_bp.route('/delete_transactions_bulk', methods=['POST'])
@login_required
def delete_transactions_bulk():
    ids = request.json.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'message': 'No transaction IDs provided.'}), 400
    try:
        # Only delete transactions belonging to the current user
        deleted_count = Transaction.query.filter(Transaction.id.in_(ids), Transaction.user_id == current_user.id).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'deleted': deleted_count})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk delete for user {current_user.id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500