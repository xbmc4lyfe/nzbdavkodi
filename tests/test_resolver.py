from unittest.mock import patch, MagicMock
from resources.lib.resolver import resolve


@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.check_file_available")
@patch("resources.lib.resolver.get_job_status")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver.get_webdav_stream_url")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_success(
    mock_poll,
    mock_stream_url,
    mock_submit,
    mock_status,
    mock_webdav,
    mock_plugin,
    mock_gui,
):
    mock_poll.return_value = (2, 60)
    mock_submit.return_value = "SABnzbd_nzo_abc123"
    mock_status.return_value = {"status": "Downloading", "percentage": "100"}
    mock_webdav.return_value = True
    mock_stream_url.return_value = "http://user:pass@webdav:8080/movie.mkv"

    dialog = MagicMock()
    dialog.iscanceled.return_value = False
    mock_gui.DialogProgress.return_value = dialog

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_submit.assert_called_once()
    mock_plugin.setResolvedUrl.assert_called_once()


@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_submit_failure(mock_poll, mock_submit, mock_plugin, mock_gui):
    mock_poll.return_value = (2, 60)
    mock_submit.return_value = None

    dialog = MagicMock()
    mock_gui.DialogProgress.return_value = dialog

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_plugin.setResolvedUrl.assert_not_called()


@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.check_file_available")
@patch("resources.lib.resolver.get_job_status")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_job_failed(
    mock_poll, mock_submit, mock_status, mock_webdav, mock_plugin, mock_gui
):
    mock_poll.return_value = (2, 60)
    mock_submit.return_value = "SABnzbd_nzo_abc123"
    mock_status.return_value = {"status": "Failed", "percentage": "0"}
    mock_webdav.return_value = False

    dialog = MagicMock()
    dialog.iscanceled.return_value = False
    mock_gui.DialogProgress.return_value = dialog

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_plugin.setResolvedUrl.assert_not_called()


@patch("resources.lib.resolver.xbmcgui")
@patch("resources.lib.resolver.xbmcplugin")
@patch("resources.lib.resolver.check_file_available")
@patch("resources.lib.resolver.get_job_status")
@patch("resources.lib.resolver.submit_nzb")
@patch("resources.lib.resolver._get_poll_settings")
def test_resolve_user_cancels(
    mock_poll, mock_submit, mock_status, mock_webdav, mock_plugin, mock_gui
):
    mock_poll.return_value = (2, 60)
    mock_submit.return_value = "SABnzbd_nzo_abc123"
    mock_status.return_value = {"status": "Downloading", "percentage": "50"}
    mock_webdav.return_value = False

    dialog = MagicMock()
    dialog.iscanceled.return_value = True
    mock_gui.DialogProgress.return_value = dialog

    resolve(1, {"nzburl": "http://hydra/getnzb/abc", "title": "movie.mkv"})

    mock_plugin.setResolvedUrl.assert_not_called()
