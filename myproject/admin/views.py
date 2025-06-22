from flask import render_template
from myproject.admin.decorators import admin_required
from myproject import db

from myproject.companies.models import Company, Industry
from myproject.auth.models import User
from myproject.recommendations.models import Recommendation
from myproject.reports.models import Report
from myproject.forum.models import Post

from . import admin

@admin.route('/panel')
@admin_required
def admin_panel():
    from sqlalchemy import func
    # Statystyki spółek wg rynku
    market_stats = db.session.query(Company.market, func.count(Company.id)).group_by(Company.market).all()
    # Statystyki branż
    industry_stats = db.session.query(Company.industry_id, func.count(Company.id)).group_by(Company.industry_id).all()
    industries = {i.id: i.industry_name for i in db.session.query(Industry).all()}
    # Najaktywniejsi użytkownicy (po liczbie postów)
    top_users = db.session.query(User, func.count(Post.id).label('posts_count'))\
        .outerjoin(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(10).all()
    # Liczba raportów i rekomendacji
    reports_count = Report.query.count()
    recommendations_count = Recommendation.query.count()
    users = User.query.all()
    return render_template(
        '/admin/admin_panel.html',
        market_stats=market_stats,
        industry_stats=industry_stats,
        industries=industries,
        top_users=top_users,
        reports_count=reports_count,
        recommendations_count=recommendations_count,
        users=users
    )