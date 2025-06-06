from flask import request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from myproject import create_app, db, login_manager
from myproject.models import User, Company, UserCompany, Report, Recommendation, Post, Comment, Industry
from myproject.forms import LoginForm, RegistrationForm, AddCompanyForm, PostForm, CommentForm
import requests
import pandas as pd
from io import StringIO
from datetime import date
from myproject.scarp_import_reports import update_reports
from functools import wraps
from flask import abort
from myproject.stock_game.views import bp as stock_game_bp

app = create_app()
app.register_blueprint(stock_game_bp)

with app.app_context():
    # Nie uruchamiaj update_reports() ani importów jeśli nie ma jeszcze tabel
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'company' in tables:
        update_reports() # automatyczna aktualizacja terminarza z raportami ze strefy inwestora
        from myproject.scrape_recommendations import update_recommendations
        update_recommendations() # automatyczna aktualizacja rekomendacji
        

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/companies', methods=['GET'])
@login_required
def list_companies():
    companies = db.session.query(Company).join(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    return render_template('companies.html', companies=companies)

@app.route('/add_company', methods=['GET', 'POST'])
@login_required
def add_company():
    from werkzeug.datastructures import MultiDict
    # Dodanie spółki do portfela
    if request.method == 'POST' and 'submit' in request.form:
        form = AddCompanyForm(formdata=MultiDict(request.form))
        if form.validate_on_submit():
            company_id = form.company.data
            already_added = UserCompany.query.filter_by(user_id=current_user.id, company_id=company_id).first()
            if not already_added:
                user_company = UserCompany(user_id=current_user.id, company_id=company_id)
                db.session.add(user_company)
                db.session.commit()
            return redirect(url_for('list_companies'))
        return render_template('add_company.html', form=form)
    # Obsługa wyboru rynku przez przycisk (selected_market)
    elif request.method == 'POST' and 'selected_market' in request.form:
        form = AddCompanyForm(formdata=MultiDict(request.form))
        form.company.data = None
        return render_template('add_company.html', form=form)
    # GET: pusta lista spółek
    else:
        form = AddCompanyForm()
        return render_template('add_company.html', form=form)

@app.route('/company/<int:company_id>', methods=['GET', 'POST'])
@login_required
def company_detail(company_id):
    user_company = UserCompany.query.filter_by(user_id=current_user.id, company_id=company_id).first_or_404()
    company = user_company.company

    # Pobierz najbliższe raporty (od dziś w górę)
    upcoming_reports = Report.query.filter(
        Report.company_id == company.id,
        Report.report_date >= date.today()
    ).order_by(Report.report_date.asc()).all()

    # Pobierz rekomendacje dla spółki (posortowane od najnowszej)
    recommendations = Recommendation.query.filter_by(company_id=company.id).order_by(Recommendation.publication_date.desc()).all()

    # Pobierz dzienne dane ze Stooq
    stooq_daily = None
    try:
        url = f'https://stooq.pl/q/d/l/?s={company.ticker.lower()}&i=d'
        r = requests.get(url, timeout=20)
        if r.ok and r.text and not r.text.strip().startswith('Brak danych'):
            lines = r.text.splitlines()
            if len(lines) > 1 and (lines[0].startswith('Data') or lines[0].startswith('<DATE>')):
                df = pd.read_csv(StringIO('\n'.join(lines)))
                if not df.empty:
                    last_row = df.iloc[-1]
                    stooq_daily = {
                        'date': str(last_row.get('<DATE>', last_row.get('Data', ''))),
                        'open': last_row.get('<OPEN>', last_row.get('Otwarcie', '')),
                        'high': last_row.get('<HIGH>', last_row.get('Najwyzszy', '')),
                        'low': last_row.get('<LOW>', last_row.get('Najnizszy', '')),
                        'close': last_row.get('<CLOSE>', last_row.get('Zamkniecie', '')),
                        'vol': last_row.get('<VOL>', last_row.get('Wolumen', ''))
                    }
    except Exception:
        stooq_daily = None

    if request.method == 'POST':
        user_company.note = request.form.get('note', '')
        target_buy = request.form.get('target_buy', '')
        target_sell = request.form.get('target_sell', '')
        try:
            user_company.target_buy = float(target_buy) if target_buy else None
        except ValueError:
            user_company.target_buy = None
        try:
            user_company.target_sell = float(target_sell) if target_sell else None
        except ValueError:
            user_company.target_sell = None
        db.session.commit()
    return render_template(
        'company_detail.html',
        company=company,
        user_company=user_company,
        stooq_daily=stooq_daily,
        upcoming_reports=upcoming_reports,
        recommendations=recommendations
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully!')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('list_companies')
            return redirect(next_page)
        else:
            flash('Nieprawidłowy login lub hasło!')
    # Show all form errors (e.g. missing fields)
    for field, errors in form.errors.items():
        for error in errors:
            flash(error)
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user with hashed password
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        # Redirect to login
        return redirect(url_for('login'))
    # Show all form errors (including password mismatch, duplicate email/username)
    for field, errors in form.errors.items():
        for error in errors:
            flash(error)
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/reports', methods=['GET', 'POST'])
@login_required
def all_reports():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = Report.query
    if selected_company:
        query = query.filter(Report.company_id == int(selected_company))
    if date_from:
        query = query.filter(Report.report_date >= date_from)
    if date_to:
        query = query.filter(Report.report_date <= date_to)
    reports = query.order_by(Report.report_date.asc()).all()
    return render_template('reports.html', reports=reports, companies=companies, selected_company=selected_company, date_from=date_from, date_to=date_to)

@app.route('/recommendations', methods=['GET', 'POST'])
@login_required
def all_recommendations():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    rec_type = request.args.get('rec_type')
    query = Recommendation.query
    if selected_company:
        query = query.filter(Recommendation.company_id == int(selected_company))
    if date_from:
        query = query.filter(Recommendation.publication_date >= date_from)
    if date_to:
        query = query.filter(Recommendation.publication_date <= date_to)
    if rec_type:
        query = query.filter(Recommendation.recommendation_type == rec_type)
    recommendations = query.order_by(Recommendation.publication_date.desc()).all()
    # Pobierz unikalne typy rekomendacji do selecta
    rec_types = [row[0] for row in db.session.query(Recommendation.recommendation_type).distinct().order_by(Recommendation.recommendation_type)]
    return render_template('recommendations.html', recommendations=recommendations, companies=companies, selected_company=selected_company, date_from=date_from, date_to=date_to, rec_types=rec_types, rec_type=rec_type)

@app.route('/forum')
@login_required
def forum():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    query = Post.query.order_by(Post.created_at.desc())
    if selected_company:
        query = query.filter(Post.company_id == int(selected_company))
    posts = query.all()
    return render_template('forum.html', posts=posts, companies=companies, selected_company=selected_company)

@app.route('/forum/add', methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()
    form.company.choices = [(c.id, f"{c.ticker} - {c.name}") for c in Company.query.order_by(Company.ticker)]
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            company_id=form.company.data,
            title=form.title.data,
            content=form.content.data
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('forum'))
    return render_template('add_post.html', form=form)

@app.route('/forum/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            post_id=post.id,
            user_id=current_user.id,
            content=form.content.data
        )
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('post_detail', post_id=post.id))
    return render_template('post_detail.html', post=post, form=form)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/forum/post/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('forum'))

@app.route('/forum/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('post_detail', post_id=post_id))


@app.route('/admin/panel')
@admin_required
def admin_panel():
    from sqlalchemy import func
    # Statystyki spółek wg rynku
    market_stats = db.session.query(Company.market, func.count(Company.id)).group_by(Company.market).all()
    # Statystyki branż
    industry_stats = db.session.query(Company.industry_id, func.count(Company.id)).group_by(Company.industry_id).all()
    industries = {i.id: i.industry_name for i in db.session.query(Industry).all()}
    # Najaktywniejsi użytkownicy (po liczbie postów)
    top_users = db.session.query(User, func.count(Post.id).label('posts_count'))\
        .outerjoin(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(10).all()
    # Liczba raportów i rekomendacji
    reports_count = Report.query.count()
    recommendations_count = Recommendation.query.count()
    users = User.query.all()
    return render_template(
        'admin_panel.html',
        market_stats=market_stats,
        industry_stats=industry_stats,
        industries=industries,
        top_users=top_users,
        reports_count=reports_count,
        recommendations_count=recommendations_count,
        users=users
    )
if __name__ == '__main__':
    app.run(debug=True)
