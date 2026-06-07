# EduAI Frontend

React 18 + TypeScript + Vite single-page application.

> For the full project overview and feature descriptions see the top-level `README.md`.

---

## Directory Layout

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx        # Home dashboard with progress summary
│   │   ├── Topics.tsx           # Chapter and topic browser
│   │   ├── TopicContent.tsx     # PDF viewer + Cause-Effect diagram tabs + AI chat panel
│   │   ├── AITutor.tsx          # Standalone AI Tutor conversation view
│   │   ├── Quizzes.tsx          # Quiz list and attempt history
│   │   ├── QuizAttempt.tsx      # Live quiz session with per-question feedback
│   │   ├── EssayPractice.tsx    # Essay question browser
│   │   ├── EssayWriting.tsx     # Essay writing editor with live note-form detection
│   │   ├── EssayFeedback.tsx    # Graded result with F/H/C tree or Aras descriptor table
│   │   ├── MyProgress.tsx       # Chapter mastery, focus areas, study streak heatmap
│   │   ├── Bookmarks.tsx        # Saved topics
│   │   └── Settings.tsx         # Profile, learning preferences, account management
│   ├── components/
│   │   ├── AppSidebar.tsx       # Main navigation sidebar
│   │   ├── MermaidDiagram.tsx   # Client-side Mermaid SVG renderer
│   │   └── ui/                  # shadcn/ui component library
│   ├── context/
│   │   └── AuthContext.tsx      # JWT token management, /me fetch, refreshProfile()
│   ├── lib/
│   │   └── api.ts               # Typed fetch wrapper for all backend endpoints
│   ├── App.tsx                  # Root component — page routing and auth gate
│   └── main.tsx                 # Vite entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## Setup

### Prerequisites

- Node.js 18+
- npm 9+
- Backend running on port 5001

### Steps

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env.local
# .env.local defaults to http://localhost:5001 — change VITE_API_BASE_URL if needed

# 3. Start the dev server
npm run dev
# App available at http://localhost:3000
```

### Build for production

```bash
npm run build
# Output written to dist/
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:5001` | Backend API base URL |

---

## Key Design Decisions

### Routing

`App.tsx` manages routing via a `currentPage` state string rather than React Router. Navigation is handled by passing an `onNavigate` callback down to each page and sidebar component. This keeps the bundle simple for a single-user academic prototype.

### Authentication

`AuthContext` stores the JWT access token in memory (not `localStorage`) and uses an `httpOnly`-compatible refresh token pattern. `refreshProfile()` re-fetches `/api/me` after profile updates so all components stay in sync.

### AI Tutor Streaming

The AI Tutor uses Server-Sent Events (SSE) via a native `EventSource`. The `api.ts` wrapper exposes a `streamTutorMessage` function that returns the `EventSource` instance so callers can close it on unmount.

### Cause-Effect Diagrams

`MermaidDiagram.tsx` calls `mermaid.render()` inside a `useEffect` and injects the returned SVG string directly into the DOM. The component is initialized once with `startOnLoad: false` to prevent Mermaid from scanning the DOM on load. Each diagram gets a unique ID via React's `useId()` to avoid collision when multiple diagrams are mounted.

### Essay Grading SSE

`EssayFeedback.tsx` opens an `EventSource` to `/api/me/essay-attempts/<id>/stream` immediately after submission. It listens for `status`, `result`, and `error` events and closes the stream on the `done` event or on unmount.

---

## Type Conventions

All API types are defined in `src/lib/api.ts`. The key interfaces are:

- `Student` — authenticated user profile
- `Chapter`, `Topic` — KSSM syllabus structure
- `CauseEffectDiagram` — Mermaid diagram record
- `Quiz`, `QuizAttempt`, `QuizQuestion` — quiz session types
- `EssayQuestion`, `EssayAttempt`, `MarkingScheme`, `CodeNode` — essay practice types
- `ProgressOverview`, `ChapterProgress` — My Progress data

---

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18 | UI framework |
| TypeScript | 5 | Type safety |
| Vite | 5 | Build tool and dev server |
| Tailwind CSS | 3 | Utility-first styling |
| shadcn/ui | — | Accessible component primitives |
| Mermaid.js | 10 | Client-side flowchart rendering |
| Lucide React | — | Icon set |
