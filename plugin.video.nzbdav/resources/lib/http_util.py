# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Shared HTTP and Kodi utility functions."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def redact_url(url):
    """Redact API keys from URLs for safe logging."""
    parts = urlsplit(url)
    query = [
        (k, "REDACTED" if k.lower() == "apikey" else v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def http_get(url, timeout=15):
    """Perform an HTTP GET and return the response body as text."""
    req = Request(url)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def notify(heading, message, duration=5000):
    """Show a Kodi notification."""
    import xbmc

    xbmc.executebuiltin("Notification({}, {}, {})".format(heading, message, duration))


def format_size(size_bytes):
    """Format a byte count as a human-readable string.

    Returns an empty string for falsy input (None, 0, etc.).

    Examples:
        >>> format_size(1073741824)
        '1.0 GB'
        >>> format_size(5242880)
        '5.0 MB'
        >>> format_size(512)
        '512 B'
    """
    if not size_bytes:
        return ""
    size_bytes = int(size_bytes)
    if size_bytes >= 1073741824:
        return "{:.1f} GB".format(size_bytes / 1073741824)
    if size_bytes >= 1048576:
        return "{:.1f} MB".format(size_bytes / 1048576)
    return "{} B".format(size_bytes)
