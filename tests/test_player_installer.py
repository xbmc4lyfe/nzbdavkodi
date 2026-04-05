import json
from unittest.mock import MagicMock, patch

from resources.lib.player_installer import (
    PLAYER_JSON,
    PLAYER_TARGETS,
    get_install_targets,
    install_player,
)


def test_player_targets_defined():
    assert "TMDBHelper" in PLAYER_TARGETS
    assert "Fen" in PLAYER_TARGETS
    assert "Seren" in PLAYER_TARGETS


@patch("resources.lib.player_installer.xbmcvfs")
@patch("resources.lib.player_installer.xbmcaddon")
def test_get_install_targets_returns_selected(mock_addon_mod, mock_vfs):
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {
        "install_tmdbhelper": "true",
        "install_fen": "false",
        "install_seren": "true",
    }.get(key, "false")
    mock_addon_mod.Addon.return_value = addon

    targets = get_install_targets()
    assert len(targets) == 2
    target_names = [t[0] for t in targets]
    assert "TMDBHelper" in target_names
    assert "Seren" in target_names


@patch("resources.lib.player_installer._notify")
@patch("resources.lib.player_installer.xbmcvfs")
@patch("resources.lib.player_installer.xbmcaddon")
def test_install_player_writes_to_targets(mock_addon_mod, mock_vfs, mock_notify):
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {
        "install_tmdbhelper": "true",
        "install_fen": "false",
        "install_seren": "false",
    }.get(key, "false")
    addon.getAddonInfo.return_value = "/path/to/addon"
    mock_addon_mod.Addon.return_value = addon

    mock_vfs.exists.return_value = True
    mock_vfs.translatePath.side_effect = lambda p: p.replace(
        "special://profile", "/home/kodi/.kodi/userdata"
    )

    mock_file = MagicMock()
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)
    mock_vfs.File.return_value = mock_file

    install_player()

    mock_vfs.File.assert_called()


@patch("resources.lib.player_installer._notify")
@patch("resources.lib.player_installer.xbmcvfs")
@patch("resources.lib.player_installer.xbmcaddon")
def test_install_player_no_targets_selected(mock_addon_mod, mock_vfs, mock_notify):
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: "false"
    mock_addon_mod.Addon.return_value = addon

    install_player()

    mock_notify.assert_called_once_with(
        "NZB-DAV", "No install targets selected. Check addon settings."
    )
    mock_vfs.File.assert_not_called()


# --- New tests ---


def test_player_json_contains_correct_plugin_url_patterns():
    """PLAYER_JSON should contain plugin:// URLs with the correct addon ID/routes."""
    assert "play_movie" in PLAYER_JSON, "PLAYER_JSON must have a play_movie key"
    assert "play_episode" in PLAYER_JSON, "PLAYER_JSON must have a play_episode key"

    play_movie_url = PLAYER_JSON["play_movie"]
    assert play_movie_url.startswith(
        "plugin://plugin.video.nzbdav/"
    ), "play_movie URL must use the correct addon plugin:// path"
    assert "type=movie" in play_movie_url, "play_movie URL must include type=movie"
    assert (
        "{title}" in play_movie_url
    ), "play_movie URL must include {title} placeholder"
    assert "{year}" in play_movie_url, "play_movie URL must include {year} placeholder"
    assert "{imdb}" in play_movie_url, "play_movie URL must include {imdb} placeholder"

    play_episode_url = PLAYER_JSON["play_episode"]
    assert play_episode_url.startswith(
        "plugin://plugin.video.nzbdav/"
    ), "play_episode URL must use the correct addon plugin:// path"
    assert (
        "type=episode" in play_episode_url
    ), "play_episode URL must include type=episode"
    assert (
        "{showname}" in play_episode_url
    ), "play_episode URL must include {showname} placeholder"
    assert (
        "{season}" in play_episode_url
    ), "play_episode URL must include {season} placeholder"
    assert (
        "{episode}" in play_episode_url
    ), "play_episode URL must include {episode} placeholder"

    # Verify it is valid JSON-serializable
    serialized = json.dumps(PLAYER_JSON)
    roundtripped = json.loads(serialized)
    assert (
        roundtripped["name"] == PLAYER_JSON["name"]
    ), "PLAYER_JSON must survive JSON round-trip"


@patch("resources.lib.player_installer._notify")
@patch("resources.lib.player_installer.xbmcvfs")
@patch("resources.lib.player_installer.xbmcaddon")
def test_install_player_creates_directory_when_missing(
    mock_addon_mod, mock_vfs, mock_notify
):
    """install_player should call xbmcvfs.mkdirs when the target dir doesn't exist."""
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: (
        "true" if key == "install_tmdbhelper" else "false"
    )
    mock_addon_mod.Addon.return_value = addon

    mock_vfs.translatePath.side_effect = lambda p: p.replace(
        "special://profile", "/home/kodi/.kodi/userdata"
    )
    # Directory does not exist
    mock_vfs.exists.return_value = False

    mock_file = MagicMock()
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)
    mock_vfs.File.return_value = mock_file

    install_player()

    (
        mock_vfs.mkdirs.assert_called_once(),
        ("mkdirs should be called when the target directory doesn't exist"),
    )
    # Verify the path passed to mkdirs contains the TMDBHelper addon_data path
    mkdirs_path = mock_vfs.mkdirs.call_args[0][0]
    assert (
        "themoviedb.helper" in mkdirs_path or "userdata" in mkdirs_path
    ), "mkdirs should be called with the correct target directory path"


@patch("resources.lib.player_installer._notify")
@patch("resources.lib.player_installer.xbmcvfs")
@patch("resources.lib.player_installer.xbmcaddon")
def test_install_player_handles_write_failure_gracefully(
    mock_addon_mod, mock_vfs, mock_notify
):
    """install_player should catch write exceptions and notify about failure."""
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: (
        "true" if key == "install_tmdbhelper" else "false"
    )
    mock_addon_mod.Addon.return_value = addon

    mock_vfs.translatePath.side_effect = lambda p: p.replace(
        "special://profile", "/home/kodi/.kodi/userdata"
    )
    mock_vfs.exists.return_value = True

    # Simulate a write failure by making xbmcvfs.File raise an exception
    mock_vfs.File.side_effect = OSError("Disk full")

    install_player()

    # Should not raise; should notify about failure
    notify_calls = [str(c) for c in mock_notify.call_args_list]
    assert any(
        "Failed" in s or "failed" in s for s in notify_calls
    ), "install_player should notify about write failures without raising"
