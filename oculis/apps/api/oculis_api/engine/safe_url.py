"""SSRF-safe URL validation and bounded HTTP fetching.

The key security invariant is that DNS validation and the TCP connection use the
same resolved address. The hostname remains the HTTP authority and TLS SNI name,
while a custom httpcore network backend pins the socket to the validated IP.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Iterable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend


class URLSafetyError(ValueError):
    """Raised when a URL must not be fetched by the analyzer."""


class SafeFetchError(RuntimeError):
    """Operational fetch failure with a stable user-facing classification."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        suffix = f" Detail: {detail}" if detail else ""
        super().__init__(f"[{code}] {message}{suffix}")


ALLOWED_PORTS = {80, 443}
CGNAT = ipaddress.ip_network("100.64.0.0/10")
AWS_IMDSV6 = ipaddress.ip_network("fd00:ec2::254/128")


def _decode_encoded_ipv4(hostname: str) -> ipaddress.IPv4Address | None:
    """Decode common integer/hex/octal IPv4 spellings used in SSRF filters."""
    candidate = hostname.strip().lower()
    try:
        if candidate.startswith("0x"):
            value = int(candidate, 16)
            if 0 <= value <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(value)
            return None
        if candidate.isdigit() and len(candidate) > 1:
            value = int(candidate, 10)
            if 0 <= value <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(value)
            return None

        parts = candidate.split(".")
        if len(parts) == 4 and any(part.startswith("0") and len(part) > 1 for part in parts):
            values: list[int] = []
            for part in parts:
                if not part or any(ch not in "01234567" for ch in part):
                    return None
                values.append(int(part, 8))
            if all(0 <= value <= 255 for value in values):
                return ipaddress.IPv4Address(".".join(str(value) for value in values))
    except ValueError:
        return None
    return None


def _parse_literal_or_encoded_ip(
    hostname: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return _decode_encoded_ipv4(hostname)


def _public_ip_or_error(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    address = _parse_literal_or_encoded_ip(value)
    if address is None:
        raise URLSafetyError(f"host resolved to an invalid IP address: {value}")

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address in CGNAT
        or address in AWS_IMDSV6
    ):
        raise URLSafetyError(f"host resolves to a non-public address: {address}")
    return address


def normalize_url(raw_url: str) -> str:
    """Normalize a user URL without making any network request."""
    candidate = raw_url.strip()
    if not candidate:
        raise URLSafetyError("URL must not be empty")

    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise URLSafetyError("only http and https URLs are allowed")
    if parsed.username or parsed.password:
        raise URLSafetyError("URLs with embedded credentials are not allowed")
    if not parsed.hostname:
        raise URLSafetyError("URL must include a hostname")

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise URLSafetyError("URL contains an invalid hostname or port") from exc

    if not hostname:
        raise URLSafetyError("URL must include a hostname")

    effective_port = port or (443 if parsed.scheme.lower() == "https" else 80)
    if effective_port not in ALLOWED_PORTS:
        raise URLSafetyError("only ports 80 and 443 are allowed")

    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


def _resolve(hostname: str, port: int) -> list[str]:
    literal = _parse_literal_or_encoded_ip(hostname)
    if literal is not None:
        return [_public_ip_or_error(literal.compressed).compressed]

    try:
        infos = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise URLSafetyError(f"hostname could not be resolved: {hostname}") from exc

    resolved: list[str] = []
    for info in infos:
        address = info[4][0]
        validated = _public_ip_or_error(address)
        compressed = validated.compressed
        if compressed not in resolved:
            resolved.append(compressed)

    if not resolved:
        raise URLSafetyError(f"hostname did not resolve: {hostname}")
    return resolved


def validate_target(url: str) -> tuple[str, list[str]]:
    """Return canonical URL and all validated DNS answers."""
    normalized = normalize_url(url)
    parsed = urlsplit(normalized)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    resolved = _resolve(parsed.hostname or "", port)
    return normalized, resolved


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Resolve once outside httpcore and pin all TCP connects to that answer."""

    def __init__(self, pins: dict[str, str]) -> None:
        self._pins = {host.lower().rstrip("."): ip for host, ip in pins.items()}
        self._backend = AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        key = host.lower().rstrip(".")
        pinned = self._pins.get(key)
        if pinned is None:
            raise httpcore.ConnectError(f"no validated IP pin exists for {host}")
        return await self._backend.connect_tcp(
            pinned,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("unix sockets are not permitted by OCULIS")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


def _pinned_transport(hostname: str, ip: str) -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
    # httpx does not expose httpcore's network backend publicly. Replacing the
    # backend on its owned connection pool keeps hostname authority/SNI intact
    # while changing only the TCP destination.
    pool = transport._pool  # type: ignore[attr-defined]
    pool._network_backend = _PinnedNetworkBackend({hostname: ip})  # type: ignore[attr-defined]
    return transport


@dataclass(slots=True)
class RedirectHop:
    hop: int
    url: str
    status_code: int
    location: str


@dataclass(slots=True)
class SafeFetchResult:
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    resolved_ips: list[str]
    redirects: list[RedirectHop] = field(default_factory=list)
    elapsed_ms: int = 0


async def fetch_safely(
    url: str,
    *,
    max_redirects: int = 10,
    max_bytes: int = 1_000_000,
    timeout_seconds: float = 12,
) -> SafeFetchResult:
    """Fetch using one validated DNS answer per redirect hop and no re-resolution."""
    current_url = url
    redirects: list[RedirectHop] = []
    started = monotonic()

    for hop in range(max_redirects + 1):
        current_url, resolved_ips = await asyncio.to_thread(validate_target, current_url)
        parsed = urlsplit(current_url)
        hostname = parsed.hostname or ""
        pinned_ip = resolved_ips[0]
        timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5))
        transport = _pinned_transport(hostname, pinned_ip)
        try:
            async with httpx.AsyncClient(
                transport=transport,
                follow_redirects=False,
                timeout=timeout,
                headers={"User-Agent": "OCULIS/0.1 safe-inspector"},
                trust_env=False,
            ) as client:
                async with client.stream("GET", current_url) as response:
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            raise SafeFetchError(
                                "RESPONSE_TOO_LARGE",
                                f"The response exceeded OCULIS's {max_bytes:,}-byte inspection limit.",
                                "The server responded, but the content was too large to inspect safely.",
                            )
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    headers = {
                        key.lower(): value
                        for key, value in response.headers.items()
                        if key.lower()
                        in {
                            "content-type",
                            "content-length",
                            "location",
                            "server",
                            "strict-transport-security",
                        }
                    }
                    status_code = response.status_code
        except URLSafetyError:
            raise
        except SafeFetchError:
            raise
        except httpx.ConnectTimeout as exc:
            scheme = parsed.scheme.upper()
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            raise SafeFetchError(
                "CONNECTION_TIMEOUT",
                f"The {scheme} connection to {hostname}:{port} timed out.",
                "The hostname resolved, but the target did not establish a connection before the timeout.",
            ) from exc
        except httpx.ConnectError as exc:
            scheme = parsed.scheme.upper()
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            detail = str(exc) or exc.__class__.__name__
            raise SafeFetchError(
                "CONNECTION_FAILED",
                f"OCULIS could not establish a {scheme} connection to {hostname}:{port}.",
                detail,
            ) from exc
        except httpx.RemoteProtocolError as exc:
            detail = str(exc) or exc.__class__.__name__
            raise SafeFetchError(
                "REMOTE_PROTOCOL_ERROR",
                f"The target closed or violated the HTTP connection while OCULIS was fetching {hostname}.",
                detail,
            ) from exc
        except httpx.ReadTimeout as exc:
            raise SafeFetchError(
                "RESPONSE_TIMEOUT",
                "The target did not finish sending its response within the safe timeout.",
                f"{hostname}: {exc.__class__.__name__}",
            ) from exc
        except httpx.HTTPError as exc:
            detail = str(exc) or repr(exc) or exc.__class__.__name__
            raise SafeFetchError(
                "HTTP_FETCH_ERROR",
                "OCULIS could not safely fetch the target over HTTP.",
                detail,
            ) from exc
        finally:
            await transport.aclose()

        location = headers.get("location")
        if status_code in {301, 302, 303, 307, 308} and location:
            if hop >= max_redirects:
                if max_redirects == 0:
                    return SafeFetchResult(
                        final_url=current_url,
                        status_code=status_code,
                        headers=headers,
                        body=body,
                        resolved_ips=resolved_ips,
                        redirects=redirects,
                        elapsed_ms=max(1, round((monotonic() - started) * 1000)),
                    )
                raise RuntimeError(f"redirect limit exceeded ({max_redirects})")
            next_url = urljoin(current_url, location)
            redirects.append(
                RedirectHop(
                    hop=hop + 1,
                    url=current_url,
                    status_code=status_code,
                    location=next_url,
                )
            )
            current_url = normalize_url(next_url)
            continue

        return SafeFetchResult(
            final_url=current_url,
            status_code=status_code,
            headers=headers,
            body=body,
            resolved_ips=resolved_ips,
            redirects=redirects,
            elapsed_ms=max(1, round((monotonic() - started) * 1000)),
        )

    raise RuntimeError("redirect limit exceeded")
