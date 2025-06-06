"""
W pliku services.py znajdują się funkcje pomocnicze do pobierania aktualnych cen akcji ze Stooq dla gry giełdowej:

"""

import pandas as pd

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
