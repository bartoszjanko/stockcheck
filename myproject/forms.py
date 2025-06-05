from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms import ValidationError
from myproject.models import User, Company

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message='Podaj poprawny adres email!')])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log in')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message='Podaj poprawny adres email!')])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    pass_confirm = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate(self, extra_validators=None):
        initial = super().validate(extra_validators)
        if not initial:
            return False
        # Najpierw sprawdź email/username
        email_exists = User.query.filter_by(email=self.email.data).first()
        username_exists = User.query.filter_by(username=self.username.data).first()
        if email_exists:
            self.email.errors.append('Ten adres e-mail jest już zarejestrowany!')
            return False
        if username_exists:
            self.username.errors.append('Nazwa użytkownika jest już zajęta!')
            return False
        # Dopiero teraz sprawdzaj zgodność haseł
        if self.password.data != self.pass_confirm.data:
            self.pass_confirm.errors.append('Hasła muszą być takie same!')
            return False
        return True

class AddCompanyForm(FlaskForm):
    company = SelectField('Spółka', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Dodaj spółkę')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from flask import request
        # Pobierz dostępne rynki z bazy
        markets = sorted(set(c.market for c in Company.query.distinct(Company.market)))
        self.available_markets = markets
        self.selected_market = None
        self.company.choices = []
        # Odtwórz wybrany rynek zarówno przy wyborze rynku, jak i przy submit
        if request.method == 'POST':
            selected_market = request.form.get('selected_market')
            # Jeśli submit, to selected_market może być None, więc spróbuj pobrać z poprzedniego POST
            if not selected_market and 'company' in request.form:
                # Spróbuj znaleźć rynek na podstawie wybranej spółki
                try:
                    company_id = int(request.form.get('company'))
                    company = Company.query.get(company_id)
                    if company:
                        selected_market = company.market
                except Exception:
                    selected_market = None
            self.selected_market = selected_market
            if selected_market:
                self.company.choices = [
                    (c.id, f"{c.ticker} - {c.name}")
                    for c in Company.query.filter_by(market=selected_market).order_by(Company.ticker).all()
                ]
            if 'submit' in request.form:
                try:
                    self.company.data = int(request.form.get('company')) if request.form.get('company') not in (None, '') else None
                except (TypeError, ValueError):
                    self.company.data = None
            else:
                self.company.data = None
        self.company_disabled = not bool(self.company.choices)

class PostForm(FlaskForm):
    company = SelectField('Spółka', coerce=int, validators=[DataRequired()])
    title = StringField('Tytuł', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Treść', validators=[DataRequired()])
    submit = SubmitField('Dodaj post')

class CommentForm(FlaskForm):
    content = TextAreaField('Treść', validators=[DataRequired()])
    submit = SubmitField('Dodaj komentarz')
