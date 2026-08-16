from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    STATIC_ANALYSIS = "static_analysis"
    NETWORK_ANALYSIS = "network_analysis"
    BROWSER_ANALYSIS = "browser_analysis"
    THREAT_ANALYSIS = "threat_analysis"
    SCORING = "scoring"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


class AnalysisCreateRequest(BaseModel):
    url: str = Field(
        ..., description="The suspicious URL to analyze", examples=["https://example.com"]
    )


class AnalysisCreateResponse(BaseModel):
    id: str
    status: AnalysisStatus


class Finding(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    detail: str
    evidence: str | None = None


class RedirectHop(BaseModel):
    hop: int
    url: str
    status_code: int
    location: str


class AnalysisSignals(BaseModel):
    scheme: str | None = None
    hostname: str | None = None
    port: int | None = None
    resolved_ips: list[str] = Field(default_factory=list)
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    response_size: int | None = None
    tls_version: str | None = None
    server: str | None = None
    elapsed_ms: int | None = None


class BrowserData(BaseModel):
    error: str | None = None
    title: str | None = None
    forms: list[dict] = Field(default_factory=list)
    password_inputs: int = 0
    email_inputs: int = 0
    iframes: list[str] = Field(default_factory=list)
    script_urls: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    id: str
    submitted_url: str
    status: AnalysisStatus
    created_at: datetime
    completed_at: datetime | None = None
    risk_score: int | None = None
    verdict: str | None = None
    normalized_url: str | None = None
    final_url: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    redirects: list[RedirectHop] = Field(default_factory=list)
    signals: AnalysisSignals | None = None
    error: str | None = None
    browser: BrowserData | None = None
    screenshot_url: str | None = None
    network_requests: list[dict] = Field(default_factory=list)
