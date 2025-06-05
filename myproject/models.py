from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from myproject import db
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    companies = db.relationship('UserCompany', backref='owner', lazy=True)

    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Association table for many-to-many Company <-> Index
company_index = db.Table('company_index',
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'), primary_key=True),
    db.Column('index_id', db.Integer, db.ForeignKey('index.id'), primary_key=True)
)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    industry_id = db.Column(db.Integer, db.ForeignKey('industry.id'))
    market = db.Column(db.String(100), nullable=True)

    # Relationships
    industry = db.relationship('Industry', backref=db.backref('companies', lazy=True))
    indices = db.relationship('Index', secondary=company_index, backref=db.backref('companies', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Company {self.name}>'

class UserCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    note = db.Column(db.Text)
    target_buy = db.Column(db.Float)
    target_sell = db.Column(db.Float)
    company = db.relationship('Company')

    def __repr__(self):
        return f'<UserCompany {self.user_id} - {self.company_id}>'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    #ticker = db.Column(db.String(10), nullable=False)
    #name = db.Column(db.String(100), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    report_type = db.Column(db.String(100), nullable=False)
    company = db.relationship('Company', backref=db.backref('reports', lazy=True))

    def __repr__(self):
        return f'<Report {self.company.ticker if self.company else "N/A"} {self.report_date} {self.report_type}>'

class Index(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index_name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Index {self.index_name}>'
    
class Industry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    industry_name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Industry {self.industry_name}>'

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    #ticker = db.Column(db.String(10), nullable=False)
    #name = db.Column(db.String(100), nullable=False)
    publication_date = db.Column(db.Date, nullable=False)
    recommendation_type = db.Column(db.String(100), nullable=False)
    target_price = db.Column(db.String(50), nullable=True)
    publication_price = db.Column(db.String(50), nullable=True)
    institution = db.Column(db.String(100), nullable=True)
    company = db.relationship('Company', backref=db.backref('recommendations', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Recommendation {self.company.ticker if self.company else "N/A"} {self.publication_date} {self.recommendation_type}>'