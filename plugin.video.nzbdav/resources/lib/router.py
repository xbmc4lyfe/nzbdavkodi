"""URL routing for plugin:// calls from Kodi / TMDBHelper."""

from urllib.parse import urlparse, parse_qs


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

    if path == "/search":
        _handle_search(handle, params)
    elif path == "/resolve":
        from resources.lib.resolver import resolve

        resolve(handle, params)
    elif path == "/install_player":
        from resources.lib.player_installer import install_player

        install_player()
    else:
        _handle_main_menu(handle)


def _handle_search(handle, params):
    """Search NZBHydra and present filtered results as a directory listing."""
    import xbmcplugin
    import xbmcgui
    from urllib.parse import quote
    from resources.lib.hydra import search_hydra
    from resources.lib.filter import filter_results

    search_type = params.get("type", "movie")
    title = params.get("title", "")
    year = params.get("year", "")
    imdb = params.get("imdb", "")
    season = params.get("season", "")
    episode = params.get("episode", "")

    results = search_hydra(
        search_type, title, year=year, imdb=imdb, season=season, episode=episode
    )

    if not results:
        import xbmc

        xbmc.executebuiltin(
            "Notification(NZB-DAV, No results found for {}, 3000)".format(title)
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    filtered = filter_results(results)

    for item in filtered:
        label = "{} | {} | {} | {}".format(
            item["title"],
            _format_size(item["size"]),
            item.get("indexer", ""),
            item.get("age", ""),
        )
        li = xbmcgui.ListItem(label=label)
        li.setInfo("video", {"title": item["title"]})

        url = "plugin://plugin.video.nzbdav/resolve?nzburl={}&title={}".format(
            quote(item["link"], safe=""),
            quote(item["title"], safe=""),
        )
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def _handle_main_menu(handle):
    """Show main menu with settings and install player options."""
    import xbmcplugin
    import xbmcgui

    # Install Player item
    li = xbmcgui.ListItem(label="Install Player File")
    url = "plugin://plugin.video.nzbdav/install_player"
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
