"""
WSGI entry point for production deployment.
Use this file with Gunicorn: gunicorn wsgi:app
"""
from app import create_app

app = create_app()
