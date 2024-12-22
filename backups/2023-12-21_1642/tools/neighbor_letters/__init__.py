from flask import Blueprint

neighbor_letters_bp = Blueprint('neighbor_letters', __name__, url_prefix='/neighbor_letters')

from . import routes