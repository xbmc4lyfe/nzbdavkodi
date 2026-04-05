from urllib.parse import unquote
from unittest.mock import patch
from resources.lib.webdav import (
    check_file_available,
    build_webdav_url,
    get_webdav_stream_url,
)


_SETTINGS_WITH_AUTH = {
    "webdav_url": "http://webdav:8080",
    "nzbdav_url": "http://nzbdav:3000",
    "username": "user",
    "password": "pass",
}

_SETTINGS_NO_AUTH = {
    "webdav_url": "http://webdav:8080",
    "nzbdav_url": "http://nzbdav:3000",
    "username": "",
    "password": "",
}

_SETTINGS_FALLBACK = {
    "webdav_url": "",
    "nzbdav_url": "http://nzbdav:3000",
    "username": "user",
    "password": "pass",
}


@patch("resources.lib.webdav._get_settings")
def test_build_webdav_url_with_explicit_url(mock_settings):
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    url = build_webdav_url("The.Matrix.1999.2160p.mkv")
    assert url.startswith("http://webdav:8080/")
    assert "The.Matrix.1999.2160p.mkv" in url


@patch("resources.lib.webdav._get_settings")
def test_build_webdav_url_falls_back_to_nzbdav_url(mock_settings):
    mock_settings.return_value = _SETTINGS_FALLBACK
    url = build_webdav_url("movie.mkv")
    assert url.startswith("http://nzbdav:3000/")


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_true_on_200(mock_head, mock_settings):
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    mock_head.return_value = 200
    available = check_file_available("movie.mkv")
    assert available is True


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_false_on_404(mock_head, mock_settings):
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    mock_head.return_value = 404
    available = check_file_available("movie.mkv")
    assert available is False


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_false_on_error(mock_head, mock_settings):
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    mock_head.side_effect = Exception("Connection refused")
    available = check_file_available("movie.mkv")
    assert available is False


# --- URL encoding round-trip tests ---


@patch("resources.lib.webdav._get_settings")
def test_build_webdav_url_special_characters(mock_settings):
    """Filenames with spaces and special chars should be URL-encoded."""
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    filename = "Movie (2024) [1080p].mkv"
    url = build_webdav_url(filename)
    # The filename should be URL-encoded in the URL
    assert "Movie" in url
    # Verify the encoded filename can be decoded back
    encoded_part = url.split("/")[-1]
    assert unquote(encoded_part) == filename


@patch("resources.lib.webdav._get_settings")
def test_get_webdav_stream_url_with_auth(mock_settings):
    """Stream URL should embed credentials."""
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    url = get_webdav_stream_url("movie.mkv")
    assert url == "http://user:pass@webdav:8080/movie.mkv"


@patch("resources.lib.webdav._get_settings")
def test_get_webdav_stream_url_without_auth(mock_settings):
    """Stream URL without auth should be a plain URL."""
    mock_settings.return_value = _SETTINGS_NO_AUTH
    url = get_webdav_stream_url("movie.mkv")
    assert url == "http://webdav:8080/movie.mkv"


@patch("resources.lib.webdav._get_settings")
def test_get_webdav_stream_url_special_chars_in_credentials(mock_settings):
    """Credentials with special chars should be URL-encoded."""
    mock_settings.return_value = {
        "webdav_url": "http://webdav:8080",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user@domain",
        "password": "p@ss:word",
    }
    url = get_webdav_stream_url("movie.mkv")
    assert "user%40domain" in url
    assert "p%40ss%3Aword" in url
