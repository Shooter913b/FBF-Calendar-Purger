# FBF Calendar Purger

Web app for instructors to remove stale **Feedback Fruits** calendar entries from Canvas courses—common after course copies or deadline changes.

## Stack

- **Backend:** Python 3.11+, FastAPI, `fbf_purge` core library
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS

## Quick start (local)

You need **two terminals** — backend and frontend.

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` at the project root — see [docs/oauth-setup.md](./docs/oauth-setup.md) for OAuth setup.

### 2. Backend (terminal 1)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn api.main:app --reload --port 8000
```

### 3. Frontend (terminal 2)

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**. Sign-in goes through the frontend; API calls are proxied to port 8000.

If sign-in fails, confirm the backend is running (`http://localhost:8000/health` should return `{"status":"ok"}`).

### 4. Tests

```bash
cd backend && pytest
```

## Sign-in (Canvas OAuth)

Instructors sign in with their own Canvas account. See **[docs/oauth-setup.md](./docs/oauth-setup.md)** for:

1. Creating a Canvas **Developer Key** (redirect URI + scopes)
2. Setting `CANVAS_CLIENT_ID` and `CANVAS_CLIENT_SECRET` in `.env`
3. Keeping `DEV_MODE=false`

Redirect URI for local dev:

```text
http://localhost:3000/api/auth/callback
```

**Dev fallback** (single shared token, no OAuth): set `DEV_MODE=true` and `CANVAS_ACCESS_TOKEN=` in `.env`.

## User flow

1. Sign in with Canvas (OAuth)
2. Choose a course
3. **Scan** — select events to delete
4. **Delete selected**

## Canvas API scopes (Developer Key)

- `url:GET|/api/v1/courses`
- `url:GET|/api/v1/calendar_events`
- `url:DELETE|/api/v1/calendar_events/:id`
- `url:GET|/api/v1/users/self/profile`

## Tuning detection

Edit `backend/config/fbf_patterns.yaml` for your institution. See `backend/config/README.md`.

Optional inspect endpoint: `ENABLE_INSPECT=true` → `GET /api/courses/{id}/inspect`

## Documentation

- [OAuth setup](./docs/oauth-setup.md)
- [Tool 1 spec](./docs/tool-1-calendar-purge.md)
- [Implementation plan](./docs/next-steps.md)
- [Tool 2 (future)](./docs/tool-2-calendar-sync.md)

## Docker

```bash
cp .env.example .env
# fill in values
docker compose up --build
```
