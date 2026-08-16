from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from oculis_api.db import Analysis as AnalysisDB
from oculis_api.db import get_db
from oculis_api.schemas import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisResult,
    AnalysisSignals,
    AnalysisStatus,
    BrowserData,
    Finding,
    RedirectHop,
)
from oculis_api.services.queue import enqueue_analysis

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


def _get_analysis(db: Session, analysis_id: str) -> AnalysisDB | None:
    return db.scalar(
        select(AnalysisDB)
        .options(selectinload(AnalysisDB.findings), selectinload(AnalysisDB.redirects))
        .where(AnalysisDB.id == analysis_id)
    )


def _to_result(analysis: AnalysisDB) -> AnalysisResult:
    return AnalysisResult(
        id=analysis.id,
        submitted_url=analysis.submitted_url,
        status=AnalysisStatus(analysis.status),
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        risk_score=analysis.risk_score,
        verdict=analysis.verdict,
        normalized_url=analysis.normalized_url,
        final_url=analysis.final_url,
        findings=[
            Finding(
                id=item.finding_id,
                category=item.category,
                severity=item.severity,
                title=item.title,
                detail=item.detail,
                evidence=item.evidence,
            )
            for item in analysis.findings
        ],
        redirects=[
            RedirectHop(
                hop=item.hop,
                url=item.url,
                status_code=item.status_code,
                location=item.location,
            )
            for item in analysis.redirects
        ],
        signals=AnalysisSignals.model_validate(analysis.signals) if analysis.signals else None,
        error=analysis.error,
        browser=BrowserData.model_validate(analysis.browser_data)
        if analysis.browser_data
        else None,
        screenshot_url=(
            f"/artifacts/{analysis.screenshot_path.rsplit('/', 1)[-1]}"
            if analysis.screenshot_path
            else None
        ),
        network_requests=[
            {
                "url": item.url,
                "method": item.method,
                "resource_type": item.resource_type,
                "blocked": item.blocked,
                "reason": item.reason,
            }
            for item in analysis.network_requests
        ],
    )


@router.post("", response_model=AnalysisCreateResponse, status_code=201)
async def create_analysis(
    payload: AnalysisCreateRequest, db: Session = Depends(get_db)
) -> AnalysisCreateResponse:
    if not payload.url.strip():
        raise HTTPException(status_code=422, detail="url must not be empty")
    analysis_id = str(uuid.uuid4())
    db.add(
        AnalysisDB(
            id=analysis_id,
            submitted_url=payload.url,
            status=AnalysisStatus.QUEUED.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    enqueue_analysis(analysis_id)
    return AnalysisCreateResponse(id=analysis_id, status=AnalysisStatus.QUEUED)


@router.get("/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisResult:
    result = _get_analysis(db, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return _to_result(result)
