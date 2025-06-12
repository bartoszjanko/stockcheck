from myproject import db

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    report_type = db.Column(db.String(100), nullable=False)
    company = db.relationship('Company', backref=db.backref('reports', lazy=True))

    def __repr__(self):
        return f'<Report {self.company.ticker if self.company else "N/A"} {self.report_date} {self.report_type}>'
