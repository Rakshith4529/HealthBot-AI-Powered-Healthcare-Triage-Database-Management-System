import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, g, request, redirect, url_for, session, jsonify
from app.config import config
from app.database import init_app, init_db


def create_app(env='default'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[env])

    # Logging
    if not app.debug:
        handler = RotatingFileHandler('medassist.log', maxBytes=1_000_000, backupCount=3)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
        app.logger.addHandler(handler)
    else:
        logging.basicConfig(level=logging.DEBUG)

    # DB
    init_app(app)

    # Auto-create DB if not exists
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        init_db(app)
        app.logger.info("Database initialized from schema.sql")

    # Request hooks
    @app.before_request
    def set_request_id():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def secure_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Root redirect
    @app.route('/')
    def index():
        if 'patient_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        if request.is_json:
            return jsonify({'error': 'Forbidden'}), 403
        return _err_page('403 Forbidden', 'You do not have permission.'), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.is_json:
            return jsonify({'error': 'Not found'}), 404
        return _err_page('404 Not Found', 'Page not found.'), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"500: {request.url} | {e}")
        if request.is_json:
            return jsonify({'error': 'Internal server error'}), 500
        return _err_page('500 Error', 'Something went wrong. Please try again.'), 500

    def _err_page(title, msg):
        return f"""<!DOCTYPE html><html><head><title>{title} – MedAssist</title>
        <style>body{{font-family:sans-serif;background:#060d1f;color:#e2e8f0;text-align:center;padding:80px}}
        h1{{color:#00d4aa}}a{{color:#00d4aa}}</style></head>
        <body><h1>{title}</h1><p>{msg}</p><a href="/">← Home</a></body></html>"""

    # Register blueprints
    from app.routes.auth import auth
    from app.routes.dashboard import dashboard
    from app.routes.chat import chat
    from app.routes.profile import profile
    from app.routes.admin import admin
    from app.routes.doctor import doctor

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(chat)
    app.register_blueprint(profile)
    app.register_blueprint(admin)
    app.register_blueprint(doctor)

    return app
