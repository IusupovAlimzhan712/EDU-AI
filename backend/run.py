"""
Entry point for the Flask development server.

Usage:
    flask run                  # uses FLASK_APP=run.py from .env
    python run.py              # alternative

Production: do not use this — use a proper WSGI server (gunicorn, etc.)
"""
import os

from app import create_app


app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
