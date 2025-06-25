"""
Moduł serwisów do gry giełdowej.

Ten moduł dostarcza funkcje pomocnicze do gry giełdowej, w tym:
- Pobieranie cen akcji ze Stooq
- Zarządzanie portfelem (kupno, sprzedaż, obliczanie pozycji i zysku)
- Przetwarzanie transakcji
- Obliczanie rankingu użytkowników
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
    Pobiera najnowszą cenę akcji z serwisu Stooq.
    
    Argumenty:
        ticker (str): Symbol giełdowy akcji.
        
    Zwraca:
        float lub None: Najnowsza cena zamknięcia dla danego tickera lub None, jeśli pobranie się nie powiodło.
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
    Pobiera najnowsze ceny dla listy pozycji.
    
    Argumenty:
        positions (list): Lista obiektów Position zawierających atrybut ticker.
        
    Zwraca:
        dict: Słownik mapujący tickery na ich najnowsze ceny.
    """
    prices = {}
    for pos in positions:
        prices[pos.ticker] = get_latest_price(pos.ticker)
    return prices

def aggregate_positions(open_positions):
    """
    Agreguje pozycje według symbolu tickera.
    
    Argumenty:
        open_positions (list): Lista pozycji do agregacji.
        
    Zwraca:
        dict: Słownik zagregowanych pozycji według tickerów, gdzie każda wartość zawiera:
            - shares: Łączna liczba akcji
            - positions: Lista obiektów pozycji
            - buy_dates: Lista dat zakupu wszystkich pozycji
    """
    agg = defaultdict(lambda: {'shares': 0, 'positions': [], 'buy_dates': []})
    for pos in open_positions:
        agg[pos.ticker]['shares'] += pos.shares
        agg[pos.ticker]['positions'].append(pos)
        agg[pos.ticker]['buy_dates'].append(pos.buy_date)
    return agg

def calculate_avg_buy_prices(portfolio_id, agg):
    """
    Oblicza średnie ceny zakupu dla tickerów na podstawie wszystkich transakcji kupna, uwzględniając tylko aktualnie posiadane akcje.
    
    Używa metody FIFO (First In, First Out), aby określić, które transakcje kupna odpowiadają obecnym pozycjom po uwzględnieniu sprzedaży.
    
    Argumenty:
        portfolio_id (int): ID portfela do obliczenia średnich cen
        agg (dict): Słownik zagregowanych pozycji zwrócony przez aggregate_positions()
        
    Zwraca:
        dict: Słownik mapujący tickery na ich średnie ceny zakupu
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
    Oblicza pozycje z aktualnymi cenami i procentowym zyskiem.
    
    Argumenty:
        agg (dict): Słownik zagregowanych pozycji zwrócony przez aggregate_positions()
        avg_buy_prices (dict): Słownik mapujący tickery na średnie ceny zakupu
        prices (dict): Słownik mapujący tickery na aktualne ceny rynkowe
        
    Zwraca:
        list: Lista obiektów Position z obliczonymi wartościami (aktualna wartość i procentowy zysk)
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
        profit_value = (current_price - avg_price) * shares if avg_price and avg_price > 0 else 0.0

        position = Position(
            ticker=ticker,
            shares=shares,
            buy_price=avg_price or 0,
            buy_date=max(data['buy_dates']) if data['buy_dates'] else datetime.now(),
            value=value,
            profit_pct=profit_percent
        )
        position.profit_value = profit_value  # kwotowy zysk/strata
        positions.append(position)
    return positions

def validate_buy(portfolio, ticker, shares, price, company):
    """
    Waliduje, czy transakcja kupna może zostać wykonana.
    
    Argumenty:
        portfolio (GamePortfolio): Obiekt portfela próbujący dokonać zakupu
        ticker (str): Symbol giełdowy akcji
        shares (int): Liczba akcji do kupienia
        price (float): Aktualna cena za akcję
        company (Company): Obiekt spółki powiązany z tickerem
        
    Zwraca:
        tuple: (is_valid, error_message), gdzie:
            - is_valid (bool): True jeśli transakcja jest poprawna, False w przeciwnym razie
            - error_message (str): Pusty string jeśli poprawna, w przeciwnym razie komunikat błędu
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
    Wykonuje transakcję kupna z obsługą błędów i zarządzaniem transakcją w bazie danych.
    
    Argumenty:
        portfolio (GamePortfolio): Obiekt portfela dokonujący zakupu
        ticker (str): Symbol giełdowy akcji
        shares (int): Liczba akcji do kupienia
        price (float): Aktualna cena za akcję
        company (Company): Obiekt spółki powiązany z tickerem
        
    Zwraca:
        tuple: (success, message), gdzie:
            - success (bool): True jeśli transakcja się powiodła, False w przeciwnym razie
            - message (str): Komunikat sukcesu lub błędu
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

def validate_sell(portfolio, ticker, shares, position=None):
    """
    Waliduje, czy transakcja sprzedaży może zostać wykonana dla sumy wszystkich pozycji.
    """
    if not ticker:
        return False, "Nie wybrano poprawnej spółki."
    if shares <= 0:
        return False, "Liczba akcji musi być większa od zera."
    all_positions = GamePosition.query.filter_by(portfolio_id=portfolio.id, ticker=ticker, closed=False).all()
    total_shares = sum(p.shares for p in all_positions)
    if total_shares < shares:
        return False, "Brak wystarczającej liczby akcji do sprzedaży."
    return True, ""


def execute_sell(portfolio, ticker, shares, price, position=None):
    """
    Sprzedaje akcje z wielu pozycji (FIFO) aż do wyczerpania żądanej liczby akcji.
    """
    try:
        positions = GamePosition.query.filter_by(portfolio_id=portfolio.id, ticker=ticker, closed=False).order_by(GamePosition.buy_date.asc()).all()
        shares_to_sell = shares
        company_id = None
        for pos in positions:
            if shares_to_sell <= 0:
                break
            if company_id is None and pos.company_id is not None:
                company_id = pos.company_id
            if pos.shares <= shares_to_sell:
                shares_to_sell -= pos.shares
                db.session.delete(pos)
            else:
                pos.shares -= shares_to_sell
                shares_to_sell = 0
        portfolio.cash += price * shares
        transaction = GameTransaction(
            portfolio_id=portfolio.id,
            ticker=ticker,
            shares=shares,
            price=price,
            date=datetime.now(),
            type='sell',
            company_id=company_id
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
    Pobiera istniejący portfel użytkownika lub tworzy nowy, jeśli nie istnieje.
    
    Argumenty:
        user_id (int): ID użytkownika, dla którego pobierany/tworzony jest portfel
        
    Zwraca:
        GamePortfolio: Znaleziony lub nowo utworzony obiekt portfela
    """
    portfolio = GamePortfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        portfolio = GamePortfolio(user_id=user_id)
        db.session.add(portfolio)
        db.session.commit()
    return portfolio

def get_company_names():
    """
    Pobiera wszystkie nazwy spółek mapowane na ich tickery.
    
    Zwraca:
        dict: Słownik mapujący tickery na nazwy spółek, posortowany alfabetycznie po nazwie
    """
    companies = Company.query.order_by(Company.name).all()
    return {c.ticker: c.name for c in companies}

def get_open_positions(portfolio_id):
    """
    Pobiera wszystkie otwarte pozycje dla danego portfela.
    
    Argumenty:
        portfolio_id (int): ID portfela, dla którego pobierane są pozycje
        
    Zwraca:
        list: Lista obiektów GamePosition, które są obecnie otwarte (niezamknięte)
    """
    db_positions = GamePosition.query.filter_by(portfolio_id=portfolio_id, closed=False).all()
    return [p for p in db_positions if not p.closed]

def close_deleted_company_positions(portfolio_id):
    """
    Zamyka pozycje, które nie mają już powiązanej spółki (usunięte spółki).
    
    Argumenty:
        portfolio_id (int): ID portfela do sprawdzenia pozycji z usuniętymi spółkami
        
    Zwraca:
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
    Pobiera wszystkie transakcje dla danego portfela, posortowane od najnowszych.
    
    Argumenty:
        portfolio_id (int): ID portfela, dla którego pobierane są transakcje
        
    Zwraca:
        list: Lista obiektów GameTransaction dla danego portfela
    """
    return GameTransaction.query.filter_by(portfolio_id=portfolio_id).order_by(GameTransaction.date.desc()).all()

def get_ranking_list():
    """
    Generuje ranking graczy na podstawie wartości ich portfeli.
    
    Oblicza całkowitą wartość (gotówka + pozycje) dla każdego portfela gracza
    i zwraca posortowaną listę z nazwami użytkowników i wartościami portfeli.
    
    Zwraca:
        list: Lista słowników z kluczami 'username' i 'total' (wartość portfela),
              posortowana malejąco po wartości portfela
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
    Oblicza łączny zysk/stratę portfela.
    
    Wylicza zarówno wartość bezwzględną zysku/straty, jak i procentowy zwrot
    na podstawie aktualnych wartości pozycji i ich średnich cen zakupu.
    
    Argumenty:
        positions (list): Lista obiektów Position z aktualnymi wartościami
        avg_buy_prices (dict): Słownik mapujący tickery na średnie ceny zakupu
        
    Zwraca:
        tuple: (total_profit, total_profit_percent), gdzie:
            - total_profit (float): Bezwzględna wartość zysku/straty w walucie
            - total_profit_percent (float): Procentowy zysk/strata względem kosztu
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
    Sprawdza, czy polska giełda jest otwarta (poniedziałek-piątek, 9:00-17:00), z wyłączeniem oficjalnych świąt (na sztywno dla 2025).
    
    Argumenty:
        now (datetime, opcjonalnie): Data i godzina do sprawdzenia. Domyślnie bierze aktualny czas.
        
    Zwraca:
        bool: True jeśli giełda jest otwarta, False w przeciwnym razie.
    """
    tz = pytz.timezone('Europe/Warsaw')
    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)
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
    if now.weekday() >= 5 or (now.year == 2025 and now.date() in holidays_2025):
        return False
    market_open = time(9, 0)
    market_close = time(17, 0)
    return market_open <= now.time() < market_close
