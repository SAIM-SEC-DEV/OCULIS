# OCULIS

See what's behind the link before you visit it.

OCULIS is a remote URL inspection console for links that make you hesitate.
It validates the target, checks DNS/IP safety, follows redirects with
re-validation, inspects a bounded HTTP response, and returns an explainable
risk score — without opening the link in your browser.

## What is built

- React + TypeScript + Vite inspection console with live lifecycle polling.
- FastAPI analysis API with queued, progress, completed, blocked, failed, and
  timeout states.
- SSRF-safe URL boundary:
  - HTTP and HTTPS only.
  - Embedded credentials rejected.
  - Loopback, private, link-local, multicast, reserved, and unspecified IPs
    rejected.
  - DNS is checked immediately before every request.
  - Every redirect is normalized and validated before the next hop.
  - Response size, redirect count, connection, and total request limits are
    bounded.
- Explainable heuristics for punycode, suspicious TLDs, credential language,
  deceptive delimiters, unusual ports, obfuscated paths, password forms,
  page titles, redirects, and HTTP errors.
- Security-focused backend tests covering prohibited protocols, metadata
  addresses, localhost, credential-bearing URLs, and API lifecycle behavior.

This release intentionally does not claim to provide a browser sandbox,
Playwright capture, Postgres persistence, Redis/RQ workers, or TLS certificate
inspection. Those are the next hardening milestones; the current release
keeps network access behind the tested safe fetch boundary instead of adding
an unsafe placeholder.

## Local development

See [`SETUP_AND_TESTING.md`](SETUP_AND_TESTING.md) for the complete setup and
verification walkthrough.

### Native development

Backend terminal:

```bash
cd apps/api
python3 -m pip install -r requirements.txt
uvicorn oculis_api.main:app --reload --port 8000
```

Frontend terminal:

```bash
cd apps/web
npm ci
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the API
at http://localhost:8000. API docs are available at
http://localhost:8000/docs.

### Docker Compose

The existing Compose file remains available for the Postgres and Redis
services that later milestones will use:

```bash
cp .env.example .env
docker compose up --build
```

The current API does not require a database or Redis to run; analysis records
are held in memory for this release and disappear when the API restarts.

## Repo layout

```
apps/
  web/      React + TypeScript frontend
  api/      FastAPI backend
    oculis_api/engine/
              safe_url.py   network boundary and bounded fetcher
              analyzer.py   explainable URL/response heuristics
workers/    reserved for the future queue worker
engine/     reserved for future analysis modules
sandbox/    reserved for future browser isolation configuration
docs/       product and architecture specification
```

## Testing

```bash
cd apps/api
pytest -q
ruff check .

cd ../web
npx tsc --noEmit
npm run build
```
