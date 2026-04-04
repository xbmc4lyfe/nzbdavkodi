import json
from unittest.mock import patch
from resources.lib.nzbdav_api import submit_nzb, get_job_status


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_submit_nzb_returns_nzo_id(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps(
        {"status": True, "nzo_ids": ["SABnzbd_nzo_abc123"]}
    )
    nzo_id = submit_nzb(
        "http://hydra:5076/getnzb/abc123?apikey=testkey", "The.Matrix.1999"
    )
    assert nzo_id == "SABnzbd_nzo_abc123"
    call_url = mock_http.call_args[0][0]
    assert "mode=addurl" in call_url
    assert "apikey=testkey" in call_url


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_submit_nzb_failure_returns_none(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps({"status": False, "nzo_ids": []})
    nzo_id = submit_nzb("http://hydra:5076/getnzb/abc123", "The.Matrix")
    assert nzo_id is None


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_submit_nzb_connection_error(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.side_effect = Exception("Connection refused")
    nzo_id = submit_nzb("http://hydra:5076/getnzb/abc123", "The.Matrix")
    assert nzo_id is None


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_downloading(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps(
        {
            "queue": {
                "slots": [
                    {
                        "nzo_id": "SABnzbd_nzo_abc123",
                        "status": "Downloading",
                        "percentage": "45",
                        "filename": "The.Matrix.1999.2160p",
                    }
                ]
            }
        }
    )
    status = get_job_status("SABnzbd_nzo_abc123")
    assert status["status"] == "Downloading"
    assert status["percentage"] == "45"


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_not_found(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps({"queue": {"slots": []}})
    status = get_job_status("SABnzbd_nzo_abc123")
    assert status is None


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_connection_error(mock_http, mock_settings):
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.side_effect = Exception("Connection refused")
    status = get_job_status("SABnzbd_nzo_abc123")
    assert status is None
