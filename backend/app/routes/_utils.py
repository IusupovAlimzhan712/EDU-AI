"""Shared route-layer helpers (request parsing only)."""
from flask import request

from ..utils.errors import BadRequestError


def _body() -> dict:
    """Return the JSON request body or raise a 400."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequestError('Request body must be JSON.')
    return data


def _int_arg(name: str) -> int | None:
    """Parse an integer query parameter, or raise a 400 if malformed."""
    raw = request.args.get(name)
    if raw is None or raw == '':
        return None
    try:
        return int(raw)
    except ValueError:
        raise BadRequestError(f'Query parameter `{name}` must be an integer.')
