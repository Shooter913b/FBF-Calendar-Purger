# Deploying the backend on Render

Render’s default filesystem is **ephemeral**: when a service sleeps, restarts, or redeploys, files under `/app` are wiped. The visitor counter (`data/visitors.json`) must live on **persistent storage**.

Choose **one** of the options below (no SQL database required).

## Option A — Render persistent disk (recommended on Starter+)

1. Open your web service in the [Render Dashboard](https://dashboard.render.com).
2. **Disks → Add disk**
   - **Mount path:** `/app/data`
   - **Size:** 1 GB is plenty
3. **Environment →** add:
   ```text
   VISITOR_STORE_PATH=/app/data/visitors.json
   ```
4. Redeploy.

Or deploy from the repo’s `render.yaml`, which configures the disk automatically (requires a **Starter** plan or higher — free instances cannot attach disks).

Only files written under the mount path survive sleep and deploys. See [Render persistent disks](https://render.com/docs/disks).

## Option B — Upstash Redis (free tier, no Render disk)

Works when the service sleeps on Render’s **free** plan:

1. Create a free database at [Upstash Console](https://console.upstash.com/) → **Redis**.
2. Copy the **REST URL** and **REST token**.
3. In Render **Environment**, set:
   ```text
   UPSTASH_REDIS_REST_URL=https://your-db.upstash.io
   UPSTASH_REDIS_REST_TOKEN=your-token
   ```
4. Redeploy.

The app stores anonymous visitor UUIDs in a Redis set (`fbf:visitor_ids`). No names, emails, or Canvas IDs.

If both Upstash variables are set, they take priority over the file store.

## Verify

1. Load the login page — note the lifetime user count.
2. Trigger a sleep/restart (or wait for spin-down on free tier).
3. Reload — the count should **not** reset, and returning browsers should not inflate the total.
