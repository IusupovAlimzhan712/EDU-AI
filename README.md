# EduAI Study Companion

A React + TypeScript study companion app with AI tutoring, quizzes, essay practice, and progress tracking.

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** (dev server & bundler)
- **Tailwind CSS v4** (pre-compiled in `src/index.css`)
- **shadcn/ui** components (Radix UI primitives)
- **Lucide React** icons
- **Recharts** for progress charts

## Getting Started

```bash
npm install
npm run dev
```

The app opens at http://localhost:3000

## Build for Production

```bash
npm run build
```

Output goes to `dist/`.

## Pages

| Page | Route Key |
|------|-----------|
| Login / Register / Forgot Password | Auth screens |
| Dashboard | Overview & quick actions |
| Topics Browser | Browse study topics |
| Topic Content | Read topic material |
| AI Tutor | Chat with AI |
| Quiz Selection / In Progress / Results | Quiz flow |
| Essay Practice / Writing / Feedback | Essay flow |
| My Progress | Charts & stats |
| Bookmarks | Saved content |
| Settings | User preferences |

## Notes

- Navigation is client-side state in `App.tsx` (no React Router needed for this prototype)
- All data is currently mocked — connect your own API to make it dynamic
- The AI Tutor page is UI-only; wire up the Anthropic API to make it functional
