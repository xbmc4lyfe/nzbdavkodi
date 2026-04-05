"""NZBHydra2 Newznab API client."""

import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.error import URLError

from resources.lib.http_util import http_get as _http_get


NEWZNAB_NS = "http://www.newznab.com/DTD/2010/feeds/attributes/"


def _get_settings():
    """Read NZBHydra settings from Kodi addon config."""
    import xbmcaddon

    addon = xbmcaddon.Addon()
    url = addon.getSetting("hydra_url").rstrip("/")
    api_key = addon.getSetting("hydra_api_key")
    return url, api_key


def search_hydra(search_type, title, year="", imdb="", season="", episode=""):
    """Search NZBHydra2 for NZBs.

    Args:
        search_type: "movie" or "episode"
        title: Movie or show title
        year: Release year
        imdb: IMDb ID (e.g. "tt0133093")
        season: Season number (TV only)
        episode: Episode number (TV only)

    Returns:
        List of result dicts with keys: title, link, size, indexer, pubdate, age
    """
    try:
        base_url, api_key = _get_settings()
    except Exception:
        return []

    params = {"apikey": api_key, "o": "xml"}

    if search_type == "episode":
        params["t"] = "tvsearch"
        params["q"] = title
        if season:
            params["season"] = season
        if episode:
            params["ep"] = episode
    else:
        params["t"] = "movie"
        if imdb:
            params["imdbid"] = imdb
        else:
            params["q"] = title

    url = "{}/api?{}".format(base_url, urlencode(params))

    try:
        xml_text = _http_get(url)
    except (URLError, Exception):
        return []

    return parse_results(xml_text)


def parse_results(xml_text):
    """Parse Newznab XML response into a list of result dicts."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []
    for item in root.iter("item"):
        title = _get_text(item, "title")
        link = _get_text(item, "link")
        pubdate = _get_text(item, "pubDate")

        # Get size and indexer from newznab attributes
        size = ""
        indexer = ""
        for attr in item.iter("{%s}attr" % NEWZNAB_NS):
            name = attr.get("name", "")
            if name == "size":
                size = attr.get("value", "")
            elif name == "indexer":
                indexer = attr.get("value", "")

        # Fallback: get size from enclosure
        if not size:
            enclosure = item.find("enclosure")
            if enclosure is not None:
                size = enclosure.get("length", "")

        # Fallback: get link from enclosure
        if not link:
            enclosure = item.find("enclosure")
            if enclosure is not None:
                link = enclosure.get("url", "")

        age = _calculate_age(pubdate) if pubdate else ""

        results.append(
            {
                "title": title or "",
                "link": link or "",
                "size": size,
                "indexer": indexer,
                "pubdate": pubdate or "",
                "age": age,
            }
        )

    return results


def _get_text(element, tag):
    """Get text content of a child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text
    return ""


def _calculate_age(pubdate_str):
    """Calculate human-readable age from an RFC 2822 date string."""
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone

    try:
        pub = parsedate_to_datetime(pubdate_str)
        now = datetime.now(timezone.utc)
        delta = now - pub
        days = delta.days
        if days == 0:
            return "today"
        if days == 1:
            return "1 day"
        if days < 30:
            return "{} days".format(days)
        months = days // 30
        if months == 1:
            return "1 month"
        return "{} months".format(months)
    except Exception:
        return ""
