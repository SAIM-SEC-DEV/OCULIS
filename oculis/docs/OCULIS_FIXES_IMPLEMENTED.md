# OCULIS — Fixes Implemented

This branch closes the gaps identified in the OCULIS assessment in the requested order.

## Step 1 — SSRF / DNS rebinding

Implemented in `apps/api/oculis_api/engine/safe_url.py`.

- Resolves a hostname once per request/redirect hop.
- Validates every DNS answer returned by the resolver.
- Pins the TCP destination to the validated IP.
- Keeps the original hostname as the HTTP authority and TLS SNI.
- Uses `trust_env=False` so host proxy settings cannot bypass the network boundary.
- Allows only ports `80` and `443`.
- Rejects decimal, hexadecimal, and dotted-octal loopback spellings.
- Explicitly blocks CGNAT `100.64.0.0/10`.
- Explicitly blocks AWS IMDS IPv6 `fd00:ec2::254`.
- Revalidates every redirect before the next connection.

The important invariant is now:

> validated DNS answer == TCP destination

There is no second hostname lookup between validation and connection.

## Step 2 — PostgreSQL + Alembic

Added:

- `apps/api/oculis_api/db/database.py`
- `apps/api/oculis_api/db/models.py`
- `apps/api/alembic/`
- `apps/api/alembic.ini`

Tables:

- `analyses`
- `findings`
- `redirects`

Browser-support tables are also added by the second migration:

- `network_requests`
- `screenshots`

`analyses` now persists status, normalized/final URLs, score, verdict, timestamps, signals, and browser artifact metadata.

The API no longer uses the old process-local `_ANALYSES` dictionary.

## Step 3 — Security test suite

Added:

- `apps/api/tests/test_ssrf_security.py`

Coverage includes:

- loopback
- RFC1918 private ranges
- link-local
- IPv4 metadata
- IPv6 metadata
- CGNAT
- IPv6 loopback/link-local
- encoded IPv4 forms
- disallowed protocols
- embedded credentials
- disallowed ports
- validation of every DNS answer
- public-address false-positive protection
- DNS-rebinding/pinning behavior

The SQLite analysis tests use an isolated in-memory database and do not share state between test cases.

## Step 4 — Redirect chain dashboard

`apps/web/src/pages/Analysis.tsx` now renders:

- hop number
- source URL
- HTTP status
- `Location` target

The existing graphite/cyan console styling is preserved.

## Step 5 — Redis/RQ worker

Added:

- `apps/api/oculis_api/services/queue.py`
- `apps/api/oculis_api/services/analysis_runner.py`
- `apps/api/oculis_api/workers/analyzer.py`
- `apps/api/worker.Dockerfile`

`POST /api/v1/analyses` now:

1. persists the queued analysis in PostgreSQL;
2. enqueues an RQ job;
3. returns the analysis ID immediately.

The worker owns the analysis execution and writes results back to PostgreSQL.

This means API restarts do not discard queued work and analysis execution can scale independently of the API.

## Step 6 — Browser sandbox

Added a separate `apps/sandbox` service.

Security properties:

- Playwright/Chromium runs in a separate container.
- The browser container runs as a non-root `sandbox` user.
- The sandbox is attached only to the dedicated sandbox network, not the PostgreSQL/Redis network.
- Worker-to-sandbox communication happens over the dedicated network.
- Browser requests are intercepted at the Playwright request layer.
- Only GET/HEAD browser requests are permitted.
- Every GET/HEAD request goes through the same SSRF-safe fetch layer before the browser receives the response.
- Redirects are returned to the browser one hop at a time, so every redirected URL is independently validated.
- Screenshot, title, forms, password/email inputs, iframes, script URLs, external links, console errors, and network requests are captured.
- Container-level limits are set in Compose: memory, CPU, and PID limits.
- Screenshot artifacts are stored in a shared Docker volume and exposed by the API.

The dashboard now exposes the captured screenshot and browser/network evidence.

## Verification

API tests executed in the available environment:

`54 passed`

Python source files were also parsed successfully after the final changes.

The environment used for this assessment did not have outbound package-install access, so the pinned dependency set could not be freshly installed there. The final verification should therefore be run in the repository's Docker environment:

```bash
docker compose build
docker compose up -d
docker compose logs -f api worker sandbox
```

Then:

```bash
cd apps/api
ruff check .
pytest -q
```

And:

```bash
cd apps/web
npm ci
npx tsc --noEmit
npm run build
```

For the full stack:

```bash
docker compose up --build
```

The API container automatically runs:

```bash
alembic upgrade head
```

before starting FastAPI.

## Important operational note

The browser sandbox intentionally blocks non-GET/HEAD browser requests. This is a deliberate safety boundary for the current implementation: it prevents a rendered page from submitting arbitrary POST requests into the network.

If OCULIS later needs to model authenticated/session-aware browser behavior, that should be added as a separate security-reviewed capability rather than weakening this boundary.
