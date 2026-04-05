import json
from unittest.mock import patch

from resources.lib.nzbdav_api import get_job_status, submit_nzb


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


# --- New tests ---


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_submit_nzb_special_characters_in_name(mock_http, mock_settings):
    """submit_nzb should handle special characters in the NZB name without crashing."""
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps(
        {"status": True, "nzo_ids": ["SABnzbd_nzo_special99"]}
    )
    nzb_name = "Spider-Man: No Way Home (2021) 1080p BluRay & extras"
    nzo_id = submit_nzb("http://hydra:5076/getnzb/special", nzb_name)
    assert (
        nzo_id == "SABnzbd_nzo_special99"
    ), "submit_nzb should return nzo_id even when name has special characters"
    call_url = mock_http.call_args[0][0]
    assert "mode=addurl" in call_url, "URL should contain addurl mode"
    # The name should appear URL-encoded somewhere in the request
    assert "nzbname=" in call_url, "URL should contain nzbname parameter"


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_multiple_slots_finds_correct(mock_http, mock_settings):
    """get_job_status should find the correct slot when multiple jobs are queued."""
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps(
        {
            "queue": {
                "slots": [
                    {
                        "nzo_id": "SABnzbd_nzo_other1",
                        "status": "Downloading",
                        "percentage": "20",
                        "filename": "Other.Movie.2024",
                    },
                    {
                        "nzo_id": "SABnzbd_nzo_target",
                        "status": "Queued",
                        "percentage": "0",
                        "filename": "The.Matrix.1999.2160p",
                    },
                    {
                        "nzo_id": "SABnzbd_nzo_other2",
                        "status": "Paused",
                        "percentage": "75",
                        "filename": "Another.Show.S01E01",
                    },
                ]
            }
        }
    )
    status = get_job_status("SABnzbd_nzo_target")
    assert status is not None, "Should find the target job among multiple slots"
    assert (
        status["status"] == "Queued"
    ), "Should return the status of the correct (target) slot"
    assert status["percentage"] == "0", "Percentage should match the target slot"


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_returns_correct_fields(mock_http, mock_settings):
    """get_job_status should return a dict with status, percentage, filename."""
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = json.dumps(
        {
            "queue": {
                "slots": [
                    {
                        "nzo_id": "SABnzbd_nzo_fields_test",
                        "status": "Downloading",
                        "percentage": "62",
                        "filename": "Dune.Part.Two.2024.2160p",
                    }
                ]
            }
        }
    )
    status = get_job_status("SABnzbd_nzo_fields_test")
    assert status is not None
    assert "status" in status, "Result must contain 'status' key"
    assert "percentage" in status, "Result must contain 'percentage' key"
    assert "filename" in status, "Result must contain 'filename' key"
    assert status["status"] == "Downloading"
    assert status["percentage"] == "62"
    assert status["filename"] == "Dune.Part.Two.2024.2160p"
