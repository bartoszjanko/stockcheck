from myproject import db
from datetime import date

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
    ticker = db.Column(db.String(10))
    shares = db.Column(db.Integer)
    buy_price = db.Column(db.Float)
    buy_date = db.Column(db.Date, default=date.today)

# Reprezentuje pojedynczą transakcję (kupno lub sprzedaż) w grze.
class GameTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('game_portfolio.id'))
    ticker = db.Column(db.String(10))
    shares = db.Column(db.Integer)
    price = db.Column(db.Float)
    date = db.Column(db.Date, default=date.today)
    type = db.Column(db.String(10))  # 'buy' lub 'sell'
