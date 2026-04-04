"""Resolve flow: submit NZB to nzbdav, poll until stream is ready, play."""

import time
from urllib.parse import unquote

import xbmcgui
import xbmcplugin

from resources.lib.nzbdav_api import submit_nzb, get_job_status
from resources.lib.webdav import check_file_available, get_webdav_stream_url


_STATUS_MESSAGES = {
    "Queued": "Queued...",
    "Fetching": "Fetching NZB...",
    "Propagating": "Waiting for propagation...",
    "Downloading": "Downloading... {}%",
    "Paused": "Paused",
}


def _get_poll_settings():
    import xbmcaddon

    addon = xbmcaddon.Addon()
    interval = int(addon.getSetting("poll_interval") or "5")
    timeout = int(addon.getSetting("download_timeout") or "3600")
    return interval, timeout


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

    nzo_id = submit_nzb(nzb_url, title)
    if not nzo_id:
        dialog.close()
        _notify("NZB-DAV", "Failed to submit NZB to nzbdav")
        return

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed >= download_timeout:
            dialog.close()
            _notify(
                "NZB-DAV", "Download timed out after {} seconds".format(int(elapsed))
            )
            return

        if dialog.iscanceled():
            dialog.close()
            return

        job_status = get_job_status(nzo_id)
        if job_status:
            status = job_status.get("status", "Unknown")
            percentage = job_status.get("percentage", "0")

            if status.lower() in ("failed", "deleted"):
                dialog.close()
                _notify("NZB-DAV", "Download failed")
                return

            msg = _STATUS_MESSAGES.get(status, "Status: {}".format(status))
            if "{}" in msg:
                msg = msg.format(percentage)
            progress = min(int(percentage or 0), 100)
            dialog.update(progress, msg)

        if check_file_available(title):
            dialog.close()
            stream_url = get_webdav_stream_url(title)
            li = xbmcgui.ListItem(path=stream_url)
            xbmcplugin.setResolvedUrl(handle, True, li)
            return

        time.sleep(poll_interval)


def _notify(heading, message, duration=5000):
    import xbmc

    xbmc.executebuiltin("Notification({}, {}, {})".format(heading, message, duration))
