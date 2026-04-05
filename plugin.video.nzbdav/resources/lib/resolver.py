"""Resolve flow: submit NZB to nzbdav, poll until stream is ready, play."""

import threading
import time
from urllib.parse import unquote

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.http_util import notify as _notify
from resources.lib.nzbdav_api import get_job_status, submit_nzb
from resources.lib.playback_monitor import PlaybackMonitor
from resources.lib.webdav import (
    check_file_available_with_retry,
    get_webdav_stream_url,
    validate_stream,
)

_STATUS_MESSAGES = {
    "Queued": "Queued...",
    "Fetching": "Fetching NZB...",
    "Propagating": "Waiting for propagation...",
    "Downloading": "Downloading... {}%",
    "Paused": "Paused",
}

_ERROR_MESSAGES = {
    "auth_failed": "WebDAV authentication failed. Check credentials.",
    "server_error": "WebDAV server error. Retrying...",
    "connection_error": "WebDAV connection error. Check server.",
}


def _get_poll_settings():
    import xbmcaddon

    addon = xbmcaddon.Addon()
    interval = int(addon.getSetting("poll_interval") or "5")
    timeout = int(addon.getSetting("download_timeout") or "3600")
    return interval, timeout


def _poll_once(nzo_id, title):
    """Poll nzbdav API and WebDAV in parallel.

    Returns (job_status, file_available, error_type).
    """
    job_status = [None]
    file_available = [False]
    error_type = [None]

    def check_api():
        job_status[0] = get_job_status(nzo_id)

    def check_webdav():
        available, error = check_file_available_with_retry(
            title, max_retries=1, retry_delay=1
        )
        file_available[0] = available
        error_type[0] = error

    t1 = threading.Thread(target=check_api)
    t2 = threading.Thread(target=check_webdav)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    xbmc.log(
        "NZB-DAV: Poll result - job_status={} file_available={} error_type={}".format(
            job_status[0], file_available[0], error_type[0]
        ),
        xbmc.LOGDEBUG,
    )
    return job_status[0], file_available[0], error_type[0]


def resolve(handle, params):
    nzb_url = unquote(params.get("nzburl", ""))
    title = unquote(params.get("title", ""))

    if not nzb_url:
        _notify("NZB-DAV", "No NZB URL provided")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    poll_interval, download_timeout = _get_poll_settings()

    dialog = xbmcgui.DialogProgress()
    dialog.create("NZB-DAV", "Submitting NZB to nzbdav...")

    xbmc.log("NZB-DAV: Submitting NZB for '{}'".format(title), xbmc.LOGINFO)
    nzo_id = submit_nzb(nzb_url, title)
    if not nzo_id:
        dialog.close()
        _notify("NZB-DAV", "Failed to submit NZB to nzbdav")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    xbmc.log(
        "NZB-DAV: NZB submitted, nzo_id={}, polling every {}s (timeout={}s)".format(
            nzo_id, poll_interval, download_timeout
        ),
        xbmc.LOGINFO,
    )

    monitor = xbmc.Monitor()
    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time

        if elapsed >= download_timeout:
            dialog.close()
            xbmc.log(
                "NZB-DAV: Download timed out after {}s for nzo_id={}".format(
                    int(elapsed), nzo_id
                ),
                xbmc.LOGERROR,
            )
            _notify(
                "NZB-DAV", "Download timed out after {} seconds".format(int(elapsed))
            )
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return

        if dialog.iscanceled():
            xbmc.log(
                "NZB-DAV: User cancelled resolve for nzo_id={}".format(nzo_id),
                xbmc.LOGINFO,
            )
            dialog.close()
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return

        job_status, file_available, webdav_error = _poll_once(nzo_id, title)

        if job_status:
            status = job_status.get("status", "Unknown")
            percentage = job_status.get("percentage", "0")

            if status != last_status:
                xbmc.log(
                    "NZB-DAV: Job {} status changed: {} -> {}".format(
                        nzo_id, last_status, status
                    ),
                    xbmc.LOGINFO,
                )
                last_status = status

            if status.lower() in ("failed", "deleted"):
                dialog.close()
                xbmc.log(
                    "NZB-DAV: Job {} failed/deleted (status={})".format(nzo_id, status),
                    xbmc.LOGERROR,
                )
                _notify("NZB-DAV", "Download failed")
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return

            msg = _STATUS_MESSAGES.get(status, "Status: {}".format(status))
            if "{}" in msg:
                msg = msg.format(percentage)
            progress = min(int(percentage or 0), 100)
            dialog.update(progress, msg)

        # Handle WebDAV error types
        if webdav_error == "auth_failed":
            dialog.close()
            xbmc.log("NZB-DAV: WebDAV auth failed, stopping resolve", xbmc.LOGERROR)
            _notify("NZB-DAV", _ERROR_MESSAGES["auth_failed"])
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return

        if webdav_error == "server_error":
            xbmc.log(
                "NZB-DAV: WebDAV server error, will retry on next poll",
                xbmc.LOGWARNING,
            )

        if file_available:
            dialog.close()
            stream_url = get_webdav_stream_url(title)
            xbmc.log(
                "NZB-DAV: File available, streaming '{}' via WebDAV".format(title),
                xbmc.LOGINFO,
            )

            # Validate stream supports range requests before playback
            if not validate_stream(title):
                xbmc.log(
                    "NZB-DAV: Stream validation failed for '{}', "
                    "attempting playback anyway".format(title),
                    xbmc.LOGWARNING,
                )

            li = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(handle, True, li)

            # Start playback monitoring for auto-retry on stream drops
            pb_monitor = PlaybackMonitor(stream_url, title=title)
            pb_monitor.start_monitoring()
            return

        if monitor.waitForAbort(poll_interval):
            # Kodi is shutting down
            xbmc.log("NZB-DAV: Kodi shutdown detected, aborting resolve", xbmc.LOGINFO)
            dialog.close()
            return
