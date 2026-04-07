# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Error-path tests for webdav module.

These tests cover authentication and network failure scenarios encountered
by real users with misconfigured WebDAV servers.
"""

from unittest.mock import patch
from urllib.error import HTTPError

from resources.lib.webdav import find_video_file

_SETTINGS_WITH_AUTH = {
    "webdav_url": "http://webdav:8080",
    "nzbdav_url": "http://nzbdav:3000",
    "username": "user",
    "password": "pass",
}


@patch("resources.lib.webdav._get_settings")
@patch("resources.lib.webdav.urlopen")
def test_find_video_file_returns_none_on_403(mock_urlopen, mock_settings):
    """find_video_file() should return None (not raise) on HTTP 403.

    User scenario: the WebDAV credentials stored in the addon settings are wrong
    or have expired.  The server responds with HTTP 403 Forbidden when the addon
    issues a PROPFIND to list directory contents.  find_video_file() must catch
    the HTTPError and return None so the resolver can show the user an actionable
    "authentication failed" message rather than an unhandled exception.
    """
    mock_settings.return_value = _SETTINGS_WITH_AUTH
    mock_urlopen.side_effect = HTTPError(
        "http://webdav:8080/content/uncategorized/Movie/",
        403,
        "Forbidden",
        {},
        None,
    )

    result = find_video_file("/content/uncategorized/Movie/")

    assert result is None, (
        "find_video_file() must return None instead of raising when the WebDAV "
        "server responds with HTTP 403 Forbidden"
    )
