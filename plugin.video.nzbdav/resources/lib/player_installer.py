"""Player JSON installer for TMDBHelper and compatible addons."""

import json
import os

import xbmc
import xbmcaddon
import xbmcvfs


PLAYER_TARGETS = {
    "TMDBHelper": {
        "setting_id": "install_tmdbhelper",
        "path": "special://profile/addon_data/plugin.video.themoviedb.helper/players/",
    },
    "Fen": {
        "setting_id": "install_fen",
        "path": "special://profile/addon_data/plugin.video.fen/players/",
    },
    "Seren": {
        "setting_id": "install_seren",
        "path": "special://profile/addon_data/plugin.video.seren/players/",
    },
}

PLAYER_JSON = {
    "name": "NZB-DAV",
    "plugin": "plugin.video.nzbdav",
    "priority": 100,
    "is_resolvable": "true",
    "assert": {
        "play_movie": ["title", "year"],
        "play_episode": ["showname", "season", "episode"],
    },
    "play_movie": "plugin://plugin.video.nzbdav/search?type=movie&title={title}&year={year}&imdb={imdb}",
    "play_episode": "plugin://plugin.video.nzbdav/search?type=episode&title={showname}&year={showyear}&season={season}&episode={episode}&imdb={imdb}",
}


def get_install_targets():
    addon = xbmcaddon.Addon()
    targets = []
    for name, config in PLAYER_TARGETS.items():
        if addon.getSetting(config["setting_id"]).lower() == "true":
            targets.append((name, config["path"]))
    return targets


def install_player():
    targets = get_install_targets()

    if not targets:
        _notify("NZB-DAV", "No install targets selected. Check addon settings.")
        return

    player_content = json.dumps(PLAYER_JSON, indent=4)
    succeeded = []
    failed = []

    for name, path in targets:
        try:
            real_path = xbmcvfs.translatePath(path)
            if not xbmcvfs.exists(real_path):
                xbmcvfs.mkdirs(real_path)

            file_path = os.path.join(real_path, "nzbdav.json")
            f = xbmcvfs.File(file_path, "w")
            try:
                f.write(player_content)
                succeeded.append(name)
            finally:
                f.close()
        except Exception:
            failed.append(name)

    if succeeded:
        _notify("NZB-DAV", "Player installed to: {}".format(", ".join(succeeded)))
    if failed:
        _notify("NZB-DAV", "Failed to install to: {}".format(", ".join(failed)))


def _notify(heading, message, duration=5000):
    xbmc.executebuiltin("Notification({}, {}, {})".format(heading, message, duration))
