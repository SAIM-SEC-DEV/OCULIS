#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
API_SAFE="$ROOT/apps/api/oculis_api/engine/safe_url.py"
SANDBOX_SAFE="$ROOT/apps/sandbox/safe_url.py"
RUNNER="$ROOT/apps/api/oculis_api/services/analysis_runner.py"
WEB="$ROOT/apps/web/src/pages/Analysis.tsx"

for f in "$API_SAFE" "$SANDBOX_SAFE" "$RUNNER" "$WEB"; do
  [[ -f "$f" ]] || { echo "Missing expected file: $f" >&2; exit 1; }
done

stamp="$(date +%Y%m%d-%H%M%S)"
cp "$API_SAFE" "$API_SAFE.bak.$stamp"
cp "$SANDBOX_SAFE" "$SANDBOX_SAFE.bak.$stamp"
cp "$RUNNER" "$RUNNER.bak.$stamp"
cp "$WEB" "$WEB.bak.$stamp"

python3 - <<'PY'
from pathlib import Path

# --- shared safe fetch errors: API + sandbox copies ---
for filename in [
    Path("apps/api/oculis_api/engine/safe_url.py"),
    Path("apps/sandbox/safe_url.py"),
]:
    text = filename.read_text()

    if "class SafeFetchError" not in text:
        marker = 'class URLSafetyError(ValueError):\n    """Raised when a URL must not be fetched by the analyzer."""\n'
        insert = '''class URLSafetyError(ValueError):\n    """Raised when a URL must not be fetched by the analyzer."""\n\n\nclass SafeFetchError(RuntimeError):\n    """Operational fetch failure with a stable user-facing classification."""\n\n    def __init__(self, code: str, message: str, detail: str | None = None) -> None:\n        self.code = code\n        self.message = message\n        self.detail = detail\n        suffix = f" Detail: {detail}" if detail else ""\n        super().__init__(f"[{code}] {message}{suffix}")\n'''
        if marker not in text:
            raise SystemExit(f"Could not find URLSafetyError marker in {filename}")
        text = text.replace(marker, insert, 1)

    old = '''                            raise URLSafetyError(\n                                f"response exceeded the {max_bytes:,} byte safety limit"\n                            )\n'''
    new = '''                            raise SafeFetchError(\n                                "RESPONSE_TOO_LARGE",\n                                f"The response exceeded OCULIS's {max_bytes:,}-byte inspection limit.",\n                                "The server responded, but the content was too large to inspect safely.",\n                            )\n'''
    if old in text:
        text = text.replace(old, new, 1)

    old = '''        except URLSafetyError:\n            raise\n        except httpx.HTTPError as exc:\n            raise RuntimeError(f"safe request failed: {exc}") from exc\n'''
    new = '''        except URLSafetyError:\n            raise\n        except SafeFetchError:\n            raise\n        except httpx.ConnectTimeout as exc:\n            scheme = parsed.scheme.upper()\n            port = parsed.port or (443 if parsed.scheme == "https" else 80)\n            raise SafeFetchError(\n                "CONNECTION_TIMEOUT",\n                f"The {scheme} connection to {hostname}:{port} timed out.",\n                "The hostname resolved, but the target did not establish a connection before the timeout.",\n            ) from exc\n        except httpx.ConnectError as exc:\n            scheme = parsed.scheme.upper()\n            port = parsed.port or (443 if parsed.scheme == "https" else 80)\n            detail = str(exc) or exc.__class__.__name__\n            raise SafeFetchError(\n                "CONNECTION_FAILED",\n                f"OCULIS could not establish a {scheme} connection to {hostname}:{port}.",\n                detail,\n            ) from exc\n        except httpx.ConnectError as exc:\n            detail = str(exc) or exc.__class__.__name__\n            raise SafeFetchError(\n                "CONNECTION_FAILED",\n                f"OCULIS could not establish a connection to {hostname}.",\n                detail,\n            ) from exc\n        except httpx.RemoteProtocolError as exc:\n            detail = str(exc) or exc.__class__.__name__\n            raise SafeFetchError(\n                "REMOTE_PROTOCOL_ERROR",\n                f"The target closed or violated the HTTP connection while OCULIS was fetching {hostname}.",\n                detail,\n            ) from exc\n        except httpx.ReadTimeout as exc:\n            raise SafeFetchError(\n                "RESPONSE_TIMEOUT",\n                f"The target did not finish sending its response within the safe timeout.",\n                f"{hostname}: {exc.__class__.__name__}",\n            ) from exc\n        except httpx.HTTPError as exc:\n            detail = str(exc) or repr(exc) or exc.__class__.__name__\n            raise SafeFetchError(\n                "HTTP_FETCH_ERROR",\n                f"OCULIS could not safely fetch the target over HTTP.",\n                detail,\n            ) from exc\n'''
    if old not in text:
        # support current manually modified exception block; do a more local replacement
        marker = '        except URLSafetyError:\n            raise\n'
        if marker not in text:
            raise SystemExit(f"Could not locate fetch exception block in {filename}")
        start = text.index(marker)
        end = text.index('        finally:', start)
        replacement = new + '\n'
        text = text[:start] + replacement + text[end:]
    else:
        text = text.replace(old, new, 1)

    # Remove the accidentally duplicated ConnectError handler if the replacement was applied twice.
    duplicate = '''        except httpx.ConnectError as exc:\n            detail = str(exc) or exc.__class__.__name__\n            raise SafeFetchError(\n                "CONNECTION_FAILED",\n                f"OCULIS could not establish a connection to {hostname}.",\n                detail,\n            ) from exc\n'''
    # Keep the first richer ConnectError handler only.
    if text.count('except httpx.ConnectError as exc:') > 1 and duplicate in text:
        text = text.replace(duplicate, '', 1)

    filename.write_text(text)

# --- runner: preserve meaningful failure reason ---
p = Path("apps/api/oculis_api/services/analysis_runner.py")
text = p.read_text()
text = text.replace(
    'from oculis_api.engine.safe_url import URLSafetyError, normalize_url\n',
    'from oculis_api.engine.safe_url import SafeFetchError, URLSafetyError, normalize_url\n',
)
old = '''    except URLSafetyError as exc:\n        _save(db, analysis_id, status=AnalysisStatus.BLOCKED.value, error=str(exc), completed_at=datetime.now(UTC))\n    except TimeoutError:\n        _save(db, analysis_id, status=AnalysisStatus.TIMEOUT.value, error="analysis timed out", completed_at=datetime.now(UTC))\n    except Exception as exc:  # noqa: BLE001\n        db.rollback()\n        _save(db, analysis_id, status=AnalysisStatus.FAILED.value, error=str(exc), completed_at=datetime.now(UTC))\n'''
new = '''    except URLSafetyError as exc:\n        _save(\n            db,\n            analysis_id,\n            status=AnalysisStatus.BLOCKED.value,\n            error=str(exc),\n            completed_at=datetime.now(UTC),\n        )\n    except SafeFetchError as exc:\n        _save(\n            db,\n            analysis_id,\n            status=AnalysisStatus.FAILED.value,\n            error=str(exc),\n            completed_at=datetime.now(UTC),\n        )\n    except TimeoutError:\n        _save(\n            db,\n            analysis_id,\n            status=AnalysisStatus.TIMEOUT.value,\n            error="[ANALYSIS_TIMEOUT] The analysis exceeded OCULIS's safe execution window.",\n            completed_at=datetime.now(UTC),\n        )\n    except Exception as exc:  # noqa: BLE001\n        db.rollback()\n        detail = str(exc) or repr(exc) or exc.__class__.__name__\n        _save(\n            db,\n            analysis_id,\n            status=AnalysisStatus.FAILED.value,\n            error=f"[UNKNOWN_ERROR] OCULIS could not complete the inspection. Detail: {detail}",\n            completed_at=datetime.now(UTC),\n        )\n'''
if old not in text:
    raise SystemExit("Could not locate runner terminal exception block")
text = text.replace(old, new, 1)

# Sandbox HTTP error becomes useful to Browser Evidence as well.
old = '''        response.raise_for_status()\n        return response.json()\n'''
new = '''        if response.is_error:\n            detail = response.text.strip()\n            raise RuntimeError(\n                f"[SANDBOX_ERROR] Browser sandbox returned HTTP {response.status_code}."\n                + (f" Detail: {detail}" if detail else "")\n            )\n        return response.json()\n'''
if old not in text:
    raise SystemExit("Could not locate sandbox raise_for_status block")
text = text.replace(old, new, 1)
p.write_text(text)

# --- frontend: classify error codes into concise human-facing titles ---
p = Path("apps/web/src/pages/Analysis.tsx")
text = p.read_text()
marker = "function pretty(value: unknown) { return value === null || value === undefined || value === '' ? '—' : String(value) }\n"
insert = '''function pretty(value: unknown) { return value === null || value === undefined || value === '' ? '—' : String(value) }\n\nfunction errorPresentation(error?: string | null) {\n  const raw = error || 'The remote analyzer could not complete this inspection.'\n  const match = raw.match(/^\\[([^\\]]+)\\]\\s*(.*)$/s)\n  const code = match?.[1] || 'UNKNOWN_ERROR'\n  const detail = match?.[2] || raw\n  const titles: Record<string, string> = {\n    RESPONSE_TOO_LARGE: 'Response too large',\n    CONNECTION_TIMEOUT: 'Connection timed out',\n    CONNECTION_FAILED: 'Connection failed',\n    REMOTE_PROTOCOL_ERROR: 'Remote protocol error',\n    RESPONSE_TIMEOUT: 'Response timed out',\n    HTTP_FETCH_ERROR: 'HTTP fetch failed',\n    SANDBOX_ERROR: 'Browser sandbox failed',\n    ANALYSIS_TIMEOUT: 'Analysis timed out',\n    UNKNOWN_ERROR: 'Inspection failed',\n  }\n  const title = titles[code] || 'Inspection failed safely'\n  const cleaned = detail.replace(/^Detail:\\s*/i, '')\n  return { title, detail: cleaned, code }\n}\n'''
if marker not in text:
    raise SystemExit("Could not find pretty helper in Analysis.tsx")
text = text.replace(marker, insert, 1)
old = '''    {terminal && data.status === 'failed' && <StateCard title="Inspection failed safely" detail={data.error || 'The remote analyzer could not complete this inspection.'} tone="danger" />}\n    {terminal && data.status === 'timeout' && <StateCard title="Inspection timed out" detail={data.error || 'The target did not respond within the safe analysis window.'} tone="warning" />}\n'''
new = '''    {terminal && data.status === 'failed' && (() => { const error = errorPresentation(data.error); return <StateCard title={error.title} detail={error.detail} tone="danger" code={error.code} /> })()}\n    {terminal && data.status === 'timeout' && <StateCard title="Inspection timed out" detail={data.error || 'The target did not respond within the safe analysis window.'} tone="warning" />}\n'''
if old not in text:
    raise SystemExit("Could not find failed/timeout state cards in Analysis.tsx")
text = text.replace(old, new, 1)
old = '''function StateCard({ title, detail, tone }: { title: string; detail: string; tone: 'warning' | 'danger' }) { return <div className={`border p-6 ${tone === 'danger' ? 'border-risk-critical/40 bg-risk-critical/[.04]' : 'border-risk-suspicious/40 bg-risk-suspicious/[.04]'}`}><p className={`font-mono text-xs uppercase tracking-widest ${tone === 'danger' ? 'text-risk-critical' : 'text-risk-suspicious'}`}>{title}</p><p className="mt-3 max-w-2xl text-sm leading-6 text-graphite-300">{detail}</p></div> }\n'''
new = '''function StateCard({ title, detail, tone, code }: { title: string; detail: string; tone: 'warning' | 'danger'; code?: string }) { return <div className={`border p-6 ${tone === 'danger' ? 'border-risk-critical/40 bg-risk-critical/[.04]' : 'border-risk-suspicious/40 bg-risk-suspicious/[.04]'}`}><div className="flex flex-wrap items-center justify-between gap-3"><p className={`font-mono text-xs uppercase tracking-widest ${tone === 'danger' ? 'text-risk-critical' : 'text-risk-suspicious'}`}>{title}</p>{code && <span className="border border-graphite-700 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-graphite-500">{code}</span>}</div><p className="mt-3 max-w-2xl text-sm leading-6 text-graphite-300">{detail}</p></div> }\n'''
if old not in text:
    raise SystemExit("Could not find StateCard function")
text = text.replace(old, new, 1)
p.write_text(text)

print("OCULIS error model applied.")
PY

python3 -m py_compile "$API_SAFE"
python3 -m py_compile "$SANDBOX_SAFE"
python3 -m py_compile "$RUNNER"

TEST_FILE="$ROOT/apps/api/tests/test_safe_fetch_errors.py"
cat > "$TEST_FILE" <<'PYTEST'
from oculis_api.engine.safe_url import SafeFetchError


def test_safe_fetch_error_has_stable_code_and_message() -> None:
    error = SafeFetchError(
        "CONNECTION_TIMEOUT",
        "The HTTPS connection to example.com:443 timed out.",
        "The hostname resolved, but the target did not establish a connection before the timeout.",
    )

    assert error.code == "CONNECTION_TIMEOUT"
    assert "CONNECTION_TIMEOUT" in str(error)
    assert "timed out" in str(error)


def test_safe_fetch_error_without_detail_is_still_descriptive() -> None:
    error = SafeFetchError("CONNECTION_FAILED", "The connection failed.")
    assert str(error) == "[CONNECTION_FAILED] The connection failed."
PYTEST

echo "\nDone. Review git diff, then rebuild api/worker/sandbox/web."
