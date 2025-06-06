"""
W pliku domain.py znajdują się klasy domenowe gry giełdowej, które odpowiadają za logikę biznesową portfela i pozycji inwestycyjnych. 
Te klasy nie są powiązane bezpośrednio z bazą danych – służą do operacji i obliczeń w kodzie aplikacji.
Te klasy pozwalają na wygodne operowanie portfelem i pozycjami w kodzie gry giełdowej: 
liczenie wartości, zysku, dodawanie i usuwanie pozycji – niezależnie od sposobu przechowywania danych w bazie. 
To czysta logika biznesowa, zgodna z zasadami programowania obiektowego.

"""

# Reprezentuje pojedynczą inwestycję w akcje danej spółki.
class Position:
    def __init__(self, ticker, shares, buy_price, buy_date):
        self.ticker = ticker
        self.shares = shares
        self.buy_price = buy_price
        self.buy_date = buy_date

    def current_value(self, current_price):
        return self.shares * current_price

    def profit_percent(self, current_price):
        if self.buy_price == 0:
            return 0
        return ((current_price - self.buy_price) / self.buy_price) * 100

# Reprezentuje cały portfel inwestycyjny użytkownika w grze.
class Portfolio:
    def __init__(self, cash, positions):
        self.cash = cash
        self.positions = positions  # lista obiektów Position

    def total_value(self, prices_dict):
        value = self.cash
        for pos in self.positions:
            value += pos.current_value(prices_dict.get(pos.ticker, 0))
        return value

    def add_position(self, position):
        self.positions.append(position)

    def remove_position(self, ticker, shares):
        for pos in self.positions:
            if pos.ticker == ticker:
                if pos.shares > shares:
                    pos.shares -= shares
                else:
                    self.positions.remove(pos)
                break
