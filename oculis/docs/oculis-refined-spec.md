# OCULIS — Refined Spec (Solo Portfolio Build)

**See what's behind the link before you visit it.**

A web platform that takes a suspicious URL, inspects it in an isolated sandbox
(DNS/TLS/HTTP, redirect chain, headless-browser render, DOM/network capture),
scores the risk, and shows you evidence-backed findings — so you never have
to open the link yourself.

This version cuts the original spec down from a ~9-module, multi-quarter
enterprise architecture to something one person can actually ship, demo, and
be proud of — while keeping the parts that make it portfolio-worthy: real
sandbox isolation, real SSRF defenses, and an explainable risk engine instead
of a black-box score.

---

## 1. What changed from the original spec, and why

| Original | Refined | Why |
|---|---|---|
| ~9 analysis modules, ~40 detection rules across 6 categories | 4 modules, ~15-20 rules | You'll ship something real in weeks, not quarters. More rules are cheap to add later once the pipeline works. |
| SSRF hardening = "Phase 7" | SSRF/protocol validation = **Phase 1**, before the browser worker ever makes a network call, even in dev | The moment your worker fetches a user-submitted URL, you're exposed — including on your own laptop. |
| Custom job orchestrator | Redis + RQ (or Celery) | This is a solved problem. Don't design a queue from scratch. |
| DNS + TLS + HTTP as separate modules in MVP | Merged into one "Infra Analyzer" | Fewer moving parts for v1; same output shape, split them later if needed. |
| PDF reports, IOC export, reputation enrichment, browser extension, CLI, multi-tenant auth — all "later" but listed alongside MVP work | Explicitly deferred to a "v2 ideas" backlog, out of the build order entirely | Keeps you from context-switching into infra that doesn't demo anything new. |
| Hardcoded scoring logic implied | Rule weights/confidence live in a config file (YAML/JSON) from day one | Tuning the risk model shouldn't mean redeploying code. |

Everything you designed around **explainability** (evidence per finding,
confidence not certainty, "HTTPS ≠ safe," "brand name in domain ≠
malicious") stays exactly as you had it — that's the best part of the spec
and the thing that'll make this stand out in an interview.

---

## 2. MVP definition (the actual target)

**Done when:** a user pastes a URL, and within ~30-60 seconds sees a
dashboard with a risk score (0-100), a verdict, a list of findings each with
evidence, the redirect chain, a screenshot of the rendered page, and basic
page/network metadata — and at no point did the analysis touch your host
machine's network unrestricted, or allow a request to a private/internal
address.

**In scope for MVP:**
- URL parsing, normalization, structural heuristics, lookalike/homoglyph checks
- SSRF-safe fetch layer (protocol allowlist + DNS/IP validation, re-checked after every redirect)
- Redirect chain capture
- HTTP metadata (status, headers, security headers present/missing)
- One merged "Infra Analyzer" pass: DNS resolution + TLS cert basics + HTTP headers
- Browser sandbox: Playwright/Chromium in a container, screenshot, DOM extraction (forms, login/password fields, external scripts, links), network request log
- Threat rules engine: ~15-20 rules total across URL / infra / redirect / page categories, each with severity + confidence + evidence
- Risk engine: weighted scoring → 0-100 → verdict bucket, config-driven weights
- Dashboard: score, verdict, findings w/ evidence, redirect chain, screenshot, request list
- No auth, short data retention (e.g. 24h), no external threat-intel API dependency

**Explicitly out of scope for MVP** (real, but later):
- TLS/DNS as separate deep-dive modules with their own rule sets
- IOC extraction/export, PDF reports
- Reputation enrichment (VirusTotal, Safe Browsing, AbuseIPDB, WHOIS/RDAP)
- Network relationship graph visualization
- ML classifier layer
- Auth, API keys, organizations, rate limiting by identity
- Browser extension, CLI, SIEM integrations

---

## 3. Simplified architecture

```
 User → Web (React/TS) → API (FastAPI) → Redis queue → Worker
                                                            │
                                          ┌─────────────────┼─────────────────┐
                                          ▼                 ▼                 ▼
                                    URL Engine      Infra Analyzer    Browser Sandbox
                                  (parse/heuristics)  (DNS+TLS+HTTP)   (Playwright/Chromium,
                                          │                 │           containerized, SSRF-safe
                                          └────────┬────────┴──────┐    fetch layer only)
                                                   ▼                ▼
                                            Threat Rules Engine (findings)
                                                   ▼
                                            Risk Engine (score + verdict)
                                                   ▼
                                            Postgres (results) → API → Dashboard
```

Four modules instead of nine. The SSRF-safe fetch layer sits underneath
*both* the Infra Analyzer and the Browser Sandbox — it's shared
infrastructure, not a feature bolted on later.

---

## 4. Revised build order

Security-critical pieces move earlier; nice-to-haves move to a backlog.

1. Repo, devcontainer, Docker Compose skeleton (web, api, postgres, redis)
2. FastAPI health endpoint + React shell, wired together
3. Postgres models + Alembic migrations (Analysis, Finding, NetworkRequest, Redirect, Screenshot)
4. **SSRF-safe fetch layer** — protocol allowlist, DNS/IP validation, re-validated on every redirect hop (build and unit-test this *before* anything calls a real URL)
5. URL parser + structural heuristics + lookalike detection
6. Infra Analyzer (DNS + TLS + HTTP merged pass), using the safe fetch layer
7. Redirect chain capture, using the safe fetch layer
8. RQ/Celery worker wiring: submit → queue → status → result
9. Browser sandbox: Playwright in a container, non-root user, timeouts, resource limits — screenshot + DOM + network capture
10. Threat rules engine (start with ~10 rules across URL/infra/redirect, prove the pipeline, then add page/browser rules)
11. Risk engine: config-driven weights, score, verdict buckets
12. Results API + dashboard (score, verdict, findings, redirect chain, screenshot, requests)
13. Security test pass: SSRF payloads, protocol abuse, redirect-to-internal, resource exhaustion
14. Polish: analysis progress UI, dark security-console styling, error handling for DNS/TLS/browser failures

Steps 4 and 9's isolation work are not deferred — they're prerequisites for step 6/7 and step 9 respectively actually running against the internet, even on your own machine.

---

## 5. Tech stack (unchanged, it was already right-sized)

- **Frontend:** React, TypeScript, Vite, Tailwind, TanStack Query
- **Backend:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, httpx, dnspython, cryptography
- **Browser:** Playwright + Chromium, containerized
- **Queue:** Redis + RQ (simpler than Celery for a solo project; swap later if needed)
- **DB:** PostgreSQL
- **Quality:** pytest, Ruff, mypy, ESLint, Prettier, GitHub Actions

---

## 6. v2 backlog (parked, not forgotten)

Reputation enrichment · IOC extraction/export · PDF reports · network graph
visualization · ML classifier as an additional signal · auth + orgs · CLI ·
browser extension · SIEM integrations · rate limiting by identity.

---

## 7. Suggested immediate next step

Start at step 1-4 of the build order: repo scaffold through the SSRF-safe
fetch layer with tests. That's a self-contained, demo-able unit (you can
show "here's a URL fetcher that refuses to touch 127.0.0.1, 169.254.169.254,
or internal ranges even after three redirects") and it unblocks everything
else.
