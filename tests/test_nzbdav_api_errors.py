# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Error-path tests for nzbdav_api module.

These tests cover scenarios encountered by users with misconfigured or
flaky servers, where silent failures make debugging nearly impossible.
"""

from unittest.mock import patch

from resources.lib.nzbdav_api import get_job_status, submit_nzb


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_submit_nzb_returns_none_on_malformed_json(mock_http, mock_settings):
    """submit_nzb() should return None (not raise) when response is not valid JSON.

    User scenario: nzbdav returns an HTML error page (e.g. a proxy 502 Bad Gateway)
    instead of the expected JSON, causing json.loads() to raise JSONDecodeError.
    The addon must not propagate the exception — it should silently return None so
    the caller can show a friendly error to the user.
    """
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.return_value = "<html><body>502 Bad Gateway</body></html>"

    result = submit_nzb("http://hydra:5076/getnzb/abc123?apikey=testkey", "The.Matrix")

    assert (
        result is None
    ), "submit_nzb() must return None when the server responds with non-JSON content"


@patch("resources.lib.nzbdav_api._get_settings")
@patch("resources.lib.nzbdav_api._http_get")
def test_get_job_status_returns_none_on_connection_error(mock_http, mock_settings):
    """get_job_status() should return None (not raise) on network error.

    User scenario: nzbdav goes offline mid-download or the network drops while
    the addon is polling for job status.  The polling loop must handle a connection
    failure gracefully and continue retrying rather than crashing Kodi.
    """
    mock_settings.return_value = ("http://nzbdav:3000", "testkey")
    mock_http.side_effect = OSError("Network unreachable")

    result = get_job_status("SABnzbd_nzo_abc123")

    assert (
        result is None
    ), "get_job_status() must return None instead of raising on a network error"
