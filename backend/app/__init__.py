"""
Flask application factory.

Implements the layered (N-Tier) architecture defined in Chapter 5 of the
FYP1 report:
    routes/        -> Presentation/Boundary layer (HTTP API)
    services/      -> Business Logic / Control classes
                      (AccountManager, TopicManager, ...)
    repositories/  -> Data Access layer (Repository pattern)
    models/        -> Entity layer (SQLAlchemy ORM)
"""
import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import get_config
from .extensions import db, migrate, bcrypt, jwt, cors


def create_app(config_class=None):
    """Application factory.

    Args:
        config_class: Optional config class. If None, picked from FLASK_ENV.

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuration ---
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # --- Logging ---
    _configure_logging(app)

    # --- Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
        supports_credentials=True,
    )

    # --- Make sure all models are registered before migrate sees them ---
    with app.app_context():
        from . import models  # noqa: F401

    # --- Blueprints (routes) ---
    from .routes.health import health_bp
    from .routes.auth import auth_bp
    from .routes.account import account_bp
    from .routes.topics import topics_bp
    from .routes.progress import progress_bp
    from .routes.quizzes import quizzes_bp
    from .routes.tutor import tutor_bp

    app.register_blueprint(tutor_bp, url_prefix='/api')
    app.register_blueprint(quizzes_bp, url_prefix='/api')
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(account_bp, url_prefix='/api/me')
    app.register_blueprint(topics_bp, url_prefix='/api')
    app.register_blueprint(progress_bp, url_prefix='/api/me')

    # --- Error handlers ---
    _register_error_handlers(app)

    # --- JWT error handlers ---
    _register_jwt_handlers(app)

    return app


def _configure_logging(app):
    """Set up basic console logging."""
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    )


def _register_error_handlers(app):
    """Convert Werkzeug HTTPExceptions and our custom errors to JSON."""
    from .utils.errors import APIError

    @app.errorhandler(APIError)
    def handle_api_error(err):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return jsonify({
            'error': err.name,
            'message': err.description,
        }), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        app.logger.exception('Unhandled exception')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.',
        }), 500


def _register_jwt_handlers(app):
    """Standard JSON responses for JWT errors."""

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({'error': 'Unauthorized', 'message': reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({'error': 'Invalid Token', 'message': reason}), 422

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token Expired',
            'message': 'The token has expired. Please log in again.',
        }), 401
