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
    """Open a full-screen directory listing of search results.

    Called via executebuiltin://RunPlugin from TMDBHelper player JSON.
    Redirects to /search via ActivateWindow for a full-screen view.
    """
    from urllib.parse import urlencode

    search_params = urlencode(
        {k: v for k, v in params.items() if v},
    )
    url = "plugin://plugin.video.nzbdav/search?{}".format(search_params)
    xbmc.log("NZB-DAV: Redirecting to full-screen search: {}".format(url), xbmc.LOGINFO)
    xbmc.executebuiltin("ActivateWindow(videos,{},return)".format(url))


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
    """Format a compact label with parsed metadata. No color tags for compatibility.

    Format: [RES HDR] CODEC AUDIO | SIZE | GROUP | INDEXER | age
    Line 2 (if using ListItem): filename
    """
    meta = item.get("_meta", {})
    tags = []

    # Resolution + HDR combined
    res = meta.get("resolution", "")
    hdr = meta.get("hdr", [])
    if res and hdr:
        tags.append("{} {}".format(res, "/".join(hdr)))
    elif res:
        tags.append(res)

    # Video codec
    codec = meta.get("codec", "")
    if codec:
        tags.append(codec)

    # Audio (first only for brevity)
    audio = meta.get("audio", [])
    if audio:
        tags.append(audio[0])

    # Languages
    langs = meta.get("languages", [])
    if langs:
        tags.append("/".join(langs))

    # Build the quality portion
    quality = " ".join(tags) if tags else "Unknown"

    # Size
    size_str = _format_size(item.get("size"))

    # Release group
    group = meta.get("group", "")

    # Indexer
    indexer = item.get("indexer", "")

    # Age
    age = item.get("age", "")

    # Line 1: [quality] | size | group | indexer | age
    parts = ["[{}]".format(quality), size_str]
    if group:
        parts.append(group)
    if indexer:
        parts.append(indexer)
    if age:
        parts.append(age)

    return " | ".join(parts)


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
