from flask import Blueprint

companies = Blueprint('companies', __name__, url_prefix='/companies')

from . import views


