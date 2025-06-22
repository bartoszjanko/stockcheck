from flask import request, render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user, login_required
from myproject import db
from myproject.auth.forms import LoginForm, RegistrationForm
from myproject.auth.models import User

from . import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('companies.list_companies')
            return redirect(next_page)
        else:
            flash('Nieprawidłowy login lub hasło!')
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user with hashed password
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        # Redirect to login
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('core.index'))