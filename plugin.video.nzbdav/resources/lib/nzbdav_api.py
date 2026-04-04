"""nzbdav SABnzbd-compatible API client."""

import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError


def _get_settings():
    import xbmcaddon

    addon = xbmcaddon.Addon()
    url = addon.getSetting("nzbdav_url").rstrip("/")
    api_key = addon.getSetting("nzbdav_api_key")
    return url, api_key


def _http_get(url):
    req = Request(url)
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def submit_nzb(nzb_url, nzb_name=""):
    try:
        base_url, api_key = _get_settings()
    except Exception:
        return None
    params = {
        "mode": "addurl",
        "name": nzb_url,
        "nzbname": nzb_name,
        "apikey": api_key,
        "output": "json",
    }
    url = "{}/api?{}".format(base_url, urlencode(params))
    try:
        response_text = _http_get(url)
        response = json.loads(response_text)
    except (URLError, json.JSONDecodeError, Exception):
        return None
    if response.get("status") and response.get("nzo_ids"):
        return response["nzo_ids"][0]
    return None


def get_job_status(nzo_id):
    try:
        base_url, api_key = _get_settings()
    except Exception:
        return None
    params = {
        "mode": "queue",
        "nzo_ids": nzo_id,
        "apikey": api_key,
        "output": "json",
    }
    url = "{}/api?{}".format(base_url, urlencode(params))
    try:
        response_text = _http_get(url)
        response = json.loads(response_text)
    except (URLError, json.JSONDecodeError, Exception):
        return None
    slots = response.get("queue", {}).get("slots", [])
    for slot in slots:
        if slot.get("nzo_id") == nzo_id:
            return {
                "status": slot.get("status", "Unknown"),
                "percentage": slot.get("percentage", "0"),
                "filename": slot.get("filename", ""),
            }
    return None
