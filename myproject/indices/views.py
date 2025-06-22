from flask import request, render_template, redirect, url_for
from flask_login import login_required, current_user
from myproject.companies.models import Index
import pandas as pd
from . import indices
from .services import get_index_chart

@indices.route('/')
@login_required
def indices_list():
    indices = Index.query.order_by(Index.index_name).all()
    return render_template('indices/indices.html', indices=indices)

@indices.route('/<int:index_id>')
@login_required
def index_detail(index_id):
    idx = Index.query.get_or_404(index_id)
    companies = idx.companies.order_by('ticker').all() if hasattr(idx.companies, 'order_by') else idx.companies
    df = pd.read_csv('myproject/indices/indices.csv')
    ticker_row = df[df['index_name'].str.strip() == idx.index_name.strip()]
    ticker = None
    if not ticker_row.empty:
        ticker = str(ticker_row.iloc[0]['index_ticker']).strip()
    index_chart = None
    if ticker and ticker.lower() != 'nan':
        selected_range = request.args.get('range', '6m').lower()
        index_chart = get_index_chart(ticker, selected_range)
    return render_template('indices/index_detail.html', index=idx, companies=companies, ticker=ticker, index_chart=index_chart)