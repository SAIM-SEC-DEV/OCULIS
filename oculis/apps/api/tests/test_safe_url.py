import asyncio
import socket

import pytest

from oculis_api.engine import safe_url
from oculis_api.engine.safe_url import URLSafetyError, normalize_url, validate_target


def fake_public_getaddrinfo(host: str, port: int, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]


def test_normalize_url_defaults_path_and_removes_fragment():
    assert normalize_url("HTTPS://Example.COM/foo#fragment") == "https://example.com/foo"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[fd00:ec2::254]/",
        "http://100.64.0.1/",
        "ftp://example.com/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "dict://example.com/",
        "javascript:alert(1)",
        "data:text/plain,hello",
        "https://user:pass@example.com/",
        "https://example.com:22/",
        "https://example.com:5432/",
        "https://example.com:6379/",
    ],
)
def test_unsafe_targets_are_rejected(url):
    with pytest.raises(URLSafetyError):
        validate_target(url)


@pytest.mark.parametrize("host", ["2130706433", "0x7f000001", "0177.0.0.1"])
def test_encoded_loopback_ip_forms_are_rejected(host):
    with pytest.raises(URLSafetyError):
        validate_target(f"http://{host}/")


def test_all_dns_answers_are_validated(monkeypatch):
    def answers(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.5", 443)),
        ]

    monkeypatch.setattr(safe_url.socket, "getaddrinfo", answers)
    with pytest.raises(URLSafetyError, match="non-public"):
        validate_target("https://example.com/")


def test_public_https_target_is_accepted(monkeypatch):
    monkeypatch.setattr(safe_url.socket, "getaddrinfo", fake_public_getaddrinfo)
    normalized, ips = validate_target("https://example.com/")
    assert normalized == "https://example.com/"
    assert ips == ["93.184.216.34"]


def test_dns_rebinding_cannot_trigger_a_second_hostname_lookup(monkeypatch):
    calls = []

    def rebinding_answers(host: str, port: int, *args, **kwargs):
        calls.append(host)
        answer = "93.184.216.34" if len(calls) == 1 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (answer, port))]

    monkeypatch.setattr(safe_url.socket, "getaddrinfo", rebinding_answers)
    normalized, ips = validate_target("https://example.com/")
    assert normalized == "https://example.com/"
    assert ips == ["93.184.216.34"]
    assert calls == ["example.com"]


def test_pinned_backend_uses_validated_ip(monkeypatch):
    captured = {}

    class FakeBackend:
        async def connect_tcp(self, host, port, **kwargs):
            captured["host"] = host
            captured["port"] = port
            return object()

        async def sleep(self, seconds):
            return None

    backend = safe_url._PinnedNetworkBackend({"example.com": "93.184.216.34"})
    backend._backend = FakeBackend()
    asyncio.run(backend.connect_tcp("example.com", 443))
    assert captured == {"host": "93.184.216.34", "port": 443}
