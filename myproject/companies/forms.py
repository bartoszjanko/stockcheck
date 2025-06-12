from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from myproject.companies.models import Company

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