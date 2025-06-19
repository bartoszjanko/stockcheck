from myproject import db
from datetime import datetime
from sqlalchemy.orm import backref

# Reprezentuje portfel gry giełdowej jednego użytkownika.
class GamePortfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # Powiązanie z główną tabelą użytkowników (users).
    cash = db.Column(db.Float, default=100000.0)
    positions = db.relationship('GamePosition', backref='portfolio', lazy=True)

# Reprezentuje pojedynczą pozycję (inwestycję) w akcje w portfelu użytkownika.
class GamePosition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('game_portfolio.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', ondelete='SET NULL'), nullable=True)
    ticker = db.Column(db.String(10))  # kopia tickera na wypadek usunięcia spółki
    shares = db.Column(db.Integer)
    buy_price = db.Column(db.Float)
    buy_date = db.Column(db.Date, default=datetime.now)
    closed = db.Column(db.Boolean, default=False)  # czy pozycja zamknięta (np. spółka usunięta)
    company = db.relationship('Company', backref=backref('game_positions', passive_deletes=True))

# Reprezentuje pojedynczą transakcję (kupno lub sprzedaż) w grze.
class GameTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('game_portfolio.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', ondelete='SET NULL'), nullable=True)
    ticker = db.Column(db.String(10))  # kopia tickera na wypadek usunięcia spółki
    shares = db.Column(db.Integer)
    price = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.now) 
    type = db.Column(db.String(10))  # 'buy' lub 'sell'
    company = db.relationship('Company', backref=backref('game_transactions', passive_deletes=True))


"""
Pole ticker jest kopiowane do modeli gry giełdowej (GamePosition, GameTransaction), aby zachować informację o spółce nawet wtedy, gdy zostanie ona usunięta z głównej tabeli Company. 
Dzięki temu w historii transakcji i zamkniętych pozycjach zawsze widoczny jest ticker, niezależnie od zmian w bazie spółek. 
To zapewnia spójność i czytelność danych historycznych dla użytkownika.

Ticker w historii operacji nie zniknie, nawet jeśli spółka została usunięta.
Nazwa spółki pojawi się tylko, jeśli spółka istnieje w bazie.
Jeśli spółka została usunięta, pojawi się komunikat „(spółka usunięta)”, a ticker nadal będzie widoczny.

"""

