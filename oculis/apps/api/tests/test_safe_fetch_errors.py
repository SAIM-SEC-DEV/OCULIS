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
