from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user
from myproject.recommendations.models import Recommendation
from myproject.companies.models import Company
from myproject import db

from . import recommendations

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
    recommendations = query.order_by(Recommendation.publication_date.desc()).all()
    # Pobierz unikalne typy rekomendacji do selecta
    rec_types = [row[0] for row in db.session.query(Recommendation.recommendation_type).distinct().order_by(Recommendation.recommendation_type)]
    return render_template('recommendations/recommendations.html', recommendations=recommendations, companies=companies, selected_company=selected_company, date_from=date_from, date_to=date_to, rec_types=rec_types, rec_type=rec_type)