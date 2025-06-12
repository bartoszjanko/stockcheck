from myproject import db

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