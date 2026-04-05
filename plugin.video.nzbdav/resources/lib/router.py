"""URL routing for plugin:// calls from Kodi / TMDBHelper."""

from urllib.parse import parse_qs, urlparse

import xbmc


def parse_route(url):
    """Extract the path from a plugin:// URL."""
    parsed = urlparse(url)
    path = parsed.path
    if not path or path == "":
        path = "/"
    return path


def parse_params(query_string):
    """Parse query string into a flat dict (first value only)."""
    if not query_string:
        return {}
    # Strip leading '?'
    if query_string.startswith("?"):
        query_string = query_string[1:]
    if not query_string:
        return {}
    parsed = parse_qs(query_string)
    return {k: v[0] for k, v in parsed.items()}


def route(argv):
    """Main entry point called from addon.py with sys.argv.

    argv[0] = base URL (plugin://plugin.video.nzbdav/)
    argv[1] = addon handle (int)
    argv[2] = query string (?type=movie&title=...)
    """
    base_url = argv[0]
    handle = int(argv[1])
    query_string = argv[2] if len(argv) > 2 else ""

    path = parse_route(base_url)
    params = parse_params(query_string)

    xbmc.log("NZB-DAV: Routing path='{}' params={}".format(path, params), xbmc.LOGDEBUG)

    if path == "/play":
        _handle_play(params)
    elif path == "/search":
        _handle_search(handle, params)
    elif path == "/resolve":
        from resources.lib.resolver import resolve

        resolve(handle, params)
    elif path == "/install_player":
        from resources.lib.player_installer import install_player

        install_player()
    elif path == "/clear_cache":
        from resources.lib.cache import clear_cache

        clear_cache()
        from resources.lib.http_util import notify

        notify("NZB-DAV", "Search cache cleared", 3000)
    else:
        _handle_main_menu(handle)


def _handle_play(params):
    """Full play flow: search, filter, show select dialog, resolve, play.

    Called via executebuiltin://RunPlugin from TMDBHelper player JSON.
    """
    import xbmcaddon
    import xbmcgui

    from resources.lib.cache import get_cached, set_cached
    from resources.lib.filter import filter_results
    from resources.lib.http_util import notify
    from resources.lib.hydra import search_hydra

    search_type = params.get("type", "movie")
    title = params.get("title", "")
    year = params.get("year", "")
    imdb = params.get("imdb", "")
    season = params.get("season", "")
    episode = params.get("episode", "")

    # Show progress spinner while searching
    progress = xbmcgui.DialogProgress()
    progress.create("NZB-DAV", "Searching for {}...".format(title))
    progress.update(10)

    cache_kwargs = dict(year=year, imdb=imdb, season=season, episode=episode)
    results = get_cached(search_type, title, **cache_kwargs)
    if results is None:
        results = search_hydra(
            search_type, title, year=year, imdb=imdb, season=season, episode=episode
        )
        if results:
            set_cached(search_type, title, results, **cache_kwargs)

    if not results:
        progress.close()
        notify("NZB-DAV", "No results found for {}".format(title), 3000)
        return

    if progress.iscanceled():
        progress.close()
        return

    progress.update(60, "Filtering {} results...".format(len(results)))
    filtered = filter_results(results)

    if not filtered:
        progress.close()
        notify("NZB-DAV", "All results filtered out for {}".format(title), 3000)
        return

    progress.update(90, "Preparing {} results...".format(len(filtered)))
    progress.close()

    # Auto-select best match if enabled
    addon = xbmcaddon.Addon()
    if addon.getSetting("auto_select_best").lower() == "true":
        selected = filtered[0]
    else:
        # Show select dialog with detailed labels
        labels = [_format_label(item) for item in filtered]
        dialog = xbmcgui.Dialog()
        choice = dialog.select("NZB-DAV: {} results".format(len(filtered)), labels)
        if choice < 0:
            return  # User cancelled
        selected = filtered[choice]

    # Resolve and play
    from resources.lib.resolver import resolve_and_play

    resolve_and_play(selected["link"], selected["title"])


def _handle_search(handle, params):
    """Search NZBHydra and present filtered results as a directory listing."""
    import xbmcaddon
    import xbmcplugin

    from resources.lib.cache import get_cached, set_cached
    from resources.lib.filter import filter_results
    from resources.lib.hydra import search_hydra

    search_type = params.get("type", "movie")
    title = params.get("title", "")
    year = params.get("year", "")
    imdb = params.get("imdb", "")
    season = params.get("season", "")
    episode = params.get("episode", "")

    cache_kwargs = dict(year=year, imdb=imdb, season=season, episode=episode)

    # Check cache first
    results = get_cached(search_type, title, **cache_kwargs)
    if results is None:
        results = search_hydra(
            search_type, title, year=year, imdb=imdb, season=season, episode=episode
        )
        if results:
            set_cached(search_type, title, results, **cache_kwargs)

    if not results:
        from resources.lib.http_util import notify

        notify("NZB-DAV", "No results found for {}".format(title), 3000)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    filtered = filter_results(results)

    # Auto-select best match if enabled
    addon = xbmcaddon.Addon()
    if addon.getSetting("auto_select_best").lower() == "true" and filtered:
        best = filtered[0]
        from resources.lib.resolver import resolve

        resolve(handle, {"nzburl": best["link"], "title": best["title"]})
        return

    _display_results(handle, filtered)


def _format_label(item):
    """Format a detailed label showing all parsed metadata.

    Format: [RES] [HDR] [CODEC] [AUDIO] [LANG] | filename | GROUP | INDEXER | SIZE
    """
    meta = item.get("_meta", {})
    badges = []

    # Resolution
    res = meta.get("resolution", "")
    if res:
        badges.append("[COLOR cyan]{}[/COLOR]".format(res))

    # HDR
    hdr = meta.get("hdr", [])
    if hdr:
        badges.append("[COLOR yellow]{}[/COLOR]".format(" ".join(hdr)))

    # Video codec
    codec = meta.get("codec", "")
    if codec:
        badges.append("[COLOR lime]{}[/COLOR]".format(codec))

    # Audio
    audio = meta.get("audio", [])
    if audio:
        badges.append("[COLOR orange]{}[/COLOR]".format(" ".join(audio)))

    # Languages
    langs = meta.get("languages", [])
    if langs:
        badges.append("[COLOR skyblue]{}[/COLOR]".format(" ".join(langs)))

    # Build badge line
    badge_str = " ".join(badges) if badges else ""

    # Filename
    title = item.get("title", "")

    # Release group
    group = meta.get("group", "")
    group_str = "[COLOR mediumpurple]{}[/COLOR]".format(group) if group else ""

    # Indexer
    indexer = item.get("indexer", "")
    indexer_str = "[COLOR gray]{}[/COLOR]".format(indexer) if indexer else ""

    # Size
    size_str = "[COLOR silver]{}[/COLOR]".format(_format_size(item.get("size")))

    # Age
    age = item.get("age", "")
    age_str = "[COLOR gray]{}[/COLOR]".format(age) if age else ""

    # Compose: badges | filename | group | indexer | size | age
    parts = [badge_str, title, group_str, indexer_str, size_str, age_str]
    return " | ".join(p for p in parts if p)


def _display_results(handle, results):
    """Add filtered results to the Kodi directory listing."""
    from urllib.parse import quote

    import xbmcgui
    import xbmcplugin

    for item in results:
        label = _format_label(item)
        li = xbmcgui.ListItem(label=label)
        li.setInfo("video", {"title": item["title"]})
        li.setProperty("IsPlayable", "true")

        url = "plugin://plugin.video.nzbdav/resolve?nzburl={}&title={}".format(
            quote(item["link"], safe=""),
            quote(item["title"], safe=""),
        )
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.setContent(handle, "videos")

    xbmcplugin.endOfDirectory(handle)


def _handle_main_menu(handle):
    """Show main menu with settings and install player options."""
    import xbmcgui
    import xbmcplugin

    # Install Player item
    li = xbmcgui.ListItem(label="Install Player File")
    url = "plugin://plugin.video.nzbdav/install_player"
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    # Clear Cache item
    li = xbmcgui.ListItem(label="Clear Cache")
    url = "plugin://plugin.video.nzbdav/clear_cache"
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    # Open Settings item
    li = xbmcgui.ListItem(label="Settings")
    url = "plugin://plugin.video.nzbdav/settings"
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def _format_size(size_bytes):
    """Format byte size to human readable."""
    if not size_bytes:
        return "N/A"
    size_bytes = int(size_bytes)
    if size_bytes >= 1073741824:
        return "{:.1f} GB".format(size_bytes / 1073741824)
    if size_bytes >= 1048576:
        return "{:.1f} MB".format(size_bytes / 1048576)
    return "{} B".format(size_bytes)
