import socket

import pytest

from oculis_api.engine import safe_url
from oculis_api.engine.safe_url import URLSafetyError, validate_target


def _answers(ip: str):
    def resolver(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    return resolver


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "fd00:ec2::254",
        "::1",
        "fe80::1",
    ],
)
def test_private_and_metadata_ranges_are_blocked(monkeypatch, ip):
    monkeypatch.setattr(safe_url.socket, "getaddrinfo", _answers(ip))
    with pytest.raises(URLSafetyError):
        validate_target("https://example.com/")


@pytest.mark.parametrize("port", [22, 21, 25, 53, 3306, 5432, 6379, 8080, 8443])
def test_non_http_ports_are_blocked(port):
    with pytest.raises(URLSafetyError, match="ports 80 and 443"):
        validate_target(f"https://example.com:{port}/")


@pytest.mark.parametrize("scheme", ["ftp", "file", "gopher", "dict", "javascript", "data"])
def test_disallowed_schemes_are_blocked(scheme):
    with pytest.raises(URLSafetyError):
        validate_target(f"{scheme}://example.com/")


@pytest.mark.parametrize("encoded", ["2130706433", "0177.0.0.1", "0x7f000001"])
def test_encoded_ipv4_loopback_forms_are_blocked(encoded):
    with pytest.raises(URLSafetyError):
        validate_target(f"http://{encoded}/")


def test_public_address_is_not_false_positive(monkeypatch):
    monkeypatch.setattr(safe_url.socket, "getaddrinfo", _answers("93.184.216.34"))
    normalized, ips = validate_target("https://example.com/")
    assert normalized == "https://example.com/"
    assert ips == ["93.184.216.34"]
