from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import GamePortfolio, GamePosition, GameTransaction
from .domain import Portfolio, Position
from .services import get_latest_price, get_prices_for_positions
from myproject import db
from datetime import date
import csv
import os
from myproject.models import User

bp = Blueprint('stock_game', __name__, url_prefix='/game')

@bp.route('/portfolio')
@login_required
def portfolio():
    # Wczytaj tickery i nazwy spółek
    tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.csv')
    names = {}
    with open(tickers_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            names[row['ticker']] = row['name']
    db_portfolio = GamePortfolio.query.filter_by(user_id=current_user.id).first()
    if not db_portfolio:
        db_portfolio = GamePortfolio(user_id=current_user.id)
        db.session.add(db_portfolio)
        db.session.commit()
    db_positions = GamePosition.query.filter_by(portfolio_id=db_portfolio.id).all()
    positions = [Position(p.ticker, p.shares, p.buy_price, p.buy_date) for p in db_positions]
    prices = get_prices_for_positions(positions)
    portfolio = Portfolio(db_portfolio.cash, positions)
    total = portfolio.total_value(prices)
    return render_template('stock_game/portfolio.html', portfolio=portfolio, prices=prices, total=total, names=names)

@bp.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    tickers = []
    names = {}
    tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.csv')
    with open(tickers_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tickers.append(row['ticker'])
            names[row['ticker']] = row['name']
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        shares = int(request.form.get('shares'))
        price = get_latest_price(ticker)
        if price is None:
            flash(f'Nie udało się pobrać ceny dla spółki {ticker}. Spróbuj inną spółkę.')
            return redirect(url_for('stock_game.buy'))
        db_portfolio = GamePortfolio.query.filter_by(user_id=current_user.id).first()
        cost = price * shares
        if db_portfolio.cash < cost:
            flash('Brak środków na zakup.')
            return redirect(url_for('stock_game.buy'))
        db_portfolio.cash -= cost
        position = GamePosition(portfolio_id=db_portfolio.id, ticker=ticker, shares=shares, buy_price=price, buy_date=date.today())
        db.session.add(position)
        db.session.add(GameTransaction(portfolio_id=db_portfolio.id, ticker=ticker, shares=shares, price=price, date=date.today(), type='buy'))
        db.session.commit()
        flash('Zakupiono akcje!')
        return redirect(url_for('stock_game.portfolio'))
    return render_template('stock_game/buy.html', tickers=tickers, names=names)

@bp.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    # Wczytaj tickery i nazwy spółek
    tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.csv')
    names = {}
    with open(tickers_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            names[row['ticker']] = row['name']
    db_portfolio = GamePortfolio.query.filter_by(user_id=current_user.id).first()
    db_positions = GamePosition.query.filter_by(portfolio_id=db_portfolio.id).all()
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        shares = int(request.form.get('shares'))
        price = get_latest_price(ticker)
        if price is None:
            flash('Nie udało się pobrać ceny dla podanego tickera.')
            return redirect(url_for('stock_game.sell'))
        position = GamePosition.query.filter_by(portfolio_id=db_portfolio.id, ticker=ticker).first()
        if not position or position.shares < shares:
            flash('Brak wystarczającej liczby akcji do sprzedaży.')
            return redirect(url_for('stock_game.sell'))
        position.shares -= shares
        if position.shares == 0:
            db.session.delete(position)
        db_portfolio.cash += price * shares
        db.session.add(GameTransaction(portfolio_id=db_portfolio.id, ticker=ticker, shares=shares, price=price, date=date.today(), type='sell'))
        db.session.commit()
        flash('Sprzedano akcje!')
        return redirect(url_for('stock_game.portfolio'))
    tickers = [p.ticker for p in db_positions]
    return render_template('stock_game/sell.html', tickers=tickers, names=names)

@bp.route('/history')
@login_required
def history():
    # Wczytaj tickery i nazwy spółek
    tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.csv')
    names = {}
    with open(tickers_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            names[row['ticker']] = row['name']
    db_portfolio = GamePortfolio.query.filter_by(user_id=current_user.id).first()
    transactions = GameTransaction.query.filter_by(portfolio_id=db_portfolio.id).order_by(GameTransaction.date.desc()).all()
    return render_template('stock_game/history.html', transactions=transactions, names=names)

@bp.route('/ranking')
@login_required
def ranking():
    # Wczytaj tickery i nazwy spółek
    tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.csv')
    names = {}
    with open(tickers_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            names[row['ticker']] = row['name']
    portfolios = GamePortfolio.query.all()
    ranking_list = []
    for p in portfolios:
        db_positions = GamePosition.query.filter_by(portfolio_id=p.id).all()
        positions = [Position(pos.ticker, pos.shares, pos.buy_price, pos.buy_date) for pos in db_positions]
        prices = get_prices_for_positions(positions)
        portfolio = Portfolio(p.cash, positions)
        total = portfolio.total_value(prices)
        user = User.query.get(p.user_id)
        username = user.username if user else f"Użytkownik {p.user_id}"
        # Dodajemy listę pozycji z nazwami spółek
        pos_list = [{'ticker': pos.ticker, 'name': names.get(pos.ticker, ''), 'shares': pos.shares} for pos in positions]
        ranking_list.append({'username': username, 'total': total, 'positions': pos_list})
    ranking_list.sort(key=lambda x: x['total'], reverse=True)
    return render_template('stock_game/ranking.html', ranking=ranking_list)
