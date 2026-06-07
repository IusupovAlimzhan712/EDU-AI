# EduAI — AI Study Companion for SPM Sejarah

**Final Year Project 2 · Multimedia University · 2026**
**Student:** Iusupov Alimzhan (1231301318)

EduAI is a web-based AI-powered learning platform built specifically for Malaysian Form 4 and Form 5 students preparing for the SPM Sejarah (History) examination. It combines topic-based content delivery, AI tutoring, quiz assessment, and SPM-style essay practice in a single integrated system aligned with the KSSM Sejarah syllabus.

---

## Features

| Module | What it does |
|--------|-------------|
| **Topic Learning** | Browse the full KSSM Sejarah syllabus (Form 4 + Form 5) organised by chapter. Read PDF topic content with a built-in viewer and chat with the AI Tutor about the current page. |
| **Cause-Effect Diagrams** | Each of the 20 chapters has an AI-generated Mermaid flowchart visualising causes → central event → effects in Bahasa Malaysia. |
| **AI Tutor** | Conversational AI grounded in KSSM content via RAG. Maintains chat history per topic. Streams responses token-by-token. Constrained to syllabus-aligned content only. |
| **Quiz & Assessment** | AI-generated multiple-choice quizzes per chapter. Configurable difficulty and question count. Instant feedback with per-question explanations. Full attempt history. |
| **Essay Practice** | Full SPM Kertas 2 simulator. Struktur questions graded against an F/H/C code tree (Mana-mana N×1m). Esei questions graded against the official Aras 1–4 rubric. Note-form penalty enforced. SSE-streamed grading results. |
| **My Progress** | Per-chapter mastery score (weighted: 40% quiz + 25% essay + 35% completion). Focus Areas weakness ranking. Study streak heatmap. |
| **Bookmarks** | Save and revisit topics flagged as difficult. |
| **Settings** | Update profile, form level, quiz preferences, and password. |

---

## Architecture

```
EduAI_FYP2/
├── backend/                   # Flask REST API
│   ├── app/
│   │   ├── models/            # Entity layer (SQLAlchemy ORM)
│   │   ├── repositories/      # Data Access layer (Repository pattern)
│   │   ├── services/          # Business Logic / Control layer
│   │   │   └── ai/            # LangChain chains (tutor, quiz, essay)
│   │   ├── routes/            # Presentation / Boundary layer (HTTP API)
│   │   └── utils/             # validators, custom errors
│   ├── scripts/               # Ingestion and diagnostic scripts
│   ├── migrations/            # Flask-Migrate (Alembic)
│   ├── seed_cause_effect.py   # Generate cause-effect diagrams via GPT-4o-mini
│   ├── seed_essays.py         # Generate SPM essay questions via GPT-4o-mini
│   ├── tests/                 # pytest test suite
│   └── requirements.txt
│
├── frontend/                  # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── pages/             # One file per page (Dashboard, Topics, AI Tutor, etc.)
│   │   ├── components/        # shadcn/ui + custom components (MermaidDiagram, etc.)
│   │   ├── context/           # AuthContext (JWT token management)
│   │   └── lib/api.ts         # Typed fetch wrapper for the backend
│   └── package.json
│
├── db/schema.sql              # Reference SQL schema
├── docs/DEVIATIONS.md         # Documented deviations from FYP1 design
└── README.md                  # This file
```

The backend follows a strict **N-Tier / ECB (Entity-Control-Boundary)** architecture. Routes are thin boundaries, services hold all business logic, repositories abstract all database access, and models define the entity layer. No route ever touches `db.session` directly.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Mermaid.js |
| Backend | Python 3.11, Flask 3, SQLAlchemy 2, Flask-JWT-Extended, Flask-Migrate |
| Database | MySQL 8 |
| AI | OpenAI GPT-4o-mini via LangChain, RAG with BM25 + semantic retrieval |
| Auth | JWT (access + refresh tokens), bcrypt password hashing |

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| MySQL | 8.0+ |
| Node.js | 18+ |
| npm | 9+ |
| OpenAI API key | Required for AI Tutor, Quiz generation, Essay grading |

### 1. Create the database

```bash
mysql -u root -p
mysql> CREATE DATABASE eduai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
mysql> exit
```

### 2. Backend setup

```bash
cd backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in:
#   SECRET_KEY, JWT_SECRET_KEY    → python -c "import secrets; print(secrets.token_hex(32))"
#   DB_USER, DB_PASSWORD          → your MySQL credentials
#   OPENAI_API_KEY                → your OpenAI API key

export FLASK_APP=run.py           # Windows: $env:FLASK_APP="run.py"
flask db upgrade                  # creates all tables
python -m scripts.seed            # seeds KSSM chapters + topics
python run.py
# Backend running at http://localhost:5001
```

### 3. Seed AI-generated content (one-time)

With the backend running and the database seeded:

```bash
# Generate cause-effect diagrams for all 20 chapters (~2 minutes)
python seed_cause_effect.py

# Generate SPM essay questions for all chapters (~10 minutes)
python seed_essays.py
```

Both scripts are idempotent — re-running skips already-generated content.

### 4. Ingest PDF topic content

Place topic PDF files in `backend/static/pdfs/` following the naming convention, then run:

```bash
python -m scripts.ingest_pdf
```

### 5. Frontend setup

```bash
cd frontend

cp .env.example .env.local        # defaults to http://localhost:5001

npm install
npm run dev
# Frontend running at http://localhost:3000
```

### 6. Try it out

1. Open `http://localhost:3000` and register an account
2. Browse **Topics** → open a chapter → view PDF content and cause-effect diagram
3. Click the **AI** button to ask the AI Tutor questions about the current topic
4. Go to **Quizzes** → start a quiz for a chapter
5. Go to **Essay Practice** → attempt a Struktur or Esei question
6. Check **My Progress** for your chapter mastery breakdown

---

## API Endpoints

### Authentication
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
POST   /api/auth/forgot-password
POST   /api/auth/reset-password
```

### Account
```
GET    /api/me
PATCH  /api/me
DELETE /api/me
POST   /api/me/change-password
```

### Topics & Chapters
```
GET    /api/chapters
GET    /api/chapters?form_level=4
GET    /api/chapters/<form_level>/<chapter_id>/cause-effect
GET    /api/topics
GET    /api/topics/<id>
GET    /api/topics/<id>/pdf
POST   /api/topics/<id>/bookmark
DELETE /api/topics/<id>/bookmark
POST   /api/topics/<id>/complete
DELETE /api/topics/<id>/complete
```

### Progress & Bookmarks
```
GET    /api/me/progress
GET    /api/me/bookmarks
```

### Quizzes
```
GET    /api/quizzes
GET    /api/quizzes/<id>
POST   /api/quizzes/<id>/attempts
GET    /api/me/quiz-attempts
GET    /api/me/quiz-attempts/<id>
POST   /api/me/quiz-attempts/<id>/answer
POST   /api/me/quiz-attempts/<id>/submit
```

### AI Tutor
```
GET    /api/conversations/<topic_id>
POST   /api/conversations/<topic_id>/messages   (SSE stream)
DELETE /api/conversations/<topic_id>
```

### Essay Practice
```
GET    /api/essay-questions
GET    /api/essay-questions/<id>
POST   /api/essay-questions/<id>/attempts
GET    /api/me/essay-attempts
GET    /api/me/essay-attempts/<id>
PATCH  /api/me/essay-attempts/<id>/draft
POST   /api/me/essay-attempts/<id>/submit
GET    /api/me/essay-attempts/<id>/stream       (SSE stream)
```

---

## Running Tests

```bash
cd backend
pytest -v
pytest --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite database and do not require MySQL or an OpenAI key.

---

## Known Limitations

- **Concurrent users:** The development server (Werkzeug) handles ~10–20 concurrent users. For 50+ concurrent users, deploy with Gunicorn + gevent workers.
- **Password reset via email:** The forgot-password flow exists in the API (`/api/auth/forgot-password`) but email dispatch requires SMTP configuration. In development, set `DEV_RETURN_RESET_TOKEN=1` in `.env` to receive the token directly in the API response.
- **AI provider:** Uses OpenAI GPT-4o-mini (cloud API) rather than a local LLM. An internet connection and OpenAI API key are required for all AI features.
- **Notification preferences:** Identified as future work. Planned: study reminders, quiz result summaries, and essay grading completion alerts.
- **Data export:** The "Download My Data" feature is identified as future work.

---

## Environment Variables

See `backend/.env.example` for the full list. Required variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key (random hex string) |
| `JWT_SECRET_KEY` | JWT signing key (different random hex string) |
| `DB_USER` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `OPENAI_API_KEY` | OpenAI API key (required for AI features) |
