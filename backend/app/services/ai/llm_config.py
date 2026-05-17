"""Centralised Ollama configuration — read once, used everywhere."""
from flask import current_app


def get_ollama_base_url() -> str:
    return current_app.config['OLLAMA_BASE_URL']


def get_ollama_model() -> str:
    return current_app.config['OLLAMA_MODEL']


def get_ollama_timeout() -> int:
    return current_app.config['OLLAMA_TIMEOUT_SECONDS']