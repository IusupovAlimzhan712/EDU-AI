"""Health-check endpoint used to verify the server is up."""
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'EduAI Backend'})
