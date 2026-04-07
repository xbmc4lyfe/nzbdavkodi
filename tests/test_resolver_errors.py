# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Error-path tests for the resolver module.

These tests cover failure scenarios encountered by real users:
misconfigured servers, failed downloads, and polling timeouts.
"""

from unittest.mock import MagicMock, patch

from resources.lib.resolver import resolve


def _make_monitor():
    """Return a mock xbmc.Monitor that never signals Kodi shutdown."""
    monitor = MagicMock()
    monitor.waitForAbort.return_value = False
    return monitor


@patch("resources.lib.resolver._notify")
@patch("resources.lib.resolver.xbmc")
@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.get_job_history")
@patch("resources.lib.resolver.get_job_status")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_aborts_on_nzbdav_failed_status(
    mock_poll,
    mock_submit,
    mock_status,
    mock_history,
    mock_plugin,
    mock_gui,
    mock_xbmc,
    mock_notify,
):
    """When nzbdav reports job Failed, resolve() should notify user and call setResolvedUrl(False).

    User scenario: nzbdav cannot download the NZB — for example because the article
    is missing from Usenet (incomplete post) or the NZB is corrupt.  The addon must
    surface a notification so the user knows to try a different result, and must
    call setResolvedUrl(False) so Kodi does not hang waiting for playback.
    """  # noqa: E501
    mock_poll.return_value = (2, 60)
    mock_submit.return_value = "SABnzbd_nzo_abc123"
    mock_status.return_value = {"status": "Failed", "percentage": "0"}
    mock_history.return_value = None
    mock_xbmc.Monitor.return_value = _make_monitor()

    dialog = MagicMock()
    dialog.iscanceled.return_value = False
    mock_gui.DialogProgress.return_value = dialog

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_plugin.setResolvedUrl.assert_called_once_with(1, False, mock_gui.ListItem())
    mock_notify.assert_called(), "User must be notified when the job fails"


@patch("resources.lib.resolver._notify")
@patch("resources.lib.resolver.xbmc")
@patch("resources.lib.resolver.time")
@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.get_job_history")
@patch("resources.lib.resolver.get_job_status")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_times_out_gracefully(
    mock_poll,
    mock_submit,
    mock_status,
    mock_history,
    mock_plugin,
    mock_gui,
    mock_time,
    mock_xbmc,
    mock_notify,
):
    """When polling exceeds timeout, resolve() should notify and not hang.

    User scenario: a very large file is still downloading when the configured
    download_timeout (default 1 hour) is reached.  The addon must abort polling,
    show the user a "timed out" message, and call setResolvedUrl(False) so Kodi
    does not freeze waiting indefinitely.
    """
    mock_poll.return_value = (2, 5)  # 5-second timeout
    mock_submit.return_value = "SABnzbd_nzo_abc123"
    mock_status.return_value = {"status": "Downloading", "percentage": "10"}
    mock_history.return_value = None
    mock_xbmc.Monitor.return_value = _make_monitor()

    dialog = MagicMock()
    dialog.iscanceled.return_value = False
    mock_gui.DialogProgress.return_value = dialog

    # Simulate time jumping past the timeout on the second call
    mock_time.time.side_effect = [0.0, 10.0]

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_plugin.setResolvedUrl.assert_called_once_with(1, False, mock_gui.ListItem())
    mock_notify.assert_called(), "User must be notified when the download times out"
    notify_args = mock_notify.call_args[0]
    timed_out_msg = notify_args[1].lower()
    assert (
        "timed out" in timed_out_msg or "timeout" in timed_out_msg
    ), "The timeout notification message should mention 'timed out' or 'timeout'"
