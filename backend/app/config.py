"""
Application configuration.

Loads environment variables and exposes them as Flask config values.
Different config classes (Development, Production, Testing) inherit from
the base Config class.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from the backend root directory
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))


class Config:

    """Base configuration - shared by all environments."""

    # --- Security ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-change-me'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-only-change-me-jwt'

    # JWT token lifetimes
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    )

    # --- Database ---
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'eduai')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

    # --- CORS ---
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    ]

    # --- Password reset ---
    PASSWORD_RESET_TOKEN_EXPIRES = int(
        os.environ.get('PASSWORD_RESET_TOKEN_EXPIRES', 3600)
    )
    DEV_RETURN_RESET_TOKEN = os.environ.get('DEV_RETURN_RESET_TOKEN', '1') == '1'

    # --- Email (optional) ---
    SMTP_HOST = os.environ.get('SMTP_HOST', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'noreply@eduai.local')

    # --- Frontend URL ---
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

    # --- Ollama (AI) ---
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'aya:8b')
    OLLAMA_TIMEOUT_SECONDS = int(os.environ.get('OLLAMA_TIMEOUT_SECONDS', 180))

    # --- Bcrypt ---
    BCRYPT_LOG_ROUNDS = 12


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True to log all SQL queries


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # Use an in-memory SQLite DB for tests so they run without a MySQL server
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    BCRYPT_LOG_ROUNDS = 4  # Faster hashing in tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def get_config():
    """Return the config class matching FLASK_ENV (defaults to development)."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
