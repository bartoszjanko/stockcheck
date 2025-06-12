from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from myproject.auth.models import User

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
