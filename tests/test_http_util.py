# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

from unittest.mock import MagicMock, patch

from resources.lib.http_util import format_size, http_get, notify, redact_url


@patch("resources.lib.http_util.urlopen")
def test_http_get_returns_decoded_response(mock_urlopen):
    """http_get should return decoded UTF-8 string."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"status": true}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    result = http_get("http://example.com/api")
    assert result == '{"status": true}'


@patch("resources.lib.http_util.urlopen")
def test_http_get_passes_timeout(mock_urlopen):
    """http_get should forward the timeout argument to urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"ok"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    http_get("http://example.com/api", timeout=30)
    _, kwargs = mock_urlopen.call_args
    assert kwargs.get("timeout") == 30


def test_notify_does_not_crash():
    """notify should call xbmc.executebuiltin without error."""
    notify("Test", "Message", 3000)


def test_notify_default_duration_does_not_crash():
    """notify should work with default duration."""
    notify("Heading", "Body")


def test_redact_url_hides_apikey():
    """redact_url should replace apikey values with ***."""
    url = "http://hydra:5076/api?apikey=secretkey123&t=movie&imdbid=tt1234567"
    result = redact_url(url)
    assert "secretkey123" not in result
    assert "apikey=REDACTED" in result
    assert "t=movie" in result
    assert "imdbid=tt1234567" in result


def test_redact_url_preserves_url_without_apikey():
    """redact_url should pass through URLs without apikey unchanged."""
    url = "http://example.com/api?mode=history&limit=200"
    result = redact_url(url)
    assert result == url


# ---------------------------------------------------------------------------
# format_size
# ---------------------------------------------------------------------------


def test_format_size_gigabytes():
    assert format_size(1073741824) == "1.0 GB"


def test_format_size_gigabytes_large():
    assert format_size(107374182400) == "100.0 GB"


def test_format_size_megabytes():
    assert format_size(5242880) == "5.0 MB"


def test_format_size_megabytes_decimal():
    assert format_size(10485760) == "10.0 MB"


def test_format_size_bytes():
    assert format_size(512) == "512 B"


def test_format_size_none_returns_empty():
    assert format_size(None) == ""


def test_format_size_zero_returns_empty():
    assert format_size(0) == ""


def test_format_size_string_input():
    """format_size should accept string byte counts as received from NZB data."""
    assert format_size("1073741824") == "1.0 GB"
    assert format_size("5242880") == "5.0 MB"
