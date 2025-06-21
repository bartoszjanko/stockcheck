"""
Services module for the stock trading game.

This module provides helper functions for the stock trading game, including:
- Stock price fetching from Stooq
- Portfolio management (buying, selling, calculating positions and profit)
- Transaction processing
- User ranking calculations
"""

import pandas as pd
from collections import defaultdict
from .models import GameTransaction, GamePosition, GamePortfolio
from myproject.companies.models import Company
from myproject import db
from datetime import datetime, time, date
from .domain import Portfolio, Position
from myproject.auth.models import User
import pytz


def get_latest_price(ticker):
    """
    Fetches the latest stock price from Stooq.
    
    Args:
        ticker (str): The stock ticker symbol.
        
    Returns:
        float or None: The latest closing price for the given ticker, or None if fetching fails.
    """
    url = f"https://stooq.pl/q/d/l/?s={ticker.lower()}&i=d"
    try:
        df = pd.read_csv(url)
        if not df.empty:
            last_row = df.iloc[-1]
            return float(last_row['Zamkniecie'])
        else:
            print(f"Ostrzeżenie: Pusty dataframe dla tickera {ticker}")
            return None
    except Exception as e:
        print(f"Błąd podczas pobierania ceny dla {ticker}: {str(e)}")
        return None

def get_prices_for_positions(positions):
    """
    Fetches the latest prices for a list of positions.
    
    Args:
        positions (list): List of Position objects containing ticker attributes.
        
    Returns:
        dict: Dictionary mapping ticker symbols to their latest prices.
    """
    prices = {}
    for pos in positions:
        prices[pos.ticker] = get_latest_price(pos.ticker)
    return prices

def aggregate_positions(open_positions):
    """
    Aggregates positions by ticker symbol.
    
    Args:
        open_positions (list): List of position objects to aggregate.
        
    Returns:
        dict: Dictionary of aggregated positions keyed by ticker symbols, with each value containing:
            - shares: Total number of shares
            - positions: List of position objects
            - buy_dates: List of buy dates for all positions
    """
    agg = defaultdict(lambda: {'shares': 0, 'positions': [], 'buy_dates': []})
    for pos in open_positions:
        agg[pos.ticker]['shares'] += pos.shares
        agg[pos.ticker]['positions'].append(pos)
        agg[pos.ticker]['buy_dates'].append(pos.buy_date)
    return agg

def calculate_avg_buy_prices(portfolio_id, agg):
    """
    Calculates average buy prices for tickers based on all buy transactions, considering only shares currently held.
    
    Uses the FIFO (First In, First Out) method to determine which purchase transactions correspond to the
    current holdings after accounting for sales.
    
    Args:
        portfolio_id (int): ID of the portfolio to calculate average prices for
        agg (dict): Dictionary of aggregated positions returned by aggregate_positions()
        
    Returns:
        dict: Dictionary mapping ticker symbols to their average purchase prices
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
    
    Args:
        agg (dict): Dictionary of aggregated positions returned by aggregate_positions()
        avg_buy_prices (dict): Dictionary mapping tickers to average purchase prices
        prices (dict): Dictionary mapping tickers to current market prices
        
    Returns:
        list: List of Position objects with calculated values (current value and profit percentages)
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
        
        # Tworzenie obiektu Position zamiast słownika
        position = Position(
            ticker=ticker,
            shares=shares,
            buy_price=avg_price or 0,
            buy_date=max(data['buy_dates']) if data['buy_dates'] else datetime.now(),
            value=value,
            profit_pct=profit_percent
        )
        positions.append(position)
    return positions

def validate_buy(portfolio, ticker, shares, price, company):
    """
    Validates if a buy transaction can be executed.
    
    Args:
        portfolio (GamePortfolio): Portfolio object trying to make the purchase
        ticker (str): Stock ticker symbol
        shares (int): Number of shares to buy
        price (float): Current price per share
        company (Company): Company object associated with the ticker
        
    Returns:
        tuple: (is_valid, error_message) where:
            - is_valid (bool): True if transaction is valid, False otherwise
            - error_message (str): Empty string if valid, otherwise contains error message
    """
    if not ticker or not company:
        return False, "Nie wybrano poprawnej spółki."
    if shares <= 0:
        return False, "Liczba akcji musi być większa od zera."
    cost = price * shares
    if portfolio.cash < cost:
        return False, "Brak środków na zakup."
    return True, ""

def execute_buy(portfolio, ticker, shares, price, company):
    """
    Executes a buy transaction with error handling and database transaction management.
    
    Args:
        portfolio (GamePortfolio): Portfolio object making the purchase
        ticker (str): Stock ticker symbol
        shares (int): Number of shares to buy
        price (float): Current price per share
        company (Company): Company object associated with the ticker
        
    Returns:
        tuple: (success, message) where:
            - success (bool): True if transaction succeeded, False otherwise
            - message (str): Success or error message
    """
    try:
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
        return True, "Zakup zrealizowany pomyślnie."
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas realizacji zakupu: {str(e)}")
        return False, "Wystąpił błąd podczas wykonywania transakcji."

def validate_sell(portfolio, ticker, shares, position):
    """
    Validates if a sell transaction can be executed.
    
    Args:
        portfolio (GamePortfolio): Portfolio object trying to make the sale
        ticker (str): Stock ticker symbol
        shares (int): Number of shares to sell
        position (GamePosition): Position object representing the shares to be sold
        
    Returns:
        tuple: (is_valid, error_message) where:
            - is_valid (bool): True if transaction is valid, False otherwise
            - error_message (str): Empty string if valid, otherwise contains error message
    """
    if not ticker or not position:
        return False, "Nie wybrano poprawnej spółki."
    if shares <= 0:
        return False, "Liczba akcji musi być większa od zera."
    if position.shares < shares:
        return False, "Brak wystarczającej liczby akcji do sprzedaży."
    return True, ""

def execute_sell(portfolio, ticker, shares, price, position):
    """
    Executes a sell transaction with error handling and database transaction management.
    
    Args:
        portfolio (GamePortfolio): Portfolio object making the sale
        ticker (str): Stock ticker symbol
        shares (int): Number of shares to sell
        price (float): Current price per share
        position (GamePosition): Position object representing the shares to be sold
        
    Returns:
        tuple: (success, message) where:
            - success (bool): True if transaction succeeded, False otherwise
            - message (str): Success or error message
    """
    try:
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
            type='sell',
            company_id=position.company_id
        )
        db.session.add(transaction)
        db.session.commit()
        return True, "Sprzedaż zrealizowana pomyślnie."
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas realizacji sprzedaży: {str(e)}")
        return False, "Wystąpił błąd podczas wykonywania transakcji."

def get_or_create_portfolio(user_id):
    """
    Retrieves an existing portfolio for a user, or creates a new one if it doesn't exist.
    
    Args:
        user_id (int): ID of the user to get/create portfolio for
        
    Returns:
        GamePortfolio: The retrieved or newly created portfolio object
    """
    portfolio = GamePortfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        portfolio = GamePortfolio(user_id=user_id)
        db.session.add(portfolio)
        db.session.commit()
    return portfolio

def get_company_names():
    """
    Retrieves all company names mapped to their ticker symbols.
    
    Returns:
        dict: Dictionary mapping ticker symbols to company names, sorted alphabetically by name
    """
    companies = Company.query.order_by(Company.name).all()
    return {c.ticker: c.name for c in companies}

def get_open_positions(portfolio_id):
    """
    Retrieves all open positions for a given portfolio.
    
    Args:
        portfolio_id (int): ID of the portfolio to get positions for
        
    Returns:
        list: List of GamePosition objects that are currently open (not closed)
    """
    db_positions = GamePosition.query.filter_by(portfolio_id=portfolio_id, closed=False).all()
    return [p for p in db_positions if not p.closed]

def close_deleted_company_positions(portfolio_id):
    """
    Closes positions that no longer have an associated company (deleted companies).
    
    Args:
        portfolio_id (int): ID of the portfolio to check for deleted company positions
        
    Returns:
        None
    """
    db_positions = GamePosition.query.filter_by(portfolio_id=portfolio_id, closed=False).all()
    changed = False
    for pos in db_positions:
        if pos.company_id is None and not pos.closed:
            pos.closed = True
            changed = True
    if changed:
        db.session.commit()

def get_transactions(portfolio_id):
    """
    Retrieves all transactions for a given portfolio, ordered by date (newest first).
    
    Args:
        portfolio_id (int): ID of the portfolio to get transactions for
        
    Returns:
        list: List of GameTransaction objects for the specified portfolio
    """
    return GameTransaction.query.filter_by(portfolio_id=portfolio_id).order_by(GameTransaction.date.desc()).all()

def get_ranking_list():
    """
    Generates a player ranking based on the value of their portfolios.
    
    Calculates the total value (cash + positions) for each player's portfolio
    and returns a sorted list with usernames and total values.
    
    Returns:
        list: List of dictionaries with 'username' and 'total' (portfolio value) keys,
              sorted in descending order by total value
    """
    portfolios = GamePortfolio.query.all()
    ranking_list = []
    for p in portfolios:
        try:
            db_positions = GamePosition.query.filter_by(portfolio_id=p.id).all()
            positions = [Position(pos.ticker, pos.shares, pos.buy_price, pos.buy_date) for pos in db_positions]
            prices = get_prices_for_positions(positions)
            portfolio = Portfolio(p.cash, positions)
            total = portfolio.total_value(prices)
            user = User.query.get(p.user_id)
            username = user.username if user else f"Użytkownik {p.user_id}"
            ranking_list.append({'username': username, 'total': total})
        except Exception as e:
            print(f"Błąd podczas obliczania wartości portfela dla użytkownika {p.user_id}: {str(e)}")
            # Dodaj użytkownika do rankingu, ale z wartością 0
            try:
                user = User.query.get(p.user_id)
                username = user.username if user else f"Użytkownik {p.user_id}"
                ranking_list.append({'username': username, 'total': p.cash or 0})
            except:
                continue
    ranking_list.sort(key=lambda x: x['total'], reverse=True)
    return ranking_list

def calculate_portfolio_profit(positions, avg_buy_prices):
    """
    Calculates the total profit/loss for a portfolio.
    
    Computes both the absolute profit/loss value and the percentage return
    based on the current position values and their average purchase prices.
    
    Args:
        positions (list): List of Position objects with current values
        avg_buy_prices (dict): Dictionary mapping tickers to average purchase prices
        
    Returns:
        tuple: (total_profit, total_profit_percent) where:
            - total_profit (float): Absolute profit/loss value in currency
            - total_profit_percent (float): Percentage profit/loss relative to cost
    """
    total_profit = 0.0
    total_cost = 0.0
    for pos in positions:
        avg_price = avg_buy_prices.get(pos.ticker)
        if avg_price is not None and pos.shares > 0:
            total_cost += avg_price * pos.shares
            total_profit += (pos.value - avg_price * pos.shares)
    total_profit_percent = (total_profit / total_cost * 100) if total_cost > 0 else 0.0
    return total_profit, total_profit_percent

def is_market_open(now=None):
    """
    Checks if the Polish stock market is open (Monday-Friday, 9:00-17:00), excluding official holidays (hardcoded for 2025).
    
    Args:
        now (datetime, optional): Datetime to check. Defaults to current time.
        
    Returns:
        bool: True if market is open, False otherwise.
    """
    tz = pytz.timezone('Europe/Warsaw')
    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)
    # Hardcoded Polish stock market holidays for 2025
    holidays_2025 = set([
        date(2025, 1, 1),   # Nowy Rok
        date(2025, 1, 6),   # Trzech Króli
        date(2025, 4, 18),  # Wielki Piątek
        date(2025, 4, 21),  # Poniedziałek Wielkanocny
        date(2025, 5, 1),   # Święto Pracy
        date(2025, 6, 19),  # Boże Ciało
        date(2025, 8, 15),  # Wniebowzięcie NMP
        date(2025, 11, 11), # Święto Niepodległości
        date(2025, 12, 24), # Wigilia
        date(2025, 12, 25), # Boże Narodzenie
        date(2025, 12, 26), # Drugi dzień świąt
        date(2025, 12, 31), # Sylwester
    ])
    # Check if today is a weekend or holiday
    if now.weekday() >= 5 or (now.year == 2025 and now.date() in holidays_2025):
        return False
    market_open = time(9, 0)
    market_close = time(17, 0)
    return market_open <= now.time() < market_close
