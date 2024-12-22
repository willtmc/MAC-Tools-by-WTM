from functools import wraps
from flask import session, request, abort, redirect, url_for, Blueprint
import secrets

security_bp = Blueprint('security', __name__)

@security_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.home'))

def init_security(app):
    """Initialize security features for the Flask app"""
    
    # Register security blueprint
    app.register_blueprint(security_bp)
    
    # CSRF Protection
    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            if request.endpoint and 'static' in request.endpoint:
                return
                
            token = session.get('_csrf_token', None)
            if not token:
                app.logger.error("No CSRF token in session")
                abort(403)
                
            # Check for token in form data, JSON body, or headers
            client_token = (
                request.form.get('csrf_token') or  # Form data
                (request.is_json and request.json.get('csrf_token')) or  # JSON body
                request.headers.get('X-CSRF-Token')  # Headers
            )
            
            if not client_token or client_token != token:
                app.logger.error(f"CSRF token mismatch. Session token: {token}, Client token: {client_token}")
                abort(403)

    def generate_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    # Security Headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Authentication decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'google_token' not in session:
                return abort(401)
            return f(*args, **kwargs)
        return decorated_function
        
    return login_required
