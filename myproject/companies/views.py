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
    from werkzeug.datastructures import MultiDict
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

    # Dodaj aktualne ceny do rekomendacji (jak w recommendations.views)
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
    current_prices = {}
    for rec in recommendations:
        ticker = rec.company.ticker if rec.company else None
        current_prices[rec.id] = get_stooq_price(ticker)

    # Pobierz dane ze Stooq i generuj wykres świecowy z wolumenem
    candlestick_chart = None
    try:
        url = f'https://stooq.pl/q/d/l/?s={company.ticker.lower()}&i=d'
        r = requests.get(url, timeout=20)
        if r.ok and r.text and not r.text.strip().startswith('Brak danych'):
            lines = r.text.splitlines()
            if len(lines) > 1 and (lines[0].startswith('Data') or lines[0].startswith('<DATE>')):
                df = pd.read_csv(StringIO('\n'.join(lines)))
                if not df.empty:
                    # Mapa nazw kolumn
                    column_map = {
                        '<DATE>': 'Data', 
                        '<OPEN>': 'Otwarcie', 
                        '<HIGH>': 'Najwyzszy',
                        '<LOW>': 'Najnizszy', 
                        '<CLOSE>': 'Zamkniecie', 
                        '<VOL>': 'Wolumen'
                    }
                    # Zamiana nazw kolumn jeśli potrzebne
                    for eng, pl in column_map.items():
                        if eng in df.columns:
                            df.rename(columns={eng: pl}, inplace=True)
                    # Konwersja daty na format datetime
                    df['Data'] = pd.to_datetime(df['Data'])
                    # Sortowanie danych od najstarszych do najnowszych
                    df = df.sort_values('Data')
                    # Najpierw licz SMA20 na pełnych danych
                    if len(df) >= 20:
                        df['SMA20'] = df['Zamkniecie'].rolling(window=20).mean()
                    else:
                        df['SMA20'] = None
                    # Obsługa zakresów czasowych jak na Google (1m, 6m, YTD, 1r, 5l, max)
                    import numpy as np
                    range_map = {
                        '1m': 30,
                        '6m': 182,
                        'ytd': 'ytd',
                        '1r': 365,
                        '5l': 365*5,
                        'max': None
                    }
                    selected_range = request.args.get('range', '6m').lower()
                    days = range_map.get(selected_range, 182)
                    if not df.empty and days:
                        if selected_range == 'ytd':
                            start = pd.Timestamp(date.today().replace(month=1, day=1))
                            df = df[df['Data'] >= start]
                        else:
                            last_date = df['Data'].max()
                            start = last_date - pd.Timedelta(days=days)
                            df = df[df['Data'] >= start]
                    # Tworzenie subplotów: świecowy + wolumen
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.08,
                        row_width=[0.2, 0.8],
                        subplot_titles=(f'Notowania {company.ticker}', 'Wolumen')
                    )
                    # Przygotuj kolory wolumenu: zielony dla wzrostu, czerwony dla spadku
                    volume_colors = [
                        'rgba(0,200,0,0.5)' if close >= open_ else 'rgba(200,0,0,0.5)'
                        for open_, close in zip(df['Otwarcie'], df['Zamkniecie'])
                    ]
                    # Wykres świecowy
                    fig.add_trace(
                        go.Candlestick(
                            x=df['Data'],
                            open=df['Otwarcie'],
                            high=df['Najwyzszy'],
                            low=df['Najnizszy'],
                            close=df['Zamkniecie'],
                            name='Notowania',
                            showlegend=True
                        ),
                        row=1, col=1
                    )
                    # Średnia krocząca
                    fig.add_trace(
                        go.Scatter(
                            x=df['Data'],
                            y=df['SMA20'],
                            mode='lines',
                            name='SMA 20',
                            line=dict(color='orange', width=2),
                            showlegend=True
                        ),
                        row=1, col=1
                    )
                    # Wykres wolumenu z dynamicznym kolorem
                    fig.add_trace(
                        go.Bar(
                            x=df['Data'],
                            y=df['Wolumen'],
                            name='Wolumen',
                            marker_color=volume_colors,
                            showlegend=True,
                            opacity=0.7
                        ),
                        row=2, col=1
                    )
                    # Ustaw zakres osi Y wolumenu od zera
                    max_vol = df['Wolumen'].max() if not df['Wolumen'].isnull().all() else 1
                    fig.update_yaxes(title_text="Cena", row=1, col=1, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_yaxes(title_text="Wolumen", row=2, col=1, range=[0, max_vol * 1.05], fixedrange=False, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_xaxes(title_text="Data", row=2, col=1, tickformat='%Y-%m-%d', rangeslider_visible=False, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_layout(
                        height=650,
                        xaxis_rangeslider_visible=False,
                        title={
                            'text': f'<b>Wykres notowań i wolumenu dla {company.name} ({company.ticker})</b>',
                            'x': 0.5,
                            'xanchor': 'center',
                            'font': {'size': 20}
                        },
                        margin=dict(t=70, b=40, l=40, r=20),
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                        plot_bgcolor='white',
                        hovermode='x unified',
                    )
                    candlestick_chart = plot(fig, output_type='div', include_plotlyjs=True)
    except Exception as e:
        print(f"Błąd podczas pobierania danych: {str(e)}")
        candlestick_chart = None

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