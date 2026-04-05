"""WebDAV availability checker for nzbdav streams."""

import base64
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import xbmc


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
    xbmc.log("NZB-DAV: WebDAV check URL: {}".format(url), xbmc.LOGDEBUG)
    try:
        status = _http_head(url, settings["username"], settings["password"])
        available = status == 200
        xbmc.log(
            "NZB-DAV: WebDAV check '{}': status={} available={}".format(
                filename, status, available
            ),
            xbmc.LOGDEBUG,
        )
        return available
    except Exception as e:
        xbmc.log(
            "NZB-DAV: WebDAV check failed for '{}': {}".format(filename, e),
            xbmc.LOGERROR,
        )
        return False


def check_file_available_with_retry(filename, max_retries=3, retry_delay=2):
    """Check WebDAV file availability with retry logic.

    Retries up to max_retries times on connection errors with retry_delay seconds
    between attempts. Distinguishes between different failure modes.

    Args:
        filename: The filename to check on the WebDAV server.
        max_retries: Maximum number of retry attempts on connection errors.
        retry_delay: Seconds to wait between retries.

    Returns:
        Tuple of (available: bool, error_type: str or None).
        error_type is one of: None (success), "not_found", "auth_failed",
        "server_error", "connection_error".
    """
    settings = _get_settings()
    url = build_webdav_url(filename)
    xbmc.log("NZB-DAV: WebDAV check with retry URL: {}".format(url), xbmc.LOGDEBUG)

    attempt = 0
    while attempt <= max_retries:
        try:
            status = _http_head(url, settings["username"], settings["password"])

            if status == 200:
                xbmc.log(
                    "NZB-DAV: WebDAV file '{}' is available".format(filename),
                    xbmc.LOGINFO,
                )
                return True, None

            if status == 404:
                xbmc.log(
                    "NZB-DAV: WebDAV file '{}' not found (404)".format(filename),
                    xbmc.LOGDEBUG,
                )
                return False, "not_found"

            if status in (401, 403):
                xbmc.log(
                    "NZB-DAV: WebDAV auth failed for '{}' (status={})".format(
                        filename, status
                    ),
                    xbmc.LOGERROR,
                )
                return False, "auth_failed"

            if status >= 500:
                xbmc.log(
                    "NZB-DAV: WebDAV server error for '{}' (status={})".format(
                        filename, status
                    ),
                    xbmc.LOGERROR,
                )
                return False, "server_error"

            # Other non-200 status: treat as not found
            xbmc.log(
                "NZB-DAV: WebDAV unexpected status {} for '{}'".format(
                    status, filename
                ),
                xbmc.LOGDEBUG,
            )
            return False, "not_found"

        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                xbmc.log(
                    "NZB-DAV: WebDAV connection error for '{}' "
                    "after {} attempts: {}".format(filename, max_retries + 1, e),
                    xbmc.LOGERROR,
                )
                return False, "connection_error"

            xbmc.log(
                "NZB-DAV: WebDAV connection error for '{}' (attempt {}/{}): {}".format(
                    filename, attempt, max_retries, e
                ),
                xbmc.LOGDEBUG,
            )
            time.sleep(retry_delay)

    return False, "connection_error"
