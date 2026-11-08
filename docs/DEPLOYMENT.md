# Deployment guide

Two services: a read-only **API** (FastAPI, Python 3.12) and the **dashboard** (Next.js 16). Below, `https://api.example` and `https://app.example` stand for the addresses your host gives you.

## Current deployment

| Service | Host | Address | Source |
|---|---|---|---|
| API | Render, free web service `anac-flight-intelligence-api:v2`, one instance | `https://anac-flight-intelligence-api-v2.onrender.com` | Docker Hub image `xuxutinha777/anac-flight-intelligence-api:v3`, built locally with the data |
| Dashboard | Vercel, root directory `web` | `https://anac-flight-intelligence-api-main.vercel.app` | Git, `NEXT_PUBLIC_DATA_SOURCE=api`, `NEXT_PUBLIC_API_URL` set to the API |

Render environment: `ANAC_API_HOST`, `ANAC_API_PORT`, `ANAC_CORS_ORIGINS` (the Vercel address), `GROQ_API_KEY` (secret) and `ANAC_CLIENT_IP_HEADER=cf-connecting-ip`. The analyst limits use their defaults.

### Releasing a new API image

```powershell
.\deploy\publish-api.ps1 -Tag v4      # tests, lint, types, docker build and push
```

Then, in Render: **Settings → Image URL** → `docker.io/xuxutinha777/anac-flight-intelligence-api:v4` → **Save** and deploy. Environment variables are kept. To roll back, set the previous tag and deploy again.

## What each service needs

| | API | Dashboard |
|---|---|---|
| Code | `src/`, `pyproject.toml`, `requirements-lock.txt` | `web/` |
| Data | `data/serving/v1` (~0.1 MB) and `data/analytics/v1` (~29 MB). Built locally, **not in Git** | None: it calls the API from the browser |
| Static ML and analyst files | — | `web/public/ml/*`, `web/public/analyst/cases.json` (in Git) |
| Port | `ANAC_API_PORT` (default 8000) | `PORT` (default 3000) |
| Health | `GET /health` | `GET /dashboard` returns 200 |

Because the data is not in Git, a host that builds from the repository cannot build the API. Either build the image locally (the data is copied in), or mount the two data folders as a volume and set `ANAC_SERVING_DIR` and `ANAC_ANALYTICS_DIR`.

## Environment variables

### API

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANAC_API_HOST` | in a container | `127.0.0.1` (`0.0.0.0` in the image) | Bind address |
| `ANAC_API_PORT` | if the host assigns one | `8000` | Port. On hosts that give `$PORT`, set `ANAC_API_PORT=$PORT` |
| `ANAC_CORS_ORIGINS` | **yes in production** | `http://localhost:3000` | Comma-separated origins allowed to call the API, such as `https://app.example`. Others get no CORS header |
| `ANAC_SERVING_DIR` | no | `data/serving/v1` | Exported payloads |
| `ANAC_ANALYTICS_DIR` | no | `data/analytics/v1` | Analytical tables |
| `GROQ_API_KEY` | no | — | Enables the analyst. **Secret:** set it in the host's secret store, never in the image, the repository or a `NEXT_PUBLIC_*` variable |
| `ANAC_LLM_PROVIDER`, `ANAC_LLM_BASE_URL`, `ANAC_LLM_MODEL`, `ANAC_LLM_API_KEY` | no | Groq, `openai/gpt-oss-120b` | Any OpenAI-compatible provider |
| `ANAC_ANALYST_CLIENT_LIMIT` | no | `10` | Questions one client may ask per window. `0` turns it off |
| `ANAC_ANALYST_CLIENT_WINDOW_SECONDS` | no | `3600` | Length of that sliding window |
| `ANAC_ANALYST_DAILY_LIMIT` | no | `200` | Questions the whole server answers per UTC day. `0` turns it off |
| `ANAC_CLIENT_IP_HEADER` | **yes on Render** | empty (TCP peer) | Header holding the real client address. Set `cf-connecting-ip` on Render; see below |

Without a key, the analyst reports "not configured" and every other feature works. With a key, every question is a call to the provider, which may have usage limits or costs.

### Analyst abuse limits

`POST /v2/analyst/chat` is public and every accepted question can become paid calls to the provider (up to 4 tool rounds, 900 output tokens each). Besides the per-request bounds (question ≤ 500 characters, history ≤ 6 turns, 45 s timeout), two limits apply before the provider is contacted:

- **Per client:** `ANAC_ANALYST_CLIENT_LIMIT` questions per sliding `ANAC_ANALYST_CLIENT_WINDOW_SECONDS`.
- **Global:** `ANAC_ANALYST_DAILY_LIMIT` questions per UTC day, shared by everyone. It caps the worst-case daily cost even if many addresses are used.

Past a limit the answer is `429` with `Retry-After` (seconds) and `detail = {"code": "rate_limited", "scope": "client" | "daily", "message": …}`. The provider is not called. A refused question consumes nothing, so one client cannot burn the daily quota by retrying; invalid requests (422) are not counted. Other endpoints are not limited.

**Client address.** `X-Forwarded-For` is never read: Render's proxy appends to whatever the client sent, so a client can choose its first entry. Without `ANAC_CLIENT_IP_HEADER`, the API counts the TCP peer, which on Render is the platform's proxy: every visitor then shares one bucket (safe, but strict). On Render, set `ANAC_CLIENT_IP_HEADER=cf-connecting-ip`: Render sits behind Cloudflare, which overwrites that header with the address it saw. The value is used only if it parses as an IP address. If the service ever runs behind a host without such a header, leave it empty.

**Limitations of the in-memory counters:**

| Situation | Effect | Mitigation |
|---|---|---|
| Restart, redeploy, or a free instance spinning down | All counters reset to zero, so a client and the daily quota start over | Low daily limit; the provider's own quota still applies (its 429 is passed on) |
| Several instances or workers | Each process counts separately: real limits are N × the configured ones | Keep one instance and one worker (the image runs one), or move the counters to a shared store such as Redis |
| Many addresses (botnets, IPv6 ranges) | The per-client limit is evaded | The global daily limit still caps the total |
| Clients behind one NAT | They share a bucket | Raise `ANAC_ANALYST_CLIENT_LIMIT` if needed |

For a stronger guarantee, also set a spending or usage limit in the provider's console: it is the only cap that survives restarts and instances.

### Dashboard

These are read **at build time** and are public: they end up in the browser bundle, so never put a secret in them.

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_DATA_SOURCE` | `api` (real data) or `mock` (demo data, labelled DEMO) |
| `NEXT_PUBLIC_API_URL` | The API's public address, such as `https://api.example` |

## Option A: dashboard on Vercel, API on a container host

1. **Build and push the API image** (from the repository root, with the data built locally):

   ```powershell
   docker build -f deploy/api/Dockerfile -t <registry>/anac-fi-api:v2 .
   docker push <registry>/anac-fi-api:v2
   ```

2. **Run it on the container host** (Railway, Render, Fly.io, Azure Container Apps, …):
   - set `ANAC_CORS_ORIGINS` to the dashboard's address, and `GROQ_API_KEY` as a secret if wanted;
   - map the host's port with `ANAC_API_PORT`;
   - use `/health` as the health check.
3. **Deploy the dashboard on Vercel:**
   - import the repository, with root directory `web`;
   - set `NEXT_PUBLIC_DATA_SOURCE=api` and `NEXT_PUBLIC_API_URL=https://api.example`;
   - deploy. Framework detection handles the build (`npm run build`).
4. Add the final dashboard address to `ANAC_CORS_ORIGINS` and restart the API.

## Option B: one host with Docker Compose

```powershell
docker compose -f deploy/docker-compose.yml up --build
```

This serves the API on port 8000 and the dashboard on port 3000. For a public host, change `ANAC_CORS_ORIGINS` and the `NEXT_PUBLIC_API_URL` build argument to the public addresses first.

## Option C: without Docker

```powershell
$env:ANAC_API_HOST="0.0.0.0"; $env:ANAC_CORS_ORIGINS="https://app.example"; .venv\Scripts\anac-api
cd web; $env:NEXT_PUBLIC_DATA_SOURCE="api"; $env:NEXT_PUBLIC_API_URL="https://api.example"; npm.cmd ci; npm.cmd run build; npm.cmd run start
```

## Updating

| Change | Action |
|---|---|
| Code | Rebuild and redeploy the affected service |
| Data (`anac-analytics build`, payload export) | Rebuild the API image, or replace the mounted folders, then restart |
| ML results or report (`research/ml-showcase`) | Run `analysis.py` and `build_pdf.py`, then redeploy the dashboard |
| Analyst demo cases (`research/analyst-demo`) | Run `build_cases.py`, then redeploy the dashboard |
| API address | Rebuild the dashboard: `NEXT_PUBLIC_API_URL` is fixed at build time |

## Validation checklist

Run after every deployment. The first five rows were verified locally, with `next start` against the API on a separate port and CORS restricted to the dashboard's origin. The last two need a real host.

| Check | How | Local result |
|---|---|---|
| API health | `curl https://api.example/health` returns 200 | ✅ 200 |
| CORS | A request with `Origin: https://app.example` gets `access-control-allow-origin`; another origin gets none | ✅ allowed origin echoed, foreign origin refused |
| Pages | `/dashboard`, `/airports`, `/routes`, `/airlines`, `/ml-studio`, `/analyst`, `/methodology` return 200 and render data | ✅ all 200, no console errors in DAY and NIGHT, desktop and mobile |
| Static files | `/ml/showcase.json`, `/ml/report.pdf` and `/analyst/cases.json` return 200 | ✅ |
| Failure handling | Stop the API: pages show "Couldn't load this data" with Retry, and ML Studio still renders | ✅ |
| Analyst | Open the chat: it reads `/v2/analyst/config` only. Asking a question calls the provider | Not run live in this round (no model call made) |
| Analyst limits | Ask more than `ANAC_ANALYST_CLIENT_LIMIT` questions: the next answer is 429 with `Retry-After` | ✅ automated (`tests/test_ratelimit.py`) |
| Docker images | `docker build` for both Dockerfiles | **Not run:** the Docker daemon was not running on the build machine |
| Secrets | No key in the repository; `.env` and `web/.env.local` ignored; the Dockerfiles' allowlists exclude `.env` | ✅ scanned tracked and untracked files |
