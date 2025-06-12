from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user

from myproject.companies.models import Company
from myproject.reports.models import Report
from myproject import db

from . import reports

@reports.route('/', methods=['GET', 'POST'])
@login_required
def all_reports():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = Report.query
    if selected_company:
        query = query.filter(Report.company_id == int(selected_company))
    if date_from:
        query = query.filter(Report.report_date >= date_from)
    if date_to:
        query = query.filter(Report.report_date <= date_to)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    reports_pagination = query.order_by(Report.report_date.asc()).paginate(page=page, per_page=per_page, error_out=False)
    reports = reports_pagination.items
    return render_template('reports/reports.html', reports=reports, companies=companies, selected_company=selected_company, date_from=date_from, date_to=date_to, pagination=reports_pagination)

