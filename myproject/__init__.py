import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Inicjalizacja rozszerzeń bez aplikacji
# (będą zainicjalizowane w create_app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Konfiguracja
    app.config['SECRET_KEY'] = 'mysecretkey'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicjalizacja rozszerzeń
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Import modeli (potrzebne do migracji i user_loader)
    from myproject.auth.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Rejestracja blueprintów
    from myproject.auth import auth
    from myproject.admin import admin
    from myproject.reports import reports
    from myproject.recommendations import recommendations
    from myproject.core import core
    from myproject.companies import companies
    from myproject.forum import forum
    from myproject.stock_game import stock_game
    from myproject.indices import indices

    app.register_blueprint(core)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(reports)
    app.register_blueprint(recommendations)
    app.register_blueprint(companies)
    app.register_blueprint(forum)
    app.register_blueprint(stock_game)
    app.register_blueprint(indices)

    return app


