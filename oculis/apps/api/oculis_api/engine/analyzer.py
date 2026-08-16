"""Small, explainable URL and response analyzer for the first OCULIS release."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from oculis_api.engine.safe_url import SafeFetchResult, fetch_safely, validate_target
from oculis_api.schemas import (
    AnalysisSignals,
    Finding,
    RedirectHop,
)

SUSPICIOUS_TLDS = {
    "click",
    "country",
    "gq",
    "icu",
    "info",
    "live",
    "loan",
    "mom",
    "top",
    "zip",
}
KEYWORDS = {
    "account",
    "billing",
    "confirm",
    "gift",
    "login",
    "password",
    "recover",
    "secure",
    "verify",
}
SEVERITY_WEIGHT = {"info": 0, "low": 5, "medium": 14, "high": 25, "critical": 40}


@dataclass(slots=True)
class AnalysisOutput:
    normalized_url: str
    risk_score: int
    verdict: str
    findings: list[Finding]
    redirects: list[RedirectHop]
    signals: AnalysisSignals


def _finding(
    category: str,
    severity: str,
    title: str,
    detail: str,
    evidence: str | None = None,
) -> Finding:
    return Finding(
        id=f"{category}-{len(title)}-{severity}",
        category=category,
        severity=severity,
        title=title,
        detail=detail,
        evidence=evidence,
    )


def inspect_url(url: str) -> list[Finding]:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    labels = hostname.split(".")
    findings: list[Finding] = []
    lowered = url.lower()
    tld = labels[-1] if len(labels) > 1 else ""

    if hostname.startswith("xn--") or any(label.startswith("xn--") for label in labels):
        findings.append(
            _finding(
                "url",
                "medium",
                "Internationalized hostname",
                (
                    "The hostname uses punycode. This can be legitimate, but it can "
                    "also hide lookalike characters."
                ),
                hostname,
            )
        )
    if len(hostname) > 55 or len(labels) >= 5:
        findings.append(
            _finding(
                "url",
                "low",
                "Unusually complex hostname",
                (
                    "Long or deeply nested hostnames are commonly used to disguise "
                    "the registered domain."
                ),
                hostname,
            )
        )
    if tld in SUSPICIOUS_TLDS:
        findings.append(
            _finding(
                "url",
                "low",
                "Higher-risk top-level domain",
                f".{tld} has elevated abuse rates in OCULIS's conservative heuristic set.",
                f".{tld}",
            )
        )
    keyword_hits = sorted({word for word in KEYWORDS if word in lowered})
    if len(keyword_hits) >= 2:
        findings.append(
            _finding(
                "url",
                "medium",
                "Credential-themed URL language",
                "Multiple account or verification terms appear in the target URL.",
                ", ".join(keyword_hits),
            )
        )
    if "@" in url or "%40" in lowered:
        findings.append(
            _finding(
                "url",
                "high",
                "Deceptive URL delimiter",
                (
                    "The target contains an at-sign, which can make text before the "
                    "real hostname look trustworthy."
                ),
                url,
            )
        )
    if parsed.port and parsed.port not in {80, 443}:
        findings.append(
            _finding(
                "url",
                "low",
                "Non-standard HTTP port",
                "The URL uses a port other than the conventional HTTP or HTTPS port.",
                str(parsed.port),
            )
        )
    if len(parsed.path) > 120 or parsed.path.count("%") >= 3:
        findings.append(
            _finding(
                "url",
                "low",
                "Obfuscated path",
                "The path is unusually long or heavily encoded.",
                parsed.path[:180],
            )
        )
    return findings


def inspect_response(result: SafeFetchResult) -> list[Finding]:
    body_lower = result.body[:300_000].lower()
    findings: list[Finding] = []
    content_type = result.headers.get("content-type", "")
    if b"<input" in body_lower and b"password" in body_lower:
        findings.append(
            _finding(
                "page",
                "medium",
                "Password input detected",
                (
                    "The rendered response contains a password field. This is not "
                    "malicious by itself, but it raises the stakes of the destination."
                ),
                '<input ... type="password"',
            )
        )
    if re.search(rb"<title[^>]*>[^<]*(verify|login|account|password)", body_lower):
        findings.append(
            _finding(
                "page",
                "low",
                "Credential-themed page title",
                (
                    "The document title contains language associated with account "
                    "access or verification."
                ),
                "title text",
            )
        )
    if "text/html" not in content_type and result.status_code < 400:
        findings.append(
            _finding(
                "infra",
                "info",
                "Non-HTML response",
                "The endpoint returned a non-HTML content type, so page-level checks were limited.",
                content_type or "missing content-type",
            )
        )
    return findings


def calculate_score(findings: list[Finding], redirects: list[RedirectHop]) -> tuple[int, str]:
    score = sum(SEVERITY_WEIGHT.get(finding.severity, 0) for finding in findings)
    if len(redirects) >= 3:
        score += 10
    score = min(100, score)
    if score >= 75:
        verdict = "critical"
    elif score >= 50:
        verdict = "high risk"
    elif score >= 25:
        verdict = "suspicious"
    else:
        verdict = "low risk"
    return score, verdict


async def analyze(
    url: str,
    *,
    max_redirects: int,
    max_bytes: int,
    timeout_seconds: int,
) -> AnalysisOutput:
    normalized, _ = await asyncio.to_thread(validate_target, url)
    findings = inspect_url(normalized)
    result = await fetch_safely(
        normalized,
        max_redirects=max_redirects,
        max_bytes=max_bytes,
        timeout_seconds=timeout_seconds,
    )
    findings.extend(inspect_response(result))
    if result.status_code >= 400:
        findings.append(
            _finding(
                "infra",
                "low",
                "HTTP error response",
                "The destination responded with an error status.",
                str(result.status_code),
            )
        )
    redirects = [
        RedirectHop(
            hop=redirect.hop,
            url=redirect.url,
            status_code=redirect.status_code,
            location=redirect.location,
        )
        for redirect in result.redirects
    ]
    score, verdict = calculate_score(findings, redirects)
    parsed = urlsplit(result.final_url)
    signals = AnalysisSignals(
        scheme=parsed.scheme,
        hostname=parsed.hostname or "",
        port=parsed.port or (443 if parsed.scheme == "https" else 80),
        resolved_ips=result.resolved_ips,
        final_url=result.final_url,
        status_code=result.status_code,
        content_type=result.headers.get("content-type"),
        response_size=len(result.body),
        tls_version=None,
        server=result.headers.get("server"),
        elapsed_ms=result.elapsed_ms,
    )
    return AnalysisOutput(
        normalized_url=normalized,
        risk_score=score,
        verdict=verdict,
        findings=findings,
        redirects=redirects,
        signals=signals,
    )
