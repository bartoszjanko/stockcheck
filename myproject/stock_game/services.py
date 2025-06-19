"""
W pliku services.py znajdują się funkcje pomocnicze do pobierania aktualnych cen akcji ze Stooq dla gry giełdowej:

"""

import pandas as pd
from collections import defaultdict
from .models import GameTransaction, GamePosition, GamePortfolio
from myproject.companies.models import Company
from myproject import db
from datetime import datetime
from .domain import Portfolio, Position
from myproject.auth.models import User

def get_latest_price(ticker):
    url = f"https://stooq.pl/q/d/l/?s={ticker.lower()}&i=d"
    try:
        df = pd.read_csv(url)
        if not df.empty:
            last_row = df.iloc[-1]
            return float(last_row['Zamkniecie'])
    except Exception:
        return None

def get_prices_for_positions(positions):
    prices = {}
    for pos in positions:
        prices[pos.ticker] = get_latest_price(pos.ticker)
    return prices

def aggregate_positions(open_positions):
    """
    Aggregates positions by ticker.
    """
    agg = defaultdict(lambda: {'shares': 0, 'positions': [], 'buy_dates': []})
    for pos in open_positions:
        agg[pos.ticker]['shares'] += pos.shares
        agg[pos.ticker]['positions'].append(pos)
        agg[pos.ticker]['buy_dates'].append(pos.buy_date)
    return agg

def calculate_avg_buy_prices(portfolio_id, agg):
    """
    Calculates average buy prices for tickers based on all buy transactions, but only for shares currently held (open positions).
    Uwzględnia tylko najnowsze transakcje kupna, które odpowiadają aktualnej liczbie akcji w portfelu (FIFO).
    """
    avg_buy_prices = {}
    for ticker, data in agg.items():
        shares_left = data['shares']
        if shares_left == 0:
            avg_buy_prices[ticker] = None
            continue
        # Pobierz wszystkie transakcje kupna dla tickera, posortowane rosnąco po dacie
        buy_transactions = GameTransaction.query.filter_by(
            portfolio_id=portfolio_id, ticker=ticker, type='buy'
        ).order_by(GameTransaction.date.asc()).all()
        # Pobierz wszystkie transakcje sprzedaży dla tickera, posortowane rosnąco po dacie
        sell_transactions = GameTransaction.query.filter_by(
            portfolio_id=portfolio_id, ticker=ticker, type='sell'
        ).order_by(GameTransaction.date.asc()).all()
        # Oblicz ile akcji zostało "zużytych" przez sprzedaże (FIFO)
        sell_shares = sum(t.shares for t in sell_transactions)
        # Przejdź po transakcjach kupna i "zużyj" sprzedane akcje, zostaw tylko te, które odpowiadają obecnym pozycjom
        remaining_shares = shares_left
        total_cost = 0.0
        total_shares = 0
        for t in buy_transactions:
            if sell_shares >= t.shares:
                sell_shares -= t.shares
                continue
            buy_shares = t.shares - sell_shares if sell_shares > 0 else t.shares
            used_shares = min(buy_shares, remaining_shares)
            total_cost += used_shares * t.price
            total_shares += used_shares
            remaining_shares -= used_shares
            sell_shares = 0
            if remaining_shares == 0:
                break
        avg_price = total_cost / total_shares if total_shares > 0 else None
        avg_buy_prices[ticker] = avg_price
    return avg_buy_prices

def calculate_positions_with_prices(agg, avg_buy_prices, prices):
    """
    Calculates positions with current prices and profit percentages.
    """
    positions = []
    for ticker, data in agg.items():
        shares = data['shares']
        avg_price = avg_buy_prices[ticker]
        current_price = prices.get(ticker, 0)
        if current_price is None:
            current_price = 0
        value = shares * current_price
        profit_percent = ((current_price - avg_price) / avg_price * 100) if avg_price and avg_price > 0 else 0.0
        positions.append({
            'ticker': ticker,
            'shares': shares,
            'value': value,
            'profit_percent': profit_percent
        })
    return positions

def validate_buy(portfolio, ticker, shares, price, company):
    if not ticker or not company:
        return False, "Nie wybrano poprawnej spółki."
    if shares <= 0:
        return False, "Liczba akcji musi być większa od zera."
    cost = price * shares
    if portfolio.cash < cost:
        return False, "Brak środków na zakup."
    return True, ""

def execute_buy(portfolio, ticker, shares, price, company):
    company_id = company.id if company else None
    position = GamePosition(
        portfolio_id=portfolio.id,
        ticker=ticker,
        shares=shares,
        buy_price=price,
        buy_date=datetime.now(),
        company_id=company_id
    )
    transaction = GameTransaction(
        portfolio_id=portfolio.id,
        ticker=ticker,
        shares=shares,
        price=price,
        date=datetime.now(),
        type='buy',
        company_id=company_id
    )
    portfolio.cash -= price * shares
    db.session.add(position)
    db.session.add(transaction)
    db.session.commit()

def validate_sell(portfolio, ticker, shares, position):
    if not ticker or not position:
        return False, "Nie wybrano poprawnej spółki."
    if shares <= 0:
        return False, "Liczba akcji musi być większa od zera."
    if position.shares < shares:
        return False, "Brak wystarczającej liczby akcji do sprzedaży."
    return True, ""

def execute_sell(portfolio, ticker, shares, price, position):
    position.shares -= shares
    if position.shares == 0:
        db.session.delete(position)
    portfolio.cash += price * shares
    transaction = GameTransaction(
        portfolio_id=portfolio.id,
        ticker=ticker,
        shares=shares,
        price=price,
        date=datetime.now(),
        type='sell'
    )
    db.session.add(transaction)
    db.session.commit()

def get_or_create_portfolio(user_id):
    portfolio = GamePortfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        portfolio = GamePortfolio(user_id=user_id)
        db.session.add(portfolio)
        db.session.commit()
    return portfolio

def get_company_names():
    companies = Company.query.order_by(Company.name).all()
    return {c.ticker: c.name for c in companies}

def get_open_positions(portfolio_id):
    db_positions = GamePosition.query.filter_by(portfolio_id=portfolio_id, closed=False).all()
    return [p for p in db_positions if not p.closed]

def close_deleted_company_positions(portfolio_id):
    db_positions = GamePosition.query.filter_by(portfolio_id=portfolio_id, closed=False).all()
    changed = False
    for pos in db_positions:
        if pos.company_id is None and not pos.closed:
            pos.closed = True
            changed = True
    if changed:
        db.session.commit()

def get_transactions(portfolio_id):
    return GameTransaction.query.filter_by(portfolio_id=portfolio_id).order_by(GameTransaction.date.desc()).all()

def get_ranking_list():
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
        ranking_list.append({'username': username, 'total': total})
    ranking_list.sort(key=lambda x: x['total'], reverse=True)
    return ranking_list
