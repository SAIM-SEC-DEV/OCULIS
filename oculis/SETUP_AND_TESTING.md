# OCULIS setup and testing guide

This guide runs the included first release locally. It covers the API, web
console, unit tests, and a safe manual smoke test.

## Prerequisites

- Python 3.12 or newer
- Node.js 22 or newer
- npm

Docker is optional. The current release uses an in-memory analysis store, so
Postgres and Redis are not required to run the API.

## 1. Configure the project

From the repository root:

```bash
cp .env.example .env
```

The defaults are safe for local development. The important limits are:

- `ANALYSIS_TIMEOUT_SECONDS` — request timeout budget.
- `MAX_REDIRECTS` — maximum redirect hops.
- `MAX_RESPONSE_BYTES` — maximum response body kept for inspection.
- `CORS_ALLOW_ORIGINS` — browser origins allowed to call the API.

Do not put production secrets in `.env` or commit that file.

## 2. Start the API

In terminal 1:

```bash
cd apps/api
python3 -m pip install -r requirements.txt
uvicorn oculis_api.main:app --reload --port 8000
```

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Interactive API documentation is at http://localhost:8000/docs.

## 3. Start the web console

In terminal 2:

```bash
cd apps/web
npm ci
npm run dev
```

Open http://localhost:5173 and submit:

```text
https://example.com
```

The analysis page polls until the API returns a terminal state. For a
deliberately blocked safety test, submit one of these:

```text
http://127.0.0.1:8000
http://localhost:8000
http://169.254.169.254/latest/meta-data
ftp://example.com/file
```

The API creates a record, but the safe boundary blocks the target before any
outbound request is made.

## 4. Run automated tests

Backend unit and API tests:

```bash
cd apps/api
pytest -q
```

Static quality checks:

```bash
ruff check .
```

Frontend checks:

```bash
cd ../web
npx tsc --noEmit
npm run build
```

The production frontend bundle is written to `apps/web/dist/`.

## 5. API smoke test without the frontend

Create an analysis:

```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Copy the returned `id`, then query it:

```bash
curl http://localhost:8000/api/v1/analyses/<id>
```

The response includes the submitted and normalized URLs, status, risk score,
verdict, findings, redirect hops, and infrastructure signals when the
inspection completes.

## Security notes

The backend never trusts a redirect destination. It normalizes and resolves
each hop before requesting it, and rejects non-public address ranges. Response
bodies are bounded and are inspected as bytes; they are not executed as local
browser content.

This is not yet a production multi-user service: results are in memory,
there is no authentication, and the optional browser sandbox/queue/database
milestones are not included in this release. Do not expose this development
server directly to the public internet.