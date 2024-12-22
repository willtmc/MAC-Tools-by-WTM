from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, \
    send_from_directory, abort
import os
from tools.neighbor_letters import neighbor_letters
from tools.qr_labels import qr_labels_bp
import logging
import pytz
from dotenv import load_dotenv
from config import Config
from routes import bp, init_apis
from security import init_security
from logging_config import setup_logging

# Load environment variables
load_dotenv()

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Get module logger
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    
    # Load config
    app.config.from_object(Config)
    Config.init_app(app)
    
    # Set up logging
    setup_logging(app)
    logger.info('McLemore Auction Tools startup')
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for local development
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PREFERRED_URL_SCHEME'] = 'http'  # Set to http for local development
    
    # Initialize security features and get login_required decorator
    login_required = init_security(app)
    
    # Make login_required available to routes
    app.config['login_required'] = login_required
    
    # Register blueprints
    app.register_blueprint(bp)
    app.register_blueprint(neighbor_letters, url_prefix='/neighbor_letters')
    app.register_blueprint(qr_labels_bp, url_prefix='/qr_labels')
    
    # Initialize APIs
    init_apis()
    
    return app

# Entry point moved to run.py
