from flask import Blueprint

stock_game = Blueprint('stock_game', __name__, url_prefix='/game')

from . import views
