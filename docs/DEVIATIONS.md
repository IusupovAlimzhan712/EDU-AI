# Deviations from the FYP1 Design

This document records places where the implementation deliberately
departs from the FYP1 interim report, with the reasoning behind each
change. The N-Tier architecture, ECB pattern, Strategy/Facade/Repository
design patterns, 7 control classes, and 9 entities all **remain exactly
as designed** — these deviations are surface-level only.

---

## 1. React frontend instead of Jinja2 templates

**Report says:** Section 6.3.4 — HTML/CSS/JS frontend with Jinja2
template inheritance.

**Implementation:** React 18 + TypeScript + Vite + shadcn/ui, with the
backend returning JSON instead of HTML.

**Reason:** A high-fidelity React prototype was built during FYP1 to
validate the UI design before committing to the template engine. Rewriting
in Jinja2 would discard that investment and regress the user experience.
The deviation is superficial — it only affects the Presentation Layer
technology. All business logic, data access, and the layered architecture
are unchanged. The backend simply emits JSON instead of rendered HTML,
which is what every modern Flask app does anyway.

---

## 2. Additional fields on `Student`: `fullName` and `formLevel`

**Report says:** Table 4.30 lists only `studentId`, `email`,
`passwordHash`, `registrationDate`.

**Implementation:** The `student` table also has `fullName VARCHAR(100)`
and `formLevel INT` (with `CHECK (formLevel IN (4, 5))`).

**Reason:** The FYP1 prototype Register page (Section 5.5.2) and Settings
page (Section 5.5.14) both collect and display these two fields. Without
them the frontend would have no way to greet the student by name or show
their default form level. They're additive — the original four columns
are still there with the same constraints.

---

## 3. New entity: `PasswordResetToken`

**Report says:** UC 4.3.4 (Reset Password) is described as a flow but the
data dictionary does not specify the storage mechanism.

**Implementation:** Added a `password_reset_token` table with
`tokenId`, `studentId` (FK), `tokenHash` (SHA-256, NOT the raw token),
`expiresAt`, `used`, `createdAt`.

**Reason:** Stateless implementations of password reset are insecure
(they can't be revoked or one-shot). Storing a hash of the token is a
standard pattern that allows single-use tokens with expiry. This addition
is what makes UC 4.3.4 actually implementable. The Account Module
(`AccountService`) owns the token lifecycle exactly as the design
intended — it's a new entity but not a new control class.

---

## 4. Optional fields on `Topic`: `estimatedDurationMinutes`, `pdfReference`

**Report says:** Table 4.34 lists only `topicId`, `formLevel`, `chapterId`,
`topicName`, `content`.

**Implementation:** Added two **nullable** optional columns:
- `estimatedDurationMinutes INT NULL` — drives the "15 min" duration
  label shown on each topic card in the prototype (Section 5.5.4).
- `pdfReference VARCHAR(500) NULL` — reserved for Phase 4 when the
  three-panel Topic Content page (Section 5.5.5) embeds the KSSM PDF.

**Reason:** Both are nullable so they can't break anything; they exist so
the frontend cards already designed in FYP1 have somewhere to read their
data from. If the supervisor objects, they can be dropped with a single
migration and an update to `models/topic.py`.

---

## 5. JWT-based sessions instead of opaque session IDs

**Report says:** Section 4.4.1.5 / Table 4.31 (Session entity) implies
classic server-side session storage with a session ID issued at login.

**Implementation:** Login issues a JWT access token + refresh token
(`flask-jwt-extended`). Each JWT contains a unique `jti` which is stored
as the `sessionId` in the `session` table. Logout flips `isActive` for
that row, and the route decorator (`@auth_required`) rejects any JWT
whose session is no longer active.

**Reason:** This gives us the best of both worlds — the statelessness of
JWT (no DB lookup needed on every request for routes that don't care
about revocation) plus the **revocability** of server-side sessions
(which is what the Session entity is for in the first place). The
`session` table schema is unchanged; we just use the JWT's `jti` as the
session ID, which keeps the data model identical to the report.

---

## 6. LangChain reserved for Phase 3, not used in Weeks 1–4

**Report says:** Section 6.3.3 describes the AI Integration in Phase 3
(weeks 7–9).

**Implementation:** No AI code at all in the Weeks 1–4 deliverable.
`requirements.txt` lists `langchain`, `langchain-community`,
`langchain-core` as commented-out entries.

**Reason:** Phase 3 hasn't started yet. When it does, LangChain is the
right choice — its `Ollama` wrapper, conversation memory primitives,
and chain abstractions map cleanly onto the Strategy pattern described
in Section 5.3.3 (`Agent` interface + `RoutingAgent` selecting
implementations at runtime).

---

## Summary

| Deviation                            | Impact      | Architecture effect |
|--------------------------------------|-------------|---------------------|
| React frontend                       | Presentation only | None — backend returns JSON |
| `fullName` + `formLevel` on Student  | Additive    | None — same control class |
| `PasswordResetToken` table           | Additive    | None — owned by AccountManager |
| Optional fields on Topic             | Additive    | None — nullable, no logic change |
| JWT + Session table                  | Mechanism only | None — Session entity unchanged |
| LangChain deferred                   | Scope only  | None — Phase 3 work |

All 7 control classes, 9 entities, and the N-Tier + ECB + Strategy /
Facade / Repository patterns from Chapter 5 are preserved exactly.
