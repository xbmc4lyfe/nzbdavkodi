from unittest.mock import patch, MagicMock
from resources.lib.player_installer import (
    install_player,
    get_install_targets,
    PLAYER_TARGETS,
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
