from flask import Blueprint

indices = Blueprint('indices', __name__, url_prefix='/indices')

from . import views