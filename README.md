# EduAI — AI Study Companion for SPM Sejarah

Final Year Project 2 — Multimedia University, 2026
Student: Iusupov Alimzhan (1231301318)

> **Status:** Weeks 1–4 of the 14-week implementation plan (Phase 1 + the
> Account & Topic modules of Phase 2). Quiz / Essay / AI Tutor modules
> (Phases 2 weeks 5–6 and Phase 3) are NOT yet implemented.

---

## Project structure

```
EduAI_FYP2/
├── backend/                  # Flask REST API (business logic + data)
│   ├── app/
│   │   ├── models/           # Entity layer (SQLAlchemy ORM)
│   │   ├── repositories/     # Data Access layer (Repository pattern)
│   │   ├── services/         # Business Logic / Control classes
│   │   │                       (AccountManager, TopicManager)
│   │   ├── routes/           # Presentation/Boundary layer (HTTP API)
│   │   ├── utils/            # validators, custom errors
│   │   ├── config.py         # env-driven config
│   │   ├── extensions.py     # db, jwt, bcrypt, cors instances
│   │   └── __init__.py       # app factory
│   ├── migrations/           # Flask-Migrate (Alembic) — created on first run
│   ├── scripts/seed.py       # KSSM chapter + topic seed data
│   ├── tests/                # pytest sanity tests (16 passing)
│   ├── .env.example          # copy to .env and fill in
│   ├── requirements.txt
│   └── run.py                # `python run.py` or `flask run`
│
├── frontend/                 # React 18 + TypeScript + Vite (UI)
│   ├── src/
│   │   ├── pages/            # 15 prototype pages from FYP1
│   │   ├── components/       # shadcn/ui + custom components
│   │   ├── context/AuthContext.tsx
│   │   ├── lib/api.ts        # fetch wrapper for the backend
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example
│   └── package.json
│
├── db/
│   └── schema.sql            # Reference SQL schema
│
├── docs/
│   └── DEVIATIONS.md         # Variations from the FYP1 design
│
└── README.md                 # (this file)
```

---

## Architecture in one paragraph

The backend follows the **Layered (N-Tier) architecture** from Chapter 5 of
the FYP1 report. Each HTTP route (`routes/`) is thin: it parses JSON, calls
a **service** (`services/`), and serializes the result. Services hold the
business logic and depend on **repositories** (`repositories/`) — never on
`db.session` directly. Repositories wrap SQLAlchemy queries against
**models** (`models/`), which mirror the 9 entities + junction tables
defined in Section 4.6.1 of the report. This matches the
**Entity-Control-Boundary** pattern exactly: the routes are the Boundary,
the services are the Control classes (AccountManager → `AccountService`,
TopicManager → `TopicService`), and the models are the Entities.

The **Repository pattern** is implemented explicitly (one repo per
aggregate). The **Strategy** and **Facade** patterns from Section 5.3.3 will
appear in Phase 3 when the AI agents (RoutingAgent / KnowledgeAgent /
AssessmentAgent) are added.

---

## What's done — week by week

### ✅ Week 1 — System Setup (Phase 1)

- Flask app factory (`backend/app/__init__.py`)
- Config split (Development / Testing / Production)
- SQLAlchemy + Flask-Migrate, MySQL connection (PyMySQL)
- JWT auth (`flask-jwt-extended`), bcrypt password hashing
- CORS configured for the React dev server
- Centralized error handling (`utils/errors.py`)
- `.env.example`, `.gitignore`, pytest infrastructure
- Health check at `GET /api/health`

### ✅ Week 2 — Account Module (Phase 2.1)

Entities, repositories, service, and routes for:

- Student registration (UC 4.3.1 + 4.3.3 duplicate prevention)
- Email + password authentication (UC 4.3.2)
- Login session create/touch/deactivate (UC 4.3.5, 4.3.6)
- Password reset via single-use SHA-256-hashed token (UC 4.3.4)
- Profile read / update, password change, account delete
- Auto-creation of the one-to-one `LearningProgress` row on registration

### ✅ Weeks 3-4 — Topic Module (Phase 2.2)

Entities, repositories, service, and routes for:

- Browse syllabus by Form Level + Chapter (UC 4.3.16)
- Topic detail (UC 4.3.12) with bookmark/completion state attached
- Bookmark / unbookmark (UC 4.3.14)
- Mark complete / unmark complete (UC 4.3.7)
- `/me/progress` aggregated dashboard data (completion rate +
  per-chapter breakdown)
- `/me/bookmarks` for the Bookmarks page
- KSSM Form 4 + Form 5 chapter and starter-topic seed data

### ⏸️ Phase 2.3 (weeks 5-6) and Phase 3 (weeks 7-9) — TODO

- Quiz module (Quiz, QuizQuestion, QuizAttempt, AttemptAnswer)
- AI Tutor module (RoutingAgent / KnowledgeAgent / AssessmentAgent)
- Essay submission + evaluation
- ContentValidator for KSSM alignment

---

## Why no LangChain (yet)?

The AI Integration is **Phase 3 (Week 7+)**. For the first four weeks
(setup + auth + topic CRUD) LangChain would add complexity for zero
benefit, so I deliberately left it out.

`requirements.txt` already lists `langchain` / `langchain-community` /
`langchain-core` as **commented-out** entries, ready to be uncommented in
Phase 3. The recommendation when you get there: yes, use it.

- `langchain_community.llms.Ollama` gives you a clean wrapper around the
  local Ollama server on port 11434 (matches Section 5.4 deployment).
- `ConversationBufferMemory` handles the chat-history requirement
  (UC 4.3.10 "Handle Follow-up Questions") for free.
- LangChain's `RunnableBranch` / chains map cleanly onto the **Strategy
  Pattern** that drives the RoutingAgent in Section 5.3.3 — the abstract
  `Agent` interface becomes a `Runnable`, and the RoutingAgent becomes a
  simple branching chain.

---

## Endpoints (currently implemented)

```
Public
  GET    /api/health
  POST   /api/auth/register
  POST   /api/auth/login
  POST   /api/auth/forgot-password     → returns devResetToken in dev mode
  POST   /api/auth/reset-password

Authenticated (Bearer token)
  POST   /api/auth/logout
  POST   /api/auth/refresh             → requires refresh token

  GET    /api/me                       → current profile
  PATCH  /api/me                       → update fullName / formLevel
  DELETE /api/me                       → delete account
  POST   /api/me/change-password

  GET    /api/me/progress              → progress overview
  GET    /api/me/bookmarks             → bookmarked topics

  GET    /api/chapters                 → all chapters
  GET    /api/chapters?form_level=4    → chapters for one form

  GET    /api/topics                   → list (filter: form_level, chapter_id, search)
  GET    /api/topics/<id>              → topic detail + status

  POST   /api/topics/<id>/bookmark
  DELETE /api/topics/<id>/bookmark
  POST   /api/topics/<id>/complete
  DELETE /api/topics/<id>/complete
```

---

## Setup & run guide

### Prerequisites

| Tool        | Version    | Why                              |
|-------------|------------|----------------------------------|
| Python      | 3.10+      | Flask backend                    |
| MySQL       | 8.0+       | Persistent storage               |
| Node.js     | 18+        | Vite dev server for the frontend |
| npm         | 9+ (any)   | Frontend dependencies            |

### 1️⃣ Create the database

```bash
mysql -u root -p
mysql> CREATE DATABASE eduai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
mysql> exit
```

### 2️⃣ Backend setup

```bash
cd backend

# Create + activate a virtual environment
python -m venv venv
source venv/bin/activate            # macOS/Linux
# venv\Scripts\activate              # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy the example env and fill in YOUR values
cp .env.example .env
# Now open .env and fill in:
#   SECRET_KEY              → run `python -c "import secrets; print(secrets.token_hex(32))"`
#   JWT_SECRET_KEY          → a different random hex string from the same command
#   DB_USER, DB_PASSWORD    → your MySQL credentials
#
# Everything else has sensible defaults.

# Run database migrations (creates the 8 tables)
export FLASK_APP=run.py              # macOS/Linux
# $env:FLASK_APP="run.py"             # Windows PowerShell
flask db init                        # only the first time
flask db migrate -m "initial schema"
flask db upgrade

# Seed the KSSM Sejarah chapters and starter topics
python -m scripts.seed

# Start the server
python run.py
# → http://localhost:5000
```

You can sanity-check with:

```bash
curl http://localhost:5000/api/health
# {"status":"ok","service":"EduAI Backend"}
```

### 3️⃣ Frontend setup

```bash
cd ../frontend

# Optional: copy the example env (the default already points at localhost:5000)
cp .env.example .env.local

# Install dependencies
npm install

# Start the dev server
npm run dev
# → http://localhost:3000
```

The frontend dev server will auto-open at http://localhost:3000.

### 4️⃣ Try it out

1. Click **Register** and create an account (any email, password must be
   8+ chars with upper, lower, and a digit).
2. You'll be auto-logged in and dropped on the Dashboard.
3. Click **Topics** in the sidebar — you'll see the chapters and starter
   topics from the seed data.
4. Bookmark a couple of topics, then visit **Bookmarks** in the sidebar.
5. Visit **Settings** to update your form level or change your password.

### 5️⃣ Run backend tests

```bash
cd backend
pytest -v
# → 16 passed
```

Tests use an in-memory SQLite DB so they don't touch your MySQL server.

---

## Manual values you need to fill in

All marked with `<-- FILL THIS` in `backend/.env.example`:

| Variable          | What                                                       |
|-------------------|------------------------------------------------------------|
| `SECRET_KEY`      | Random 64-char hex string (use `secrets.token_hex(32)`)    |
| `JWT_SECRET_KEY`  | A **different** random 64-char hex string                  |
| `DB_USER`         | Your MySQL username (usually `root`)                       |
| `DB_PASSWORD`     | Your MySQL password                                        |
| `SMTP_*`          | Only if you want real password-reset emails (optional)     |

Reserved for Phase 3 (commented out — uncomment when you start AI work):

| Variable           | What                                              |
|--------------------|---------------------------------------------------|
| `OLLAMA_BASE_URL`  | `http://localhost:11434`                          |
| `OLLAMA_MODEL`     | e.g. `llama3.1:8b` or `mistral:7b`                |

---

## Troubleshooting

**`Can't connect to MySQL server`** — make sure MySQL is running and the
`DB_USER`/`DB_PASSWORD` in `.env` are correct. Test with
`mysql -u $DB_USER -p`.

**`CORS error` in the browser** — confirm `CORS_ORIGINS` in `backend/.env`
includes the URL your frontend is on (default
`http://localhost:3000,http://127.0.0.1:3000`).

**`flask db migrate` says "No changes detected"** — if the `migrations/`
folder doesn't exist yet, run `flask db init` first.

**Frontend says "Failed to load topics"** — check the backend is running
on port 5000 (`curl http://localhost:5000/api/health`) and that you ran
`python -m scripts.seed`.

**Password-reset email never arrives** — that's expected unless you
configured SMTP. The dev mode (`DEV_RETURN_RESET_TOKEN=1`) returns the
token directly in the API response, and the Forgot Password page displays
it on screen so you can paste it into a reset form.

---

## What to build next (Week 5+)

Following the Gantt chart in the FYP1 report:

- **Weeks 5-6:** Quiz Module — `Quiz`, `QuizAttempt`, `AttemptAnswer`
  models + `QuizService` (`QuizManager`)
- **Weeks 7-9:** AI Integration — Ollama setup, then `RoutingAgent`,
  `KnowledgeAgent`, `AssessmentAgent`, `ContentValidator` (this is where
  LangChain comes in)
- **Weeks 10-12:** Wire the remaining frontend pages (AI Tutor, Quiz
  flow, Essay flow, My Progress dashboard)
- **Week 13:** Testing & QA — target SUS score ≥ 70 (NFR1.1)
- **Week 14:** Deployment packaging

The architecture is set up so each new module follows the same pattern:
1. Add entities to `models/`
2. Add a repository to `repositories/`
3. Add a service to `services/`
4. Add a route blueprint to `routes/` and register it in `__init__.py`

This is the layered architecture from the design report doing exactly
what it's meant to do — letting you add modules without touching the
existing ones.
