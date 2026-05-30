# Canvas OAuth setup

OAuth lets any instructor sign in with their own Canvas account — no shared access token in `.env`.

## 1. Create a Canvas Developer Key

You need **account-level admin** access (or ask your Canvas / EdTech team).

1. Log in to Canvas as an admin.
2. Go to **Admin** → your root account → **Developer Keys**.
3. Click **+ Developer Key** → **API Key**.
4. Configure:

| Field | Value |
|-------|--------|
| **Key name** | FBF Calendar Purger |
| **Owner email** | Your contact email |
| **Redirect URIs** | `http://localhost:3000/api/auth/callback` (add production URL later) |
| **Enforce scopes** | On (recommended) |

5. Enable these **scopes**:

- `url:GET|/api/v1/courses`
- `url:GET|/api/v1/calendar_events`
- `url:DELETE|/api/v1/calendar_events/:id`
- `url:GET|/api/v1/users/self/profile`

6. Save and **turn the key ON** (Developer Keys list → State → On).
7. Copy the **Client ID** and **Client Secret** (click Show Key).

### UW Madison (`canvas.wisc.edu`)

Same steps at: **Account → UW-Madison → Developer Keys** (requires sub-account or root admin).

If you do not have admin access, send this doc to your Canvas support contact and ask them to create the key with the redirect URI and scopes above.

## 2. Configure `.env`

At the project root, edit `.env`:

```bash
CANVAS_BASE_URL=https://canvas.wisc.edu
CANVAS_CLIENT_ID=paste_client_id_here
CANVAS_CLIENT_SECRET=paste_client_secret_here
CANVAS_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback

DEV_MODE=false

# Remove or leave empty — not used when OAuth is enabled:
# CANVAS_ACCESS_TOKEN=
```

Generate a random session secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set `SESSION_SECRET=` to that value.

## 3. Restart servers

```bash
# Terminal 1
cd backend && source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

## 4. Test sign-in

1. Open http://localhost:3000
2. Click **Sign in with Canvas**
3. You should be redirected to `canvas.wisc.edu` to approve access
4. After approving, you return to the app with **your real Canvas name** (not “Dev User”)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Redirect URI mismatch | Redirect URI in Developer Key must **exactly** match `CANVAS_OAUTH_REDIRECT_URI` |
| Invalid client | Check Client ID / Secret; key must be **ON** |
| 501 on sign-in | `CANVAS_CLIENT_ID` or `CANVAS_CLIENT_SECRET` missing in `.env` |
| Still says “Dev User” | `DEV_MODE=true` with token set bypasses OAuth — set `DEV_MODE=false` |
| Empty course list | User must be a **teacher** in at least one active course |

## Production

Add your production callback URL to the Developer Key, e.g.:

```text
https://your-app.example.edu/api/auth/callback
```

Update `.env`:

```bash
FRONTEND_URL=https://your-app.example.edu
CANVAS_OAUTH_REDIRECT_URI=https://your-app.example.edu/api/auth/callback
```

Use HTTPS and a strong `SESSION_SECRET`.
