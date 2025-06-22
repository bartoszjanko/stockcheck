from flask import request, render_template, redirect, url_for, Blueprint
from flask_login import login_required, current_user
from werkzeug.datastructures import MultiDict
from datetime import date
import pandas as pd
from io import StringIO
import requests
from sqlalchemy.orm import selectinload
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from myproject.companies.models import Company, UserCompany
from myproject.companies.forms import AddCompanyForm
from myproject import db
from myproject.reports.models import Report
from myproject.recommendations.models import Recommendation

from . import companies
from .services import get_stooq_price, get_candlestick_chart

@companies.route('/', methods=['GET'])
@login_required
def list_companies():
    companies = db.session.query(Company).join(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    return render_template('companies/companies.html', companies=companies)

@companies.route('/add', methods=['GET', 'POST'])
@login_required
def add_company():
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
            return redirect(url_for('companies.list_companies'))
        return render_template('/companies/add_company.html', form=form)
    # Obsługa wyboru rynku przez przycisk (selected_market)
    elif request.method == 'POST' and 'selected_market' in request.form:
        form = AddCompanyForm(formdata=MultiDict(request.form))
        form.company.data = None
        return render_template('/companies/add_company.html', form=form)
    # GET: pusta lista spółek
    else:
        form = AddCompanyForm()
        return render_template('companies/add_company.html', form=form)

@companies.route('/<int:company_id>', methods=['GET', 'POST'])
@login_required
def company_detail(company_id):
    user_company = UserCompany.query.filter_by(user_id=current_user.id, company_id=company_id).first_or_404()
    company = user_company.company

    # Pobierz najbliższe raporty (od dziś w górę)
    upcoming_reports = Report.query.filter(
        Report.company_id == company.id,
        Report.report_date >= date.today()
    ).order_by(Report.report_date.asc()).all()

    # Pobierz rekomendacje dla spółki (posortowane od najnowszej) z eager loadingiem relacji company
    recommendations = Recommendation.query.options(selectinload(Recommendation.company)).filter_by(company_id=company.id).order_by(Recommendation.publication_date.desc()).all()

    # Dodaj aktualne ceny do rekomendacji
    current_prices = {rec.id: get_stooq_price(rec.company.ticker if rec.company else None) for rec in recommendations}

    # Generuj wykres świecowy z wolumenem
    selected_range = request.args.get('range', '6m').lower()
    candlestick_chart = get_candlestick_chart(company, selected_range)

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
        'companies/company_detail.html',
        company=company,
        user_company=user_company,
        upcoming_reports=upcoming_reports,
        recommendations=recommendations,
        current_prices=current_prices,
        candlestick_chart=candlestick_chart
    )