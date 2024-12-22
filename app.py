"""Minimal app.py for McLemore Auction Tools."""
import os
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from tools.neighbor_letters.routes import neighbor_letters
from tools.qr_labels.routes import qr_labels_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Register neighbor letters blueprint
    app.register_blueprint(neighbor_letters)
    # Register QR labels blueprint
    app.register_blueprint(qr_labels_bp, url_prefix='/qr-labels')

    @app.route('/')
    def index():
        return render_template('index.html')

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5003, debug=True)