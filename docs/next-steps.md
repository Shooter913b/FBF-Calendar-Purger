# Next Steps: Tool 1 — FBF Calendar Purge (Web App)

Implementation plan for **Tool 1** as an instructor-facing web application.

| Layer | Stack |
|-------|--------|
| Core logic | Python 3.11+ (library, testable without UI) |
| API | FastAPI |
| Frontend | Next.js 14+ (App Router), TypeScript, Tailwind CSS |
| Spec reference | [tool-1-calendar-purge.md](./tool-1-calendar-purge.md) |

**Product goal:** An instructor opens a website, picks their course, previews stale Feedback Fruits calendar events, confirms once, and gets a clear success report—without touching the CLI, API docs, or tokens (production uses Canvas OAuth).

**Agent instructions:** Execute phases **in order**. Do not skip acceptance criteria. Mark each checkbox in this file when complete (`[x]`). If a step is blocked (e.g. no sample Canvas events for classifier tuning), document the blocker in a `docs/blockers.md` and continue with mock/fixture-based work where noted.

---

## Table of contents

1. [Repository layout](#1-repository-layout)
2. [Phase 0 — Prerequisites and configuration](#2-phase-0--prerequisites-and-configuration)
3. [Phase 1 — Python core library](#3-phase-1--python-core-library)
4. [Phase 2 — Classifier tuning workflow](#4-phase-2--classifier-tuning-workflow)
5. [Phase 3 — FastAPI backend](#5-phase-3--fastapi-backend)
6. [Phase 4 — Next.js frontend (instructor UX)](#6-phase-4--nextjs-frontend-instructor-ux)
7. [Phase 5 — Canvas OAuth (production auth)](#7-phase-5--canvas-oauth-production-auth)
8. [Phase 6 — Polish, accessibility, and safety](#8-phase-6--polish-accessibility-and-safety)
9. [Phase 7 — Deployment and operations](#9-phase-7--deployment-and-operations)
10. [Phase 8 — Future hooks (Tool 2, not in scope now)](#10-phase-8--future-hooks-tool-2-not-in-scope-now)
11. [API contract reference](#11-api-contract-reference)
12. [Definition of done](#12-definition-of-done)

---

## 1. Repository layout

Create a **monorepo** at the project root. Target structure:

```text
fbf-calendar-purger/
├── backend/
│   ├── pyproject.toml              # package: fbf_purge, deps, ruff/pytest
│   ├── fbf_purge/                  # importable library (no FastAPI imports here)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── canvas/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # HTTP + pagination + rate limit
│   │   │   └── models.py           # Pydantic models for API responses
│   │   ├── classifier/
│   │   │   ├── __init__.py
│   │   │   ├── rules.py            # is_feedback_fruits_event()
│   │   │   └── patterns.py         # load fbf_patterns.yaml
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── purge.py            # list + delete orchestration
│   │   │   └── courses.py          # list courses user can access
│   │   └── exceptions.py
│   ├── api/                        # FastAPI app only
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── deps.py                 # auth, settings injection
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── courses.py
│   │   │   └── purge.py
│   │   └── schemas.py              # request/response DTOs
│   ├── config/
│   │   └── fbf_patterns.yaml       # institution-tunable detection rules
│   ├── tests/
│   │   ├── fixtures/               # sample calendar event JSON
│   │   ├── test_classifier.py
│   │   ├── test_canvas_client.py
│   │   └── test_purge_service.py
│   └── Dockerfile
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # landing
│   │   │   ├── login/
│   │   │   ├── courses/
│   │   │   │   └── page.tsx        # course picker
│   │   │   └── purge/
│   │   │       └── [courseId]/
│   │   │           ├── page.tsx    # preview (dry-run)
│   │   │           └── confirm/
│   │   │               └── page.tsx
│   │   ├── components/
│   │   ├── lib/
│   │   │   └── api.ts              # typed fetch wrapper
│   │   └── types/
│   └── Dockerfile
├── docs/
│   ├── tool-1-calendar-purge.md
│   ├── tool-2-calendar-sync.md
│   └── next-steps.md               # this file
├── docker-compose.yml              # backend + frontend for local dev
├── .env.example
├── .gitignore
└── README.md
```

### Step 1.1 — Initialize monorepo scaffolding

- [ ] Create `backend/pyproject.toml` with:
  - Project name: `fbf-purge-backend`
  - Python `>=3.11`
  - Dependencies: `httpx`, `pydantic`, `pydantic-settings`, `pyyaml`, `tenacity` (retries)
  - Dev deps: `pytest`, `pytest-asyncio`, `respx` (mock httpx), `ruff`, `mypy`
  - Optional script entry: `fbf-purge = fbf_purge.cli:main` (CLI for debugging; not required for web UI)
- [ ] Create `frontend/` via `npx create-next-app@latest` with: TypeScript, ESLint, Tailwind, App Router, `src/` directory, no import alias beyond `@/*`.
- [ ] Add root `.gitignore`: `.env`, `__pycache__`, `.venv`, `node_modules`, `.next`, `*.csv` reports in dev.
- [ ] Add root `.env.example` (see Phase 0).

**Acceptance:** `cd backend && pip install -e ".[dev]" && pytest` runs (0 tests OK). `cd frontend && npm run build` succeeds.

---

## 2. Phase 0 — Prerequisites and configuration

### Step 0.1 — Environment variables

Document in `.env.example`:

```bash
# Canvas (required for dev until OAuth is done)
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_ACCESS_TOKEN=           # dev only; leave empty in production

# Canvas OAuth (Phase 5 — production)
CANVAS_CLIENT_ID=
CANVAS_CLIENT_SECRET=
CANVAS_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback

# API
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
SESSION_SECRET=                # random 32+ bytes for signed cookies

# App
FBF_PATTERNS_PATH=backend/config/fbf_patterns.yaml
RATE_LIMIT_REQUESTS_PER_SECOND=8
LOG_LEVEL=INFO
```

- [ ] Implement `backend/fbf_purge/config.py` using `pydantic-settings` `BaseSettings` reading the above.
- [ ] Never log or return `CANVAS_ACCESS_TOKEN` in API responses.

### Step 0.2 — Obtain calibration data (human / institution step)

Before classifier work is production-ready, collect real samples:

1. Pick one Canvas course with known Feedback Fruits calendar clutter.
2. Call `GET /api/v1/calendar_events?type=event&context_codes[]=course_{id}&all_events=1` with a teacher token.
3. Save 3–5 events that **are** FBF and 2–3 that **are not** into `backend/tests/fixtures/`.

- [ ] Add `backend/tests/fixtures/README.md` explaining how samples were collected (no tokens in repo).
- [ ] If no live data yet: use placeholder fixtures based on [tool-1-calendar-purge.md](./tool-1-calendar-purge.md) title patterns until real JSON is available.

**Acceptance:** Fixtures exist; `config.py` loads settings in tests via env override.

---

## 3. Phase 1 — Python core library

**Rule:** `fbf_purge/` must not import FastAPI. All Canvas and purge logic lives here so agents can test without running the web server.

### Step 1.1 — Canvas HTTP client (`canvas/client.py`)

Implement `CanvasClient` class:

```python
class CanvasClient:
    def __init__(self, base_url: str, access_token: str, rate_limit_rps: float = 8.0): ...

    async def get(self, path: str, params: dict | None = None) -> httpx.Response: ...
    async def delete(self, path: str) -> httpx.Response: ...

    async def paginate(self, path: str, params: dict | None = None) -> AsyncIterator[dict]: ...
```

**Requirements:**

- [ ] Prefix all paths with `/api/v1`; normalize `base_url` (no trailing slash).
- [ ] Set header: `Authorization: Bearer {token}`.
- [ ] **Pagination:** Parse RFC 5988 `Link` header (`rel="next"`). Yield each page’s JSON array items. Handle both list root and wrapped responses per Canvas endpoint.
- [ ] **Rate limiting:** Token bucket or sleep to honor `RATE_LIMIT_REQUESTS_PER_SECOND` (default 8).
- [ ] **Retries:** On 429 and 5xx, exponential backoff with `tenacity` (max 5 attempts).
- [ ] **Errors:** Map 401/403 to `CanvasAuthError`, 404 to `CanvasNotFoundError`, others to `CanvasAPIError` with status + body snippet.

**Methods to implement:**

| Method | Canvas endpoint | Notes |
|--------|-----------------|-------|
| `list_calendar_events(course_id)` | `GET /calendar_events` | `type=event`, `context_codes[]=course_{id}`, `all_events=true` |
| `delete_calendar_event(event_id)` | `DELETE /calendar_events/{id}` | Return parsed JSON body |
| `get_course(course_id)` | `GET /courses/{id}` | For display name + timezone |
| `list_courses_for_user()` | `GET /courses` | `enrollment_type=teacher`, `enrollment_state=active`, `per_page=100` |

- [ ] Write `test_canvas_client.py` using `respx` to mock pagination (two pages) and 429 retry.

### Step 1.2 — Pydantic models (`canvas/models.py`)

- [ ] `CalendarEvent`: `id`, `title`, `start_at`, `end_at`, `description`, `html_url`, `context_code`, `workflow_state`, `created_at`, `updated_at` (all optional where Canvas omits).
- [ ] `Course`: `id`, `name`, `course_code`, `time_zone`.
- [ ] `PurgeEventResult`: `event_id`, `title`, `start_at`, `status` (`matched` \| `deleted` \| `failed` \| `skipped`), `error_message` optional.
- [ ] `PurgeReport`: `course_id`, `course_name`, `dry_run`, `matched_count`, `deleted_count`, `failed_count`, `events: list[PurgeEventResult]`, `started_at`, `finished_at`.

### Step 1.3 — Classifier (`classifier/`)

**File:** `config/fbf_patterns.yaml` — institution-tunable:

```yaml
domains:
  - feedbackfruits.com
  - your-institution-fbf-host.example.edu

title_step_prefixes:
  - Give Feedback
  - Read Feedback
  - Hand in
  - Submissions
  - Receive Reviews
  - Reflection

title_suffix_separator: " - "

description_substrings:
  - feedbackfruits

exclude_title_regex: []   # optional safety valve
```

- [ ] `load_patterns(path: str) -> Patterns` in `patterns.py`.
- [ ] `is_feedback_fruits_event(event: CalendarEvent, patterns: Patterns) -> bool` in `rules.py`:
  1. If `workflow_state == "deleted"`, return False.
  2. If any `exclude_title_regex` matches `title`, return False.
  3. Match if **any** of:
     - `description` or `html_url` contains a configured domain (case-insensitive)
     - `description` contains any `description_substrings`
     - `title` starts with a known step prefix **and** contains `title_suffix_separator`
  4. Return bool + optional `match_reason` string for UI/debug.
- [ ] `classify_events(events, patterns) -> tuple[list[CalendarEvent], list[CalendarEvent]]` → `(fbf_events, other_events)`.
- [ ] Tests: each fixture file → expected match/non-match; add regression test per real sample from Phase 0.

### Step 1.4 — Purge service (`services/purge.py`)

```python
async def preview_purge(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
) -> PurgeReport: ...

async def execute_purge(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
) -> PurgeReport: ...
```

**`preview_purge` (dry-run):**

- [ ] Fetch course metadata for `course_name`.
- [ ] Paginate all calendar events; classify.
- [ ] For each FBF match, append `PurgeEventResult` with `status="matched"` (not deleted).
- [ ] Set `dry_run=True`, `matched_count=len(matches)`, `deleted_count=0`.

**`execute_purge`:**

- [ ] Same listing/classification as preview.
- [ ] For each matched event, `DELETE /calendar_events/{id}` sequentially (respect rate limit).
- [ ] On success: `status="deleted"`. On exception: `status="failed"`, continue others, increment `failed_count`.
- [ ] Set `dry_run=False`, `deleted_count` = count of deleted.
- [ ] Never delete events where `is_feedback_fruits_event` is False.

**Acceptance:** `pytest backend/tests` all pass with fixtures; manual CLI smoke test:

```bash
cd backend
python -m fbf_purge.cli --course-id COURSE_ID --dry-run   # optional thin CLI wrapper
```

### Step 1.5 — Optional CLI wrapper (`fbf_purge/cli.py`)

Thin `click` or `argparse` wrapper calling `preview_purge` / `execute_purge` for local debugging.

- [ ] Flags: `--course-id`, `--apply`, `--inspect` (prints first 5 raw events + classification).
- [ ] Not exposed in production UI; useful for agents and EdTech.

---

## 4. Phase 2 — Classifier tuning workflow

### Step 2.1 — Inspect mode (backend support)

- [ ] Add `inspect_course(client, course_id) -> dict` returning:
  - `sample_events`: first 10 calendar events (raw dict)
  - `classified`: list of `{id, title, is_fbf, match_reason}`
- [ ] Expose later as `GET /api/courses/{id}/inspect` (admin-only or dev-only flag).

### Step 2.2 — Tune `fbf_patterns.yaml`

- [ ] Run inspect against a real course; adjust YAML until zero false positives on non-FBF events in sample set.
- [ ] Document tuning process in `backend/config/README.md` for institutional admins.

**Acceptance:** On pilot course, instructor agrees preview list contains only Feedback Fruits calendar entries.

---

## 5. Phase 3 — FastAPI backend

### Step 3.1 — Application bootstrap

**File:** `backend/api/main.py`

- [ ] Create FastAPI app with title `FBF Calendar Purge API`, version `0.1.0`.
- [ ] CORS: allow `FRONTEND_URL` origin, credentials true.
- [ ] Include routers: `health`, `courses`, `purge`.
- [ ] Lifespan: load settings + patterns once at startup.
- [ ] Global exception handler → JSON `{ "detail": "...", "code": "..." }`.

**Run locally:**

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

Add `uvicorn[standard]` to pyproject dependencies.

### Step 3.2 — Auth dependency (dev → OAuth)

**File:** `backend/api/deps.py`

**Phase 3 (dev):**

- [ ] `get_canvas_client(request) -> CanvasClient`:
  - Read token from `Authorization: Bearer {token}` header **or** server env `CANVAS_ACCESS_TOKEN` when `DEV_MODE=true`.
  - Reject missing token with 401.

**Phase 5 will replace** with session-stored OAuth token (see Phase 5).

### Step 3.3 — Routes

#### `GET /health`

- [ ] Returns `{ "status": "ok" }`.

#### `GET /api/courses`

- [ ] Returns list of courses current user can purge (teacher enrollments).
- [ ] Response schema:

```json
{
  "courses": [
    { "id": 12345, "name": "Intro to Biology", "course_code": "BIO-101-2026" }
  ]
}
```

- [ ] Sort by `name` ascending.

#### `GET /api/courses/{course_id}/purge/preview`

- [ ] Calls `preview_purge`.
- [ ] Verify user has access to course (course appears in their list, or `GET /courses/{id}` succeeds).
- [ ] Returns `PurgeReport` JSON.

#### `POST /api/courses/{course_id}/purge`

- [ ] Request body: `{ "confirm": true, "acknowledged_count": 12 }` — `acknowledged_count` must equal `matched_count` from last preview (prevents stale confirm).
- [ ] Optional: require header `X-Confirm-Course-Id: {course_id}`.
- [ ] Calls `execute_purge`.
- [ ] Returns final `PurgeReport`.

#### `GET /api/courses/{course_id}/inspect` (optional)

- [ ] Guard with `ENABLE_INSPECT=true` env; for EdTech tuning only.

- [ ] Implement `backend/api/schemas.py` mirroring Pydantic models for OpenAPI.

### Step 3.4 — Session / preview token (anti-mistake)

- [ ] After preview, store in server session (or signed JWT, 15 min TTL): `course_id`, `matched_count`, `event_ids[]`, `preview_hash`.
- [ ] On `POST /purge`, verify `acknowledged_count` and `event_ids` still match current preview (re-fetch preview if stale → 409 Conflict with message to refresh).

Use `SESSION_SECRET` and `starlette.middleware.sessions.SessionMiddleware` **or** signed stateless JWT in httpOnly cookie.

### Step 3.5 — API tests

- [ ] `pytest` with `httpx.AsyncClient` + FastAPI `TestClient` / `ASGITransport`.
- [ ] Mock `CanvasClient` via dependency override.
- [ ] Test: preview returns matched events; execute deletes only matched; confirm mismatch returns 409.

**Acceptance:** OpenAPI docs at `http://localhost:8000/docs` show all routes; tests pass.

---

## 6. Phase 4 — Next.js frontend (instructor UX)

**Design principle:** Default path is **Preview → Review list → Type course name to confirm → Done**. No jargon (“calendar_events”, “API”, “Feedback Fruits integration” only in help text).

### Step 4.1 — API client (`frontend/src/lib/api.ts`)

- [ ] `apiGet<T>(path)`, `apiPost<T>(path, body)` using `BACKEND_URL` from `NEXT_PUBLIC_BACKEND_URL`.
- [ ] Include `credentials: 'include'` for session cookies.
- [ ] Typed interfaces matching backend schemas (`Course`, `PurgeReport`, `PurgeEventResult`).

### Step 4.2 — Page flow and routes

| Route | Purpose |
|-------|---------|
| `/` | Landing: what this tool does, who it's for, big “Get started” CTA |
| `/login` | Dev: explain token/OAuth; Prod: redirect to Canvas OAuth |
| `/courses` | Searchable list of teacher courses (cards) |
| `/purge/[courseId]` | Preview table + “Continue to confirm” |
| `/purge/[courseId]/confirm` | Final confirmation + execute |

### Step 4.3 — Landing page (`app/page.tsx`)

Copy guidelines:

- [ ] Headline: **“Clean up Feedback Fruits calendar dates”**
- [ ] Subhead: explains duplicates after course copy / deadline changes; **only removes calendar entries**, not assignments.
- [ ] 3-step visual: Choose course → Preview → Confirm
- [ ] Link: “How do I know this is safe?” → modal with dry-run explanation
- [ ] CTA button → `/courses` (or `/login` if unauthenticated)

### Step 4.4 — Course picker (`app/courses/page.tsx`)

- [ ] Fetch `GET /api/courses` on load; skeleton loading state.
- [ ] Search/filter by name or course code.
- [ ] Each card: course name, code, button **“Review calendar entries”** → `/purge/[id]`
- [ ] Empty state: “We couldn’t find courses where you’re a teacher.”
- [ ] Error state: friendly message if 401 → redirect to login.

### Step 4.5 — Preview page (`app/purge/[courseId]/page.tsx`)

- [ ] Fetch `GET /api/courses/{id}/purge/preview` on mount.
- [ ] Show course name at top.
- [ ] Summary banner: **“Found {n} Feedback Fruits calendar entries”** (if 0: celebration + “Nothing to clean up” + back link).
- [ ] Table columns: Date (localized), Title, Status badge “Will remove”
- [ ] Sort by `start_at` ascending.
- [ ] Sticky footer: **“Continue”** disabled when `n === 0`; enabled → `/purge/[courseId]/confirm`
- [ ] Secondary: “Download preview as CSV” (generate client-side from report).

### Step 4.6 — Confirm page (`app/purge/[courseId]/confirm/page.tsx`)

**Strong confirmation pattern (prevent mis-clicks):**

- [ ] Repeat summary: “You are about to remove **{n}** calendar entries from **{courseName}**.”
- [ ] Bulleted reminders:
  - Does not delete Canvas assignments or Feedback Fruits activities
  - Students will no longer see these calendar dates
  - You can re-save assignments in Feedback Fruits to recreate dates if needed
- [ ] Checkbox: “I have reviewed the list and understand entries will be permanently removed.”
- [ ] Text input: type exact phrase `REMOVE {n}` or course code to enable button (pick one pattern and document in UI).
- [ ] Primary button **“Remove calendar entries”** → `POST /api/courses/{id}/purge` with `acknowledged_count`.
- [ ] Loading: progress indicator “Removing 3 of 12…” if backend streams; else indeterminate spinner.
- [ ] On success → results view (same page or `/purge/[courseId]/done`).

### Step 4.7 — Results state

- [ ] Show: `deleted_count`, `failed_count` (if any), list of failures with titles.
- [ ] Success message: **“Calendar cleaned up”**
- [ ] Actions: “Back to my courses”, “Download report CSV”
- [ ] If failures: “Some entries couldn’t be removed” + support hint (permissions / try again).

### Step 4.8 — Shared UI components

- [ ] `Button`, `Card`, `Table`, `Alert`, `Modal`, `LoadingSkeleton` under `src/components/`.
- [ ] Use Tailwind; keep palette simple (institution-neutral blues/grays).
- [ ] Responsive: table scrolls horizontally on mobile.

### Step 4.9 — Frontend env

`frontend/.env.local.example`:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

- [ ] `docker-compose.yml` wires frontend to backend.

**Acceptance:** Full happy path works in dev with `CANVAS_ACCESS_TOKEN` and one real course.

---

## 7. Phase 5 — Canvas OAuth (production auth)

Replace dev token-in-header with **Canvas OAuth2** so instructors never handle tokens.

### Step 5.1 — Canvas developer key (institution)

Document for admins:

- [ ] Redirect URI: `{FRONTEND_URL}/api/auth/callback`
- [ ] Scopes: match [tool-1-calendar-purge.md](./tool-1-calendar-purge.md) — calendar read/delete, courses read
- [ ] Store `CLIENT_ID` / `CLIENT_SECRET` server-side only

### Step 5.2 — OAuth flow

**Option A (recommended):** Next.js route handler proxies to backend  
**Option B:** Backend handles OAuth entirely

- [ ] `GET /api/auth/login` → redirect to Canvas authorize URL (`response_type=code`, `client_id`, `redirect_uri`, `state`, scopes).
- [ ] `GET /api/auth/callback` → exchange code for access token; store in **httpOnly secure session cookie** (encrypted or server session store).
- [ ] `POST /api/auth/logout` → clear session.
- [ ] `get_canvas_client` reads token from session, not env.

### Step 5.3 — Frontend login

- [ ] `/login` → single button **“Sign in with Canvas”**
- [ ] Show user name after login in header; logout link.

**Acceptance:** End-to-end works without `CANVAS_ACCESS_TOKEN` in `.env` (only OAuth credentials).

---

## 8. Phase 6 — Polish, accessibility, and safety

### Step 6.1 — Error handling

| Code | User-facing message |
|------|---------------------|
| 401 | “Please sign in with Canvas again.” |
| 403 | “You don’t have permission to manage this course’s calendar.” |
| 409 | “The course calendar changed. Please review the list again.” |
| 429 | “Canvas is busy. Wait a moment and try again.” |
| 5xx | “Something went wrong on our end. Try again or contact support.” |

- [ ] Map in `api.ts`; never show raw JSON errors to users.

### Step 6.2 — Accessibility

- [ ] All buttons and inputs have labels; table uses `<th scope="col">`.
- [ ] Focus trap in confirmation modal.
- [ ] Color contrast WCAG AA for text and buttons.

### Step 6.3 — Logging and audit

- [ ] Backend structured logs: `user_id`, `course_id`, `action=preview|purge`, `matched_count`, `deleted_count` (no token in logs).
- [ ] Optional: persist purge reports server-side for institutional audit (Postgres/SQLite) — defer unless required.

### Step 6.4 — Rate limiting (public deployment)

- [ ] Per-IP or per-user rate limit on `POST /purge` (e.g. 10/hour) via `slowapi` or reverse proxy.

### Step 6.5 — Help content

- [ ] `/help` page: FAQ aligned with [tool-1-calendar-purge.md](./tool-1-calendar-purge.md) limitations.
- [ ] Link from every confirm page.

---

## 9. Phase 7 — Deployment and operations

### Step 7.1 — Docker

- [ ] `backend/Dockerfile`: multi-stage, run `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- [ ] `frontend/Dockerfile`: Next.js standalone output
- [ ] `docker-compose.yml`: `backend`, `frontend`, env files, network

### Step 7.2 — Production checklist

- [ ] HTTPS only; `Secure` cookies
- [ ] `SESSION_SECRET` rotated
- [ ] `fbf_patterns.yaml` mounted via config map / env-specific file
- [ ] Health check: `GET /health` for load balancer
- [ ] README: deploy steps, required Canvas developer key scopes, support contact

### Step 7.3 — CI

- [ ] GitHub Actions (or similar): `ruff`, `pytest`, `npm run lint`, `npm run build` on PR.

---

## 10. Phase 8 — Future hooks (Tool 2, not in scope now)

Do **not** implement now; leave extension points:

- [ ] `fbf_purge/services/` — add `sync.py` later for Tool 2.
- [ ] API route namespace `/api/courses/{id}/sync/*` reserved in docs.
- [ ] Frontend nav placeholder commented out.

See [tool-2-calendar-sync.md](./tool-2-calendar-sync.md).

---

## 11. API contract reference

### `GET /api/courses`

**Response 200:**

```json
{
  "courses": [
    { "id": 12345, "name": "Course Name", "course_code": "CODE-101" }
  ]
}
```

### `GET /api/courses/{course_id}/purge/preview`

**Response 200:** `PurgeReport` (see models). `dry_run: true`, events with `status: "matched"`.

### `POST /api/courses/{course_id}/purge`

**Request:**

```json
{
  "confirm": true,
  "acknowledged_count": 12
}
```

**Response 200:** `PurgeReport` with `dry_run: false`, events with `status: "deleted"` or `"failed"`.

**Response 409:** Preview stale; client should re-fetch preview.

---

## 12. Definition of done

Tool 1 web MVP is **done** when all of the following are true:

- [ ] Instructor can sign in (OAuth or dev token documented).
- [ ] Instructor sees only their active teacher courses.
- [ ] Preview lists only Feedback Fruits calendar events per tuned `fbf_patterns.yaml`.
- [ ] Confirm step requires explicit acknowledgment; cannot purge without preview.
- [ ] Purge deletes matched events and shows accurate success/failure report + CSV download.
- [ ] No Canvas token exposed to browser in production OAuth mode.
- [ ] `pytest` and frontend build pass in CI.
- [ ] README explains setup for developers and Canvas admins.

---

## Suggested agent execution order (summary)

| Order | Phase | Est. effort |
|-------|--------|-------------|
| 1 | 0 + 1.1 Repo layout & config | Small |
| 2 | 1.1–1.4 Python core + tests | Medium |
| 3 | 2 Classifier tuning with real fixtures | Small (blocked on samples) |
| 4 | 3 FastAPI | Medium |
| 5 | 4 Next.js UX | Large |
| 6 | 5 OAuth | Medium |
| 7 | 6–7 Polish & deploy | Medium |

Start with **Phase 1** completely test-green before building the Next.js confirm flow. The preview/confirm split is the most important safety property—implement and test it in the API before polishing UI copy.
