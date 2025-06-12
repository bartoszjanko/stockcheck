from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user
from myproject.recommendations.models import Recommendation
from myproject.companies.models import Company
from myproject import db
import requests

from . import recommendations

def get_stooq_price(ticker):
    if not ticker:
        return None
    url = f'https://stooq.pl/q/l/?s={ticker.lower()}&f=sd2t2ohlcv&h&e=csv'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.splitlines()
            if len(lines) > 1:
                price = lines[1].split(',')[6]
                try:
                    return float(price)
                except Exception:
                    return None
    except Exception:
        return None
    return None

@recommendations.route('/', methods=['GET', 'POST'])
@login_required
def all_recommendations():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    rec_type = request.args.get('rec_type')
    query = Recommendation.query
    if selected_company:
        query = query.filter(Recommendation.company_id == int(selected_company))
    if date_from:
        query = query.filter(Recommendation.publication_date >= date_from)
    if date_to:
        query = query.filter(Recommendation.publication_date <= date_to)
    if rec_type:
        query = query.filter(Recommendation.recommendation_type == rec_type)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    recommendations_pagination = query.order_by(Recommendation.publication_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    recommendations = recommendations_pagination.items
    rec_types = [row[0] for row in db.session.query(Recommendation.recommendation_type).distinct().order_by(Recommendation.recommendation_type)]
    
    # Dodaj aktualne ceny do rekomendacji
    current_prices = {}
    for rec in recommendations:
        ticker = rec.company.ticker if rec.company else None
        current_prices[rec.id] = get_stooq_price(ticker)
    
    return render_template('recommendations/recommendations.html', recommendations=recommendations, companies=companies, selected_company=selected_company, date_from=date_from, date_to=date_to, rec_types=rec_types, rec_type=rec_type, pagination=recommendations_pagination, current_prices=current_prices)