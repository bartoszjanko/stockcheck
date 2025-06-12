from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from myproject import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default="user")  # "user" lub "admin"
    companies = db.relationship('UserCompany', backref='owner', lazy=True)

    def __init__(self, email, username, password, role="user"):
        self.email = email
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)