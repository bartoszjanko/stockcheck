from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import GamePortfolio, GamePosition, GameTransaction
from .domain import Portfolio, Position
from .services import (
    get_latest_price,
    get_prices_for_positions,
    aggregate_positions,
    calculate_avg_buy_prices,
    calculate_positions_with_prices,
    validate_buy,
    execute_buy,
    validate_sell,
    execute_sell,
    get_or_create_portfolio,
    get_company_names,
    get_open_positions,
    close_deleted_company_positions,
    get_transactions,
    get_ranking_list,
    calculate_portfolio_profit,  # dodaj do importów
    is_market_open,
)
from myproject import db
from datetime import datetime
import csv
import os
from myproject.companies.models import Company
from myproject.auth.models import User

from . import stock_game

# Importy bibliotek i modeli oraz utworzenie blueprinta stock_game

# Widok kupna akcji: obsługuje formularz zakupu, przelicza koszt, waliduje i realizuje transakcję kupna
# - Pobiera listę spółek i ich tickery
# - Tworzy obiekty pozycji i portfela
# - Obsługuje przeliczenie kosztu i zakup (POST)
# - Blokuje kupno, jeśli rynek zamknięty
# - Przekazuje dane do szablonu buy.html

@stock_game.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    companies = Company.query.order_by(Company.name).all()
    tickers = [c.ticker for c in companies]
    names = {c.ticker: c.name for c in companies}
    db_portfolio = current_user.portfolio
    db_positions = GamePosition.query.filter_by(portfolio_id=db_portfolio.id).all() if db_portfolio else []
    positions = [Position(pos.ticker, pos.shares, pos.buy_price, pos.buy_date) for pos in db_positions]
    prices = get_prices_for_positions(positions)
    portfolio = Portfolio(db_portfolio.cash if db_portfolio else 0, positions)
    total = portfolio.total_value(prices)

    calc_result = None
    calc_ticker = None
    calc_shares = None
    calc_price = None
    calc_cost = None
    market_open = is_market_open()
    if request.method == 'POST':
        if not market_open:
            flash('Rynek jest zamknięty. Kupno możliwe tylko w godzinach 9:00-17:00 (pon-pt).')
            return redirect(url_for('stock_game.buy'))
        ticker = request.form.get('ticker')
        shares = request.form.get('shares')
        action = request.form.get('action')
        try:
            shares = int(shares)
        except Exception:
            shares = 0
        price = get_latest_price(ticker) if ticker else None
        company = Company.query.filter_by(ticker=ticker).first() if ticker else None
        if action == 'calc':
            calc_ticker = ticker
            calc_shares = shares
            calc_price = price
            calc_cost = price * shares if price is not None and shares > 0 else None
        elif action == 'buy':
            valid, msg = validate_buy(db_portfolio, ticker, shares, price, company)
            if not valid:
                flash(msg)
                return redirect(url_for('stock_game.buy'))
            success, msg = execute_buy(db_portfolio, ticker, shares, price, company)
            if success:
                flash(msg)
                return redirect(url_for('stock_game.buy'))
            else:
                flash(msg)
                return redirect(url_for('stock_game.buy'))
    return render_template(
        'stock_game/buy.html',
        tickers=tickers,
        names=names,
        cash=db_portfolio.cash if db_portfolio else 0,
        total=total,
        calc_ticker=calc_ticker,
        calc_shares=calc_shares,
        calc_price=calc_price,
        calc_cost=calc_cost,
        market_open=market_open
    )

# Widok sprzedaży akcji: obsługuje formularz sprzedaży, waliduje i realizuje transakcję sprzedaży
# - Pobiera pozycje użytkownika i dostępne tickery
# - Obsługuje sprzedaż (POST), waliduje liczbę akcji i cenę
# - Blokuje sprzedaż, jeśli rynek zamknięty
# - Przekazuje dane do szablonu sell.html

@stock_game.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    db_portfolio = current_user.portfolio
    db_positions = GamePosition.query.filter_by(portfolio_id=db_portfolio.id).all()
    companies = Company.query.filter(Company.ticker.in_([p.ticker for p in db_positions])).all()
    tickers = [c.ticker for c in companies]
    names = {c.ticker: c.name for c in companies}
    sale_success = False
    market_open = is_market_open()
    if request.method == 'POST':
        if not market_open:
            flash('Rynek jest zamknięty. Sprzedaż możliwa tylko w godzinach 9:00-17:00 (pon-pt).')
            return redirect(url_for('stock_game.sell'))
        ticker = request.form.get('ticker')
        shares = int(request.form.get('shares'))
        price = get_latest_price(ticker)
        valid, msg = validate_sell(db_portfolio, ticker, shares)
        if price is None:
            flash('Nie udało się pobrać ceny dla podanego tickera.')
            return redirect(url_for('stock_game.sell'))
        if not valid:
            flash(msg)
            return redirect(url_for('stock_game.sell'))
        success, msg = execute_sell(db_portfolio, ticker, shares, price)
        flash(msg)
        if success:
            return redirect(url_for('stock_game.sell'))
        return redirect(url_for('stock_game.sell'))
    return render_template('stock_game/sell.html', tickers=tickers, names=names, market_open=market_open)

# Widok portfela: prezentuje aktualny stan portfela użytkownika
# - Pobiera nazwy spółek, pozycje, ceny, agreguje dane
# - Oblicza wartości pozycji, sumę portfela, zysk/stratę
# - Generuje dane do wykresu kołowego
# - Przekazuje wszystko do szablonu portfolio.html

@stock_game.route('/portfolio')
@login_required
def portfolio():
    names = get_company_names()
    db_portfolio = current_user.portfolio
    if db_portfolio is None:
        db_portfolio = GamePortfolio(user_id=current_user.id)
        db.session.add(db_portfolio)
        db.session.commit()
    close_deleted_company_positions(db_portfolio.id)
    open_positions = get_open_positions(db_portfolio.id)
    agg = aggregate_positions(open_positions)
    avg_buy_prices = calculate_avg_buy_prices(db_portfolio.id, agg)
    tickers = list(agg.keys())
    prices = get_prices_for_positions([Position(t, 0, 0, None) for t in tickers])
    positions = calculate_positions_with_prices(agg, avg_buy_prices, prices)
    pie_labels = []
    pie_values = []
    for pos in positions:
        if pos.value > 0:
            pie_labels.append(names.get(pos.ticker, pos.ticker))
            pie_values.append(pos.value)
    total = db_portfolio.cash + sum(pos.value for pos in positions)
    portfolio = Portfolio(db_portfolio.cash, positions)

    # Oblicz łączny zysk/stratę portfela przez services.py
    total_profit, total_profit_percent = calculate_portfolio_profit(positions, avg_buy_prices)
    return render_template(
        'stock_game/portfolio.html',
        portfolio=portfolio,
        prices=prices,
        total=total,
        names=names,
        pie_labels=pie_labels,
        pie_values=pie_values,
        avg_buy_prices=avg_buy_prices,
        total_profit=total_profit,
        total_profit_percent=total_profit_percent
    )

# Widok historii transakcji: prezentuje historię operacji użytkownika
# - Pobiera transakcje z bazy
# - Przekazuje do szablonu history.html

@stock_game.route('/history')
@login_required
def history():
    names = get_company_names()
    db_portfolio = current_user.portfolio
    transactions = get_transactions(db_portfolio.id)
    return render_template('stock_game/history.html', transactions=transactions, names=names)

# Widok rankingu: prezentuje ranking użytkowników wg wartości portfela
# - Pobiera ranking z serwisu
# - Przekazuje do szablonu ranking.html

@stock_game.route('/ranking')
@login_required
def ranking():
    names = get_company_names()
    ranking_list = get_ranking_list()
    return render_template('stock_game/ranking.html', ranking=ranking_list, names=names)
