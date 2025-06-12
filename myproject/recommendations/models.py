from myproject import db

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    publication_date = db.Column(db.Date, nullable=False)
    recommendation_type = db.Column(db.String(100), nullable=False)
    target_price = db.Column(db.String(50), nullable=True)
    publication_price = db.Column(db.String(50), nullable=True)
    institution = db.Column(db.String(100), nullable=True)
    company = db.relationship('Company', backref=db.backref('recommendations', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Recommendation {self.company.ticker if self.company else "N/A"} {self.publication_date} {self.recommendation_type}>'