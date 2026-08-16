from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import Page, Route, async_playwright
from pydantic import BaseModel, Field

from safe_url import URLSafetyError, fetch_safely

app = FastAPI(title="OCULIS Browser Sandbox")
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "/artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


class RenderRequest(BaseModel):
    url: str
    timeout_seconds: int = Field(default=30, ge=5, le=60)


async def _capture_page(page: Page) -> dict[str, Any]:
    forms = await page.locator("form").evaluate_all(
        "forms => forms.map(form => ({action: form.action, method: form.method || 'get'}))"
    )
    password_inputs = await page.locator("input[type='password']").count()
    email_inputs = await page.locator("input[type='email']").count()
    iframes = await page.locator("iframe").evaluate_all("items => items.map(x => x.src).filter(Boolean)")
    scripts = await page.locator("script[src]").evaluate_all("items => items.map(x => x.src).filter(Boolean)")
    links = await page.locator("a[href]").evaluate_all("items => items.map(x => x.href).filter(Boolean)")
    return {
        "title": await page.title(),
        "forms": forms,
        "password_inputs": password_inputs,
        "email_inputs": email_inputs,
        "iframes": iframes,
        "script_urls": scripts,
        "external_links": links,
    }


async def _safe_route(route: Route, requests: list[dict[str, Any]]) -> None:
    request = route.request
    record = {"url": request.url, "method": request.method, "resource_type": request.resource_type}
    requests.append(record)
    if request.method not in {"GET", "HEAD"}:
        await route.abort("blockedbyclient")
        record["blocked"] = True
        record["reason"] = "only GET and HEAD are permitted in the sandbox"
        return
    try:
        result = await fetch_safely(
            request.url,
            max_redirects=0,
            max_bytes=2_000_000,
            timeout_seconds=10,
        )
        response_headers = {
            "content-type": result.headers.get("content-type", "application/octet-stream"),
            "cache-control": "no-store",
        }
        if "location" in result.headers:
            response_headers["location"] = result.headers["location"]
        await route.fulfill(
            status=result.status_code,
            headers=response_headers,
            body=result.body,
        )
    except URLSafetyError as exc:
        record["blocked"] = True
        record["reason"] = str(exc)
        await route.abort("blockedbyclient")
    except Exception as exc:  # noqa: BLE001
        import traceback

        record["blocked"] = True
        record["reason"] = str(exc)

        print(
            f"[SANDBOX] Request failed: {route.request.url}",
            flush=True,
        )
        traceback.print_exc()

        await route.abort("failed")


@app.post("/render")
async def render(payload: RenderRequest):
    artifact_id = uuid.uuid4().hex
    requests: list[dict[str, Any]] = []
    console_errors: list[str] = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context = await browser.new_context(
                java_script_enabled=True,
                ignore_https_errors=False,
                service_workers="block",
            )
            page = await context.new_page()
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            await page.route("**/*", lambda route: _safe_route(route, requests))
            await page.goto(payload.url, wait_until="domcontentloaded", timeout=payload.timeout_seconds * 1000)
            await page.wait_for_timeout(1000)
            data = await _capture_page(page)
            screenshot_path = ARTIFACT_DIR / f"{artifact_id}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            await browser.close()

        return JSONResponse(
            {
                "artifact_id": artifact_id,
                "screenshot_path": str(screenshot_path),
                "screenshot_mime": "image/png",
                "page": data,
                "console_errors": console_errors[:100],
                "network_requests": requests[:500],
            }
        )
    except URLSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"sandbox render failed: {exc}") from exc
