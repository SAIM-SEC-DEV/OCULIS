from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from oculis_api.core.config import settings
from oculis_api.db import Analysis as AnalysisDB
from oculis_api.db import Finding as FindingDB
from oculis_api.db import NetworkRequest as NetworkRequestDB
from oculis_api.db import Redirect as RedirectDB
from oculis_api.db import Screenshot as ScreenshotDB
from oculis_api.db import database
from oculis_api.engine.analyzer import analyze, inspect_url
from oculis_api.engine.safe_url import SafeFetchError, URLSafetyError, normalize_url
from oculis_api.schemas import AnalysisStatus, Finding, RedirectHop


def _get_analysis(db: Session, analysis_id: str) -> AnalysisDB | None:
    return db.scalar(
        select(AnalysisDB)
        .options(selectinload(AnalysisDB.findings), selectinload(AnalysisDB.redirects))
        .where(AnalysisDB.id == analysis_id)
    )


def _replace_children(
    db: Session, analysis: AnalysisDB, findings: list[Finding], redirects: list[RedirectHop]
) -> None:
    analysis.findings.clear()
    analysis.redirects.clear()
    db.flush()
    analysis.findings.extend(
        FindingDB(
            finding_id=finding.id,
            category=finding.category,
            severity=finding.severity,
            title=finding.title,
            detail=finding.detail,
            evidence=finding.evidence,
        )
        for finding in findings
    )
    analysis.redirects.extend(
        RedirectDB(
            hop=redirect.hop,
            url=redirect.url,
            status_code=redirect.status_code,
            location=redirect.location,
        )
        for redirect in redirects
    )


async def _render_in_sandbox(url: str) -> dict:
    async with httpx.AsyncClient(timeout=70, trust_env=False) as client:
        response = await client.post(
            f"{settings.sandbox_url.rstrip('/')}/render",
            json={"url": url, "timeout_seconds": min(settings.analysis_timeout_seconds, 60)},
        )
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"[SANDBOX_ERROR] Browser sandbox returned HTTP {response.status_code}."
                + (f" Detail: {detail}" if detail else "")
            )
        return response.json()


def _save(db: Session, analysis_id: str, **changes: object) -> None:
    analysis = _get_analysis(db, analysis_id)
    if analysis is None:
        raise RuntimeError(f"analysis {analysis_id} not found")
    for key, value in changes.items():
        setattr(analysis, key, value)
    db.commit()


async def run_analysis(analysis_id: str) -> None:
    db = database.SessionLocal()
    try:
        analysis = _get_analysis(db, analysis_id)
        if analysis is None:
            return
        _save(db, analysis_id, status=AnalysisStatus.VALIDATING.value)
        normalized = normalize_url(analysis.submitted_url)
        static_findings = inspect_url(normalized)
        _save(
            db, analysis_id, status=AnalysisStatus.STATIC_ANALYSIS.value, normalized_url=normalized
        )
        analysis = _get_analysis(db, analysis_id)
        assert analysis is not None
        _replace_children(db, analysis, static_findings, [])
        db.commit()

        _save(db, analysis_id, status=AnalysisStatus.NETWORK_ANALYSIS.value)
        result = await analyze(
            normalized,
            max_redirects=settings.max_redirects,
            max_bytes=settings.max_response_bytes,
            timeout_seconds=settings.analysis_timeout_seconds,
        )
        _save(db, analysis_id, status=AnalysisStatus.BROWSER_ANALYSIS.value)
        browser_result: dict = {}
        try:
            browser_result = await _render_in_sandbox(result.signals.final_url)
        except Exception as exc:  # noqa: BLE001
            browser_result = {"error": str(exc)}

        _save(db, analysis_id, status=AnalysisStatus.THREAT_ANALYSIS.value)
        await asyncio.sleep(0)

        analysis = _get_analysis(db, analysis_id)
        assert analysis is not None
        _replace_children(db, analysis, result.findings, result.redirects)
        analysis.status = AnalysisStatus.SCORING.value
        analysis.normalized_url = result.normalized_url
        analysis.final_url = result.signals.final_url
        analysis.signals = result.signals.model_dump(mode="json")
        analysis.browser_data = {
            "error": browser_result.get("error"),
            **browser_result.get("page", {}),
            "console_errors": browser_result.get("console_errors", []),
        }
        analysis.screenshot_path = browser_result.get("screenshot_path")
        analysis.screenshot_mime = browser_result.get("screenshot_mime")
        analysis.network_requests.clear()
        analysis.screenshots.clear()
        db.flush()
        analysis.network_requests.extend(
            NetworkRequestDB(
                url=item.get("url", ""),
                method=item.get("method", "GET"),
                resource_type=item.get("resource_type"),
                blocked=bool(item.get("blocked", False)),
                reason=item.get("reason"),
            )
            for item in browser_result.get("network_requests", [])
        )
        if analysis.screenshot_path and analysis.screenshot_mime:
            analysis.screenshots.append(
                ScreenshotDB(path=analysis.screenshot_path, mime_type=analysis.screenshot_mime)
            )
        db.commit()
        await asyncio.sleep(0)

        analysis = _get_analysis(db, analysis_id)
        assert analysis is not None
        analysis.status = AnalysisStatus.COMPLETED.value
        analysis.risk_score = result.risk_score
        analysis.verdict = result.verdict
        analysis.completed_at = datetime.now(UTC)
        db.commit()
    except URLSafetyError as exc:
        _save(
            db,
            analysis_id,
            status=AnalysisStatus.BLOCKED.value,
            error=str(exc),
            completed_at=datetime.now(UTC),
        )
    except SafeFetchError as exc:
        _save(
            db,
            analysis_id,
            status=AnalysisStatus.FAILED.value,
            error=str(exc),
            completed_at=datetime.now(UTC),
        )
    except TimeoutError:
        _save(
            db,
            analysis_id,
            status=AnalysisStatus.TIMEOUT.value,
            error="[ANALYSIS_TIMEOUT] The analysis exceeded OCULIS's safe execution window.",
            completed_at=datetime.now(UTC),
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        detail = str(exc) or repr(exc) or exc.__class__.__name__
        _save(
            db,
            analysis_id,
            status=AnalysisStatus.FAILED.value,
            error=f"[UNKNOWN_ERROR] OCULIS could not complete the inspection. Detail: {detail}",
            completed_at=datetime.now(UTC),
        )
    finally:
        db.close()


def run_analysis_job(analysis_id: str) -> None:
    asyncio.run(run_analysis(analysis_id))
