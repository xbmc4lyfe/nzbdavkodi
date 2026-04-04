from unittest.mock import patch
from resources.lib.webdav import check_file_available, build_webdav_url


@patch("resources.lib.webdav._get_settings")
def test_build_webdav_url_with_explicit_url(mock_settings):
    mock_settings.return_value = {
        "webdav_url": "http://webdav:8080",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user",
        "password": "pass",
    }
    url = build_webdav_url("The.Matrix.1999.2160p.mkv")
    assert url.startswith("http://webdav:8080/")
    assert "The.Matrix.1999.2160p.mkv" in url


@patch("resources.lib.webdav._get_settings")
def test_build_webdav_url_falls_back_to_nzbdav_url(mock_settings):
    mock_settings.return_value = {
        "webdav_url": "",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user",
        "password": "pass",
    }
    url = build_webdav_url("movie.mkv")
    assert url.startswith("http://nzbdav:3000/")


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_true_on_200(mock_head, mock_settings):
    mock_settings.return_value = {
        "webdav_url": "http://webdav:8080",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user",
        "password": "pass",
    }
    mock_head.return_value = 200
    available = check_file_available("movie.mkv")
    assert available is True


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_false_on_404(mock_head, mock_settings):
    mock_settings.return_value = {
        "webdav_url": "http://webdav:8080",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user",
        "password": "pass",
    }
    mock_head.return_value = 404
    available = check_file_available("movie.mkv")
    assert available is False


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav._http_head")
def test_check_file_available_returns_false_on_error(mock_head, mock_settings):
    mock_settings.return_value = {
        "webdav_url": "http://webdav:8080",
        "nzbdav_url": "http://nzbdav:3000",
        "username": "user",
        "password": "pass",
    }
    mock_head.side_effect = Exception("Connection refused")
    available = check_file_available("movie.mkv")
    assert available is False
