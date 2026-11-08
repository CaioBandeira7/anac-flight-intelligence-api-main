# Deployment guide

Two services: a read-only **API** (FastAPI, Python 3.12) and the **dashboard** (Next.js 16). Nothing has been published: no public URL exists yet, and this guide does not assume one. Replace `https://api.example` and `https://app.example` with the addresses your host gives you.

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

Without a key, the analyst reports "not configured" and every other feature works. With a key, every question is a call to the provider, which may have usage limits or costs.

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
| Docker images | `docker build` for both Dockerfiles | **Not run:** the Docker daemon was not running on the build machine |
| Secrets | No key in the repository; `.env` and `web/.env.local` ignored; the Dockerfiles' allowlists exclude `.env` | ✅ scanned tracked and untracked files |
