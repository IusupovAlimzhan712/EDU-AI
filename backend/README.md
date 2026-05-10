# EduAI Backend

Flask REST API. See the top-level `README.md` for the full setup guide.

## Quickstart

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    # Fill in SECRET_KEY, JWT_SECRET_KEY, DB_*
export FLASK_APP=run.py
flask db init && flask db migrate -m "initial" && flask db upgrade
python -m scripts.seed
python run.py
```

## Layout

```
app/
├── __init__.py          # create_app() factory
├── config.py            # Dev / Testing / Production configs
├── extensions.py        # SQLAlchemy, Migrate, JWT, Bcrypt, CORS
├── models/              # Entity layer (Section 4.6 of FYP1 report)
├── repositories/        # Data Access layer (Repository pattern)
├── services/            # Control classes:
│                          AccountService = AccountManager
│                          TopicService   = TopicManager
├── routes/              # HTTP API (Boundary layer)
└── utils/
    ├── errors.py        # Custom APIError → JSON
    └── validators.py    # Email / password / form-level checks
```

## Tests

```bash
pytest -v                # 16 tests, all passing
pytest --cov=app         # with coverage
```

Tests use an in-memory SQLite DB so they don't need MySQL.

## Endpoints

See the top-level README for the full list. Quick summary:

- `POST /api/auth/register` `/login` `/logout` `/refresh`
- `POST /api/auth/forgot-password` `/reset-password`
- `GET|PATCH|DELETE /api/me`, `POST /api/me/change-password`
- `GET /api/me/progress`, `GET /api/me/bookmarks`
- `GET /api/chapters`, `GET /api/topics`, `GET /api/topics/<id>`
- `POST|DELETE /api/topics/<id>/bookmark`
- `POST|DELETE /api/topics/<id>/complete`
