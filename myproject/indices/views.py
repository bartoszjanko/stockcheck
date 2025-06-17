from flask import request, render_template, redirect, url_for, Blueprint
from flask_login import login_required, current_user
from myproject.companies.models import Index
from . import indices
import pandas as pd
import requests
import csv
from io import StringIO

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
    # Pobierz ticker z pliku indeksy.csv
    df = pd.read_csv('myproject/indices/indices.csv')
    ticker_row = df[df['index_name'].str.strip() == idx.index_name.strip()]
    ticker = None
    if not ticker_row.empty:
        ticker = str(ticker_row.iloc[0]['index_ticker']).strip()
    chart_data = None
    if ticker and ticker.lower() != 'nan':
        url = f"https://stooq.pl/q/d/l/?s={ticker}&i=d"
        try:
            response = requests.get(url, timeout=5)
            if response.ok and response.text.strip():
                f = StringIO(response.text)
                reader = csv.DictReader(f)
                chart_data = [row for row in reader]
        except Exception:
            chart_data = None
    return render_template('indices/index_detail.html', index=idx, companies=companies, chart_data=chart_data, ticker=ticker)