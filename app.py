"""Flask application factory."""
import os
import logging
import logging.config
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

from config import config
from routes import bp, init_apis
from tools.neighbor_letters.routes import neighbor_letters
from tools.qr_labels.routes import qr_labels_bp

# Load environment variables
load_dotenv()

def create_app(config_name=None):
    """Create Flask application."""
    # Create app
    app = Flask(__name__)
    
    # Load config
    if isinstance(config_name, dict):
        # Handle direct config dict
        app.config.update(config_name)
    else:
        # Load from config object
        if config_name is None:
            config_name = os.getenv('FLASK_ENV', 'development')
        app.config.from_object(config[config_name])
    
    # Initialize extensions
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Register blueprints
    app.register_blueprint(bp)
    app.register_blueprint(neighbor_letters)
    app.register_blueprint(qr_labels_bp, url_prefix='/labels')
    
    # Initialize APIs
    with app.app_context():
        init_apis()
    
    return app
