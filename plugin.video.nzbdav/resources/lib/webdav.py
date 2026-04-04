"""WebDAV availability checker for nzbdav streams."""

import base64
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def _get_settings():
    import xbmcaddon

    addon = xbmcaddon.Addon()
    return {
        "webdav_url": addon.getSetting("webdav_url").rstrip("/"),
        "nzbdav_url": addon.getSetting("nzbdav_url").rstrip("/"),
        "username": addon.getSetting("webdav_username"),
        "password": addon.getSetting("webdav_password"),
    }


def _http_head(url, username="", password=""):
    req = Request(url, method="HEAD")
    if username:
        credentials = "{}:{}".format(username, password)
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", "Basic {}".format(encoded))
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.getcode()
    except HTTPError as e:
        return e.code
    except (URLError, Exception):
        raise


def build_webdav_url(filename):
    settings = _get_settings()
    base = settings["webdav_url"] or settings["nzbdav_url"]
    return "{}/{}".format(base, quote(filename, safe=""))


def get_webdav_stream_url(filename):
    settings = _get_settings()
    base = settings["webdav_url"] or settings["nzbdav_url"]
    username = settings["username"]
    password = settings["password"]
    if username:
        proto, rest = base.split("://", 1)
        return "{}://{}:{}@{}/{}".format(
            proto,
            quote(username, safe=""),
            quote(password, safe=""),
            rest,
            quote(filename, safe=""),
        )
    return "{}/{}".format(base, quote(filename, safe=""))


def check_file_available(filename):
    settings = _get_settings()
    url = build_webdav_url(filename)
    try:
        status = _http_head(url, settings["username"], settings["password"])
        return status == 200
    except Exception:
        return False
