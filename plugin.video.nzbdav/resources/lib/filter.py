"""Result filtering and sorting using PTT for title parsing."""

import xbmc

_RESOLUTION_MAP = {
    "2160p": "2160p",
    "4K": "2160p",
    "1080p": "1080p",
    "1080i": "1080p",
    "720p": "720p",
    "480p": "480p",
    "480i": "480p",
    "SD": "480p",
}

_HDR_MAP = {
    "HDR": "HDR10",
    "HDR10": "HDR10",
    "HDR10+": "HDR10+",
    "HDR10Plus": "HDR10+",
    "DV": "Dolby Vision",
    "Dolby Vision": "Dolby Vision",
    "DoVi": "Dolby Vision",
    "HLG": "HLG",
}

_AUDIO_MAP = {
    "Atmos": "Atmos",
    "TrueHD": "TrueHD",
    "DTS-HD MA": "DTS-HD MA",
    "DTS-HD": "DTS-HD MA",
    "DTS Lossless": "DTS-HD MA",
    "DTS:X": "DTS:X",
    "DTS-X": "DTS:X",
    "DD+": "DD+",
    "EAC3": "DD+",
    "E-AC-3": "DD+",
    "Dolby Digital Plus": "DD+",
    "DD": "DD",
    "AC3": "DD",
    "AC-3": "DD",
    "Dolby Digital": "DD",
    "DTS Lossy": "DD",
    "AAC": "AAC",
}

_CODEC_MAP = {
    "x265": "x265/HEVC",
    "HEVC": "x265/HEVC",
    "H.265": "x265/HEVC",
    "h265": "x265/HEVC",
    "hevc": "x265/HEVC",
    "x264": "x264/AVC",
    "AVC": "x264/AVC",
    "H.264": "x264/AVC",
    "h264": "x264/AVC",
    "avc": "x264/AVC",
    "AV1": "AV1",
    "av1": "AV1",
    "VP9": "VP9",
    "vp9": "VP9",
    "MPEG2": "MPEG-2",
    "MPEG-2": "MPEG-2",
    "mpeg2": "MPEG-2",
}


def _collect_enabled(addon, pairs):
    """Return labels for settings that are enabled (true).

    Args:
        addon: Kodi addon instance
        pairs: list of (setting_id, label) tuples
    """
    return [
        label
        for setting_id, label in pairs
        if addon.getSetting(setting_id).lower() == "true"
    ]


def _csv_setting(addon, key):
    """Read a comma-separated setting into a stripped list."""
    val = addon.getSetting(key).strip()
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def _get_filter_settings():
    """Read filter settings from Kodi addon config."""
    import xbmcaddon

    addon = xbmcaddon.Addon()

    resolutions = _collect_enabled(
        addon,
        [
            ("filter_2160p", "2160p"),
            ("filter_1080p", "1080p"),
            ("filter_720p", "720p"),
            ("filter_480p", "480p"),
        ],
    )

    hdr = _collect_enabled(
        addon,
        [
            ("filter_hdr10", "HDR10"),
            ("filter_hdr10plus", "HDR10+"),
            ("filter_dolby_vision", "Dolby Vision"),
            ("filter_hlg", "HLG"),
            ("filter_sdr", "SDR"),
        ],
    )

    audio = _collect_enabled(
        addon,
        [
            ("filter_atmos", "Atmos"),
            ("filter_truehd", "TrueHD"),
            ("filter_dtshd_ma", "DTS-HD MA"),
            ("filter_dtsx", "DTS:X"),
            ("filter_ddplus", "DD+"),
            ("filter_dd", "DD"),
            ("filter_aac", "AAC"),
        ],
    )

    codecs = _collect_enabled(
        addon,
        [
            ("filter_hevc", "x265/HEVC"),
            ("filter_avc", "x264/AVC"),
            ("filter_av1", "AV1"),
            ("filter_vp9", "VP9"),
            ("filter_mpeg2", "MPEG-2"),
        ],
    )

    languages = _collect_enabled(
        addon,
        [
            ("filter_english", "English"),
            ("filter_spanish", "Spanish"),
            ("filter_french", "French"),
            ("filter_german", "German"),
            ("filter_italian", "Italian"),
            ("filter_portuguese", "Portuguese"),
            ("filter_dutch", "Dutch"),
            ("filter_russian", "Russian"),
            ("filter_japanese", "Japanese"),
            ("filter_korean", "Korean"),
            ("filter_chinese", "Chinese"),
            ("filter_arabic", "Arabic"),
            ("filter_hindi", "Hindi"),
        ],
    )

    return {
        "resolutions": resolutions,
        "hdr": hdr,
        "audio": audio,
        "codecs": codecs,
        "languages": languages,
        "exclude_keywords": [
            k.lower() for k in _csv_setting(addon, "filter_exclude_keywords")
        ],
        "require_keywords": [
            k.lower() for k in _csv_setting(addon, "filter_require_keywords")
        ],
        "release_group": [
            g.lower() for g in _csv_setting(addon, "filter_release_group")
        ],
        "exclude_release_group": [
            g.lower() for g in _csv_setting(addon, "filter_exclude_release_group")
        ],
        "min_size": int(addon.getSetting("filter_min_size") or "0"),
        "max_size": int(addon.getSetting("filter_max_size") or "0"),
        "sort_order": int(addon.getSetting("sort_order") or "0"),
        "max_results": int(addon.getSetting("max_results") or "25"),
    }


def parse_title_metadata(title):
    """Parse a scene title and return normalized metadata dict."""
    try:
        from resources.lib.ptt import parse_title

        parsed = parse_title(title)
    except Exception:
        parsed = {}

    raw_res = parsed.get("resolution", "") or ""
    resolution = _RESOLUTION_MAP.get(raw_res, raw_res)

    raw_hdr = parsed.get("hdr", [])
    if isinstance(raw_hdr, str):
        raw_hdr = [raw_hdr]
    hdr_list = [_HDR_MAP.get(h, h) for h in raw_hdr if h]

    raw_audio = parsed.get("audio", [])
    if isinstance(raw_audio, str):
        raw_audio = [raw_audio]
    audio_list = [_AUDIO_MAP.get(a, a) for a in raw_audio if a]

    raw_codec = parsed.get("codec", "") or ""
    codec = _CODEC_MAP.get(raw_codec, raw_codec)

    raw_langs = parsed.get("languages", [])
    if isinstance(raw_langs, str):
        raw_langs = [raw_langs]

    group = parsed.get("group", "") or ""

    return {
        "resolution": resolution,
        "hdr": hdr_list,
        "audio": audio_list,
        "codec": codec,
        "languages": raw_langs,
        "group": group,
    }


def matches_filters(result, meta, settings):
    """Check if a result passes all filter criteria."""
    title_lower = result["title"].lower()

    if settings["resolutions"] and meta["resolution"]:
        if meta["resolution"] not in settings["resolutions"]:
            return False

    if settings["hdr"] and meta["hdr"]:
        if not any(h in settings["hdr"] for h in meta["hdr"]):
            return False
    if settings["hdr"] and not meta["hdr"] and "SDR" not in settings["hdr"]:
        return False

    if settings["audio"] and meta["audio"]:
        if not any(a in settings["audio"] for a in meta["audio"]):
            return False

    if settings["codecs"] and meta["codec"]:
        if meta["codec"] not in settings["codecs"]:
            return False

    if settings["languages"] and meta["languages"]:
        if not any(lang in settings["languages"] for lang in meta["languages"]):
            return False

    for kw in settings["exclude_keywords"]:
        if kw in title_lower:
            return False

    for kw in settings["require_keywords"]:
        if kw not in title_lower:
            return False

    if meta["group"] and meta["group"].lower() in [
        g.lower() for g in settings["exclude_release_group"]
    ]:
        return False

    if result.get("size"):
        size_mb = int(result["size"]) / 1048576
        if settings["min_size"] > 0 and size_mb < settings["min_size"]:
            return False
        if settings["max_size"] > 0 and size_mb > settings["max_size"]:
            return False

    return True


def filter_results(results):
    """Apply all filters, sort, and truncate results."""
    settings = _get_filter_settings()

    total_in = len(results)
    filtered = []
    for result in results:
        meta = parse_title_metadata(result["title"])
        if matches_filters(result, meta, settings):
            result["_meta"] = meta
            filtered.append(result)

    filtered = _sort_results(filtered, settings)

    max_results = settings["max_results"]
    if max_results > 0:
        filtered = filtered[:max_results]

    xbmc.log(
        "NZB-DAV: Filtered {} -> {} results".format(total_in, len(filtered)),
        xbmc.LOGDEBUG,
    )
    return filtered


def _sort_results(results, settings):
    """Sort results by configured sort order, with preferred groups boosted.

    Sort orders:
        0 = Relevance (original order)
        1 = Size (largest first)
        2 = Size (smallest first)
        3 = Age (newest first) -- pubdate descending
        4 = Age (oldest first) -- pubdate ascending
    """
    preferred_lower = [g.lower() for g in settings["release_group"]]
    sort_order = settings["sort_order"]

    def _is_preferred(r):
        meta = r.get("_meta", {})
        return 0 if meta.get("group", "").lower() in preferred_lower else 1

    if sort_order == 1:
        # Largest first: negate size for ascending sort
        return sorted(
            results,
            key=lambda r: (_is_preferred(r), -int(r.get("size", 0) or 0)),
        )
    elif sort_order == 2:
        # Smallest first
        return sorted(
            results,
            key=lambda r: (_is_preferred(r), int(r.get("size", 0) or 0)),
        )
    elif sort_order == 3:
        # Newest first: reverse-sort by pubdate string (RFC 2822 dates
        # don't sort lexicographically, but this matches the original
        # behavior and works for same-format dates from a single indexer)
        return sorted(
            results,
            key=lambda r: (_is_preferred(r), r.get("pubdate", "")),
            reverse=True,
        )
    elif sort_order == 4:
        # Oldest first
        return sorted(
            results,
            key=lambda r: (_is_preferred(r), r.get("pubdate", "")),
        )
    else:
        # Relevance: preserve original order, preferred groups first
        return sorted(
            results,
            key=lambda r: (_is_preferred(r), results.index(r)),
        )
