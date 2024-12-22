from flask import Blueprint

qr_labels_bp = Blueprint(
    'qr_labels_bp', 
    __name__, 
    template_folder='templates'
)

from . import routes