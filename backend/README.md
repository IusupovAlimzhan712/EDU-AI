# EduAI Backend

Flask 3 REST API — N-Tier / ECB architecture.

> For the full project overview, API endpoint reference, and quick-start guide see the top-level `README.md`.

---

## Directory Layout

```
backend/
├── app/
│   ├── __init__.py          # create_app() factory + blueprint registration
│   ├── config.py            # Dev / Testing / Production config classes
│   ├── extensions.py        # SQLAlchemy, Migrate, JWT, Bcrypt, CORS singletons
│   ├── models/              # Entity layer (SQLAlchemy ORM)
│   │   ├── student.py
│   │   ├── chapter.py
│   │   ├── topic.py
│   │   ├── topic_chunk.py
│   │   ├── quiz.py
│   │   ├── quiz_attempt.py
│   │   ├── cause_effect_diagram.py
│   │   ├── essay_question.py
│   │   └── essay_attempt.py
│   ├── repositories/        # Data Access layer (Repository pattern)
│   │   ├── student_repository.py
│   │   ├── topic_repository.py
│   │   └── quiz_repository.py
│   ├── services/            # Business Logic / Control layer
│   │   ├── account_service.py
│   │   ├── topic_service.py
│   │   ├── quiz_service.py
│   │   ├── essay_service.py
│   │   └── ai/
│   │       ├── tutor_chain.py      # LangChain RAG chain for AI Tutor
│   │       ├── quiz_chain.py       # MCQ generation
│   │       └── essay_grader.py     # Struktur F/H/C + Esei Aras 1-4 grading
│   ├── routes/              # Boundary layer (HTTP endpoints)
│   │   ├── auth.py
│   │   ├── account.py
│   │   ├── topics.py
│   │   ├── quizzes.py
│   │   ├── conversations.py
│   │   └── essay.py
│   └── utils/
│       ├── errors.py        # APIError → structured JSON responses
│       └── validators.py    # Email / password / form-level validation
├── migrations/              # Flask-Migrate (Alembic) migration history
├── scripts/
│   ├── seed.py              # Seed KSSM chapters + topics from syllabus data
│   └── ingest_pdf.py        # Parse and chunk PDF files into topic_chunk table
├── seed_cause_effect.py     # Generate Mermaid cause-effect diagrams via GPT-4o-mini
├── seed_essays.py           # Generate SPM essay questions via GPT-4o-mini
├── tests/                   # pytest test suite (SQLite in-memory)
├── run.py                   # Flask dev server entry point (port 5001)
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- OpenAI API key

### Steps

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — fill in SECRET_KEY, JWT_SECRET_KEY, DB_PASSWORD, OPENAI_API_KEY

# 4. Create the MySQL database
mysql -u root -p -e "CREATE DATABASE eduai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 5. Run database migrations
export FLASK_APP=run.py
flask db upgrade

# 6. Seed chapters and topics
python -m scripts.seed

# 7. Start the server
python run.py
# Listening on http://localhost:5001
```

### Seed AI-generated content (one-time, after server is running)

```bash
# Cause-effect Mermaid diagrams for all 20 KSSM chapters (~2 min)
python seed_cause_effect.py

# SPM Kertas 2 essay questions (~10 min)
python seed_essays.py
```

Both scripts are idempotent — re-running skips already-generated records.  
Pass `--regen` to force regeneration of existing content.

### Ingest PDF topic content

Place PDFs in `static/pdfs/` following the naming convention, then:

```bash
python -m scripts.ingest_pdf
```

---

## Running Tests

```bash
pytest -v                            # all tests
pytest --cov=app --cov-report=term-missing   # with coverage
```

Tests use an in-memory SQLite database and do not require MySQL or an OpenAI key.

---

## Architecture Notes

The backend follows strict **N-Tier / ECB (Entity-Control-Boundary)** separation:

- **Routes** (Boundary) — parse HTTP request, call one service method, return JSON. No business logic, no `db.session` access.
- **Services** (Control) — all business logic, transaction management, LLM calls.
- **Repositories** (Data Access) — all SQLAlchemy queries, no business logic.
- **Models** (Entity) — ORM definitions + `to_dict()` serializers only.

### AI Integration

- **AI Tutor**: LangChain RAG chain with BM25 + semantic retrieval over `topic_chunk` table. Streams responses via SSE.
- **Quiz generation**: GPT-4o-mini generates MCQ sets on demand per chapter and difficulty level.
- **Essay grading**: Two-path grader — Struktur uses F/H/C code tree matching; Esei uses the official SPM Aras 1-4 rubric with note-form detection and score cap enforcement.
- **Cause-effect diagrams**: GPT-4o-mini generates Mermaid flowchart strings, stored in `cause_effect_diagram` table and rendered client-side.

### Password Reset

In development, set `DEV_RETURN_RESET_TOKEN=1` in `.env` to receive the reset token directly in the API response (no email needed). Set to `0` in production and configure SMTP variables.

---

## Key Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | JWT signing key (must differ from SECRET_KEY) |
| `DB_USER` / `DB_PASSWORD` | MySQL credentials |
| `OPENAI_API_KEY` | Required for all AI features |
| `OPENAI_MODEL` | Default: `gpt-4o-mini` |
| `DEV_RETURN_RESET_TOKEN` | Set `1` in dev to skip email on password reset |

See `.env.example` for the full list with descriptions.
