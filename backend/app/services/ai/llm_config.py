"""Centralised OpenAI configuration — read once, used everywhere."""
from flask import current_app


def get_openai_api_key() -> str:
    return current_app.config['OPENAI_API_KEY']


def get_openai_model() -> str:
    return current_app.config['OPENAI_MODEL']


def get_openai_timeout() -> int:
    return current_app.config['OPENAI_TIMEOUT_SECONDS']
