# NZB-DAV Architecture Guide

This document describes how the addon works end-to-end: what data flows between components at each stage, where caching occurs, how retries work, and what happens when things go wrong.

---

## System Overview

```
TMDBHelper ──plugin://──► router.py
                              │
                    ┌─────────┴──────────┐
                    │   Search Phase      │
                    │  hydra.py           │
                    │  cache.py           │
                    │  filter.py          │
                    │  results_dialog.py  │
                    └─────────┬──────────┘
                              │ user picks NZB
                    ┌─────────┴──────────┐
                    │  Download Phase     │
                    │  resolver.py        │
                    │  nzbdav_api.py      │
                    │  webdav.py          │
                    └─────────┬──────────┘
                              │ stream URL ready
                    ┌─────────┴──────────┐
                    │  Playback Phase     │
                    │  stream_proxy.py    │
                    │  playback_monitor.py│
                    └─────────────────────┘
```

---

## Phase 1 — Search (`router._handle_play`)

### Entry point

TMDBHelper calls the addon via a `plugin://` URL. `addon.py` passes `sys.argv` to `router.route()`, which dispatches to `_handle_play()` for the `/play` path.

### Parameter extraction

`_handle_play` reads the following from the query string:

| Parameter | Source | Used for |
|-----------|--------|----------|
| `title` | TMDBHelper | Search query |
| `year` | TMDBHelper | Cache key / UI context; not currently sent to NZBHydra2 to narrow results |
| `imdb` | TMDBHelper | Preferred IMDB-based search |
| `season` / `episode` | TMDBHelper or Kodi InfoLabels | TV episode lookup |
| `type` | TMDBHelper | `"movie"` or `"episode"` |

If season/episode are missing, the router falls back to reading Kodi InfoLabels (`ListItem.Season`, `VideoPlayer.Season`, etc.) from multiple container sources. If title is still missing and an IMDB ID was provided, `_lookup_episode_info()` queries the IMDB suggestion API.

### Cache check (`cache.py`)

Before hitting NZBHydra2, `get_cached()` checks for a previously stored result:

- **Key**: filesystem-safe hash of `(search_type, title, year, imdb, season, episode)`.
- **Storage**: JSON files under the Kodi addon profile directory (`special://profile/addon_data/plugin.video.nzbdav/cache/`).
- **TTL**: Configurable (default 300 s). Entries older than the TTL are ignored.
- **Max size**: 50 MB. When exceeded, the oldest files are evicted.
- **Disable**: Set `cache_ttl = 0` in settings to bypass the cache entirely.

A cache **hit** skips the NZBHydra2 request and jumps straight to filtering.

### NZBHydra2 search (`hydra.py`)

On a cache miss, `search_hydra()` sends a Newznab API request:

- Movie: `GET /api?t=movie&imdbid=<id>&apikey=<key>&o=xml`
- TV: `GET /api?t=tvsearch&imdbid=<id>&season=<s>&ep=<e>&apikey=<key>&o=xml`
- Title-only fallback: `q=<title>` instead of `imdbid=` when no IMDB ID is available.
- Automatic fallback: if IMDB search returns zero results, retries with a title query.

The response is Newznab-flavoured RSS/XML. `parse_results()` extracts each `<item>` into a list of dicts containing:

```python
{
    "title":   str,   # release name
    "link":    str,   # NZB download URL
    "size":    int,   # bytes
    "age":     int,   # days since post
    "indexer": str,   # indexer name from Newznab attr
    "grabs":   int,   # download count
}
```

**Network failures**: a `URLError` returns `([], "Search failed: …")`. The caller shows a notification and calls `setResolvedUrl(handle, False, …)` so Kodi does not hang.

### Cache write

On a successful search with results, `set_cached()` writes the list to disk. The file is written before filtering so that re-opening the dialog (e.g., user presses back) reuses the same NZBHydra2 response.

### Filtering (`filter.py`)

`filter_results()` passes each result title through the vendored PTT (parse-torrent-title) library to extract structured metadata (resolution, codec, audio, HDR, release group, etc.). Results are then filtered against the user's quality preferences (resolution, HDR, audio, codec, language, keyword includes/excludes, and file-size bounds).

Filtered results are sorted by configurable criteria (relevance, size, age). Under relevance sort, the priority order is: resolution → HDR → preferred group → audio → size.

If **all** results are filtered out, the user is offered a "Show unfiltered?" dialog.

### Selection

- **Auto-select**: If `auto_select_best = true`, the top filtered result is selected automatically and the dialog is skipped.
- **Results dialog** (`results_dialog.py`): A full-screen custom Kodi dialog shows each result with colour-coded quality labels. The user presses **Enter** to select, **Esc** to cancel.

Already-downloaded titles are tagged `_available = True` by checking the nzbdav completed-history API before the dialog opens.

---

## Phase 2 — Download/Resolve (`resolver.py`)

### Two resolve paths

There are two entry points depending on how the user reached the selection:

| Function | Called when | Plays via |
|----------|-------------|-----------|
| `resolve(handle, params)` | User selects from the results dialog (TMDBHelper pipeline) | `xbmcplugin.setResolvedUrl()` |
| `resolve_and_play(nzb_url, title)` | `/resolve` route (direct deep-link) | `xbmc.Player().play()` |

Both share the same polling logic (`_poll_once`, `_resolve_inner` / `_resolve_and_play_inner`).

**Why two paths?** `setResolvedUrl` is the Kodi-recommended API for resolver addons: it lets Kodi own the playback handle, hooks up the info overlay, and integrates with the TMDBHelper queue. `xbmc.Player().play()` is used for the direct `/resolve` route where there is no active plugin handle.

### Already-downloaded shortcut

Before submitting the NZB, `find_completed_by_name()` queries nzbdav's history API. If the title is already present (exact name match), the addon skips downloading and streams directly from the existing WebDAV path.

### NZB submission (`nzbdav_api.submit_nzb`)

The NZB URL is submitted to nzbdav's SABnzbd-compatible API:

```
GET /api?mode=addurl&name=<nzb_url>&nzbname=<title>&apikey=<key>&output=json
```

On success, nzbdav returns a JSON body with `nzo_ids: ["<id>"]`.

**Retries**: Up to **3 attempts** with a 2-second wait between each. On all failures, the user sees an error notification and `setResolvedUrl(handle, False, …)` is called.

### Polling loop

After submission, the addon polls until the download completes or a terminal error occurs:

```
while True:
    check queue API  ──► job_status  (Queued/Fetching/Downloading/…/Failed)
    check history API ► history     (None / Completed / Failed)
    (both run in parallel threads)

    on Completed → find_video_file() → play
    on Failed    → notify + abort
    on cancelled → abort
    on timeout   → notify + abort
    else         → waitForAbort(poll_interval) and loop
```

**Poll interval**: configurable (default 5 s).  
**Download timeout**: configurable (default 3600 s).  
**Max iterations**: hard cap of 720 (1 hour at 5 s intervals).

Both the queue API and history API calls run in **parallel threads** (joined with a 10-second timeout each) to halve the polling latency.

#### Queue API (`nzbdav_api.get_job_status`)

```
GET /api?mode=queue&nzo_ids=<id>&apikey=<key>&output=json
```

Returns per-job status strings: `Queued`, `Fetching`, `Propagating`, `Downloading`, `Paused`, `Failed`, `Deleted`.

#### History API (`nzbdav_api.get_job_history`)

```
GET /api?mode=history&nzo_ids=<id>&apikey=<key>&output=json
```

Returns `{"status": "Completed"|"Failed", "storage": "/mnt/nzbdav/completed-symlinks/…", "name": "…"}` once the job moves to history.

### WebDAV file discovery (`webdav.find_video_file`)

Once the history API reports `Completed`, the storage path is converted to a WebDAV content path:

```
/mnt/nzbdav/completed-symlinks/uncategorized/Name  →  /content/uncategorized/Name/
```

`find_video_file()` issues a WebDAV `PROPFIND` request on that folder, parses the XML response, and returns the path of the largest video file (`.mkv`, `.mp4`, `.avi`, etc.) found in the directory tree.

**Network failures during polling**: if both queue and history return `None` in the same poll cycle, the addon probes the WebDAV server with a single HEAD request. This distinguishes authentication failures (`401` → terminal error, abort) from transient server errors (`5xx` → log warning, continue polling on next cycle).

---

## Phase 3 — Playback (`stream_proxy.py`, `playback_monitor.py`)

### MP4 remux via stream proxy

MP4 files trigger a special code path because of a Kodi 32-bit `CFileCache` bug: when Kodi tries to parse a large MP4 moov atom over HTTP, the file cache overflows and reports "corrupted STCO atom" errors.

**Workaround**: the `StreamProxy` HTTP server (started by `service.py` on addon startup) remuxes MP4 to MKV on the fly using ffmpeg with stream copy — no re-encoding. MKV containers use a linear header that Kodi can stream without needing to read the moov atom first.

```
Kodi ──HTTP GET /stream──► StreamProxy (localhost:<port>)
                                │
                          ffmpeg -i <webdav_url> \
                                 -c:v copy \
                                 -c:a copy \
                                 -c:s srt \
                                 -f matroska pipe:1
                                │
                          streams MKV bytes back to Kodi
```

The proxy runs as a `ThreadingHTTPServer` so multiple seek requests can be handled concurrently.

#### Duration probe and seeking

When Kodi seeks (byte-range request past `_SEEK_THRESHOLD`), the proxy:

1. **Probes** the source MP4 duration once using `ffmpeg -i <url> 2>&1` (reads only the moov atom, exits immediately).
2. **Calculates** the time offset: `timestamp = (byte_offset / estimated_bitrate)` using the file size and duration.
3. **Restarts** ffmpeg with `-ss <timestamp>` to begin output at the requested position.

#### Subtitle conversion

By default, MP4 `mov_text` subtitle tracks are converted to SRT for MKV compatibility (`-c:s srt`). This can be disabled in settings (`proxy_convert_subs = false`), in which case subtitle streams are dropped.

#### Graceful fallback

If ffmpeg is not installed (checked via `shutil.which` across common CoreELEC/LibreELEC paths), MP4 files fall back to direct WebDAV playback with no remux and no seeking support.

### MKV and other formats

Non-MP4 files bypass the proxy entirely. The WebDAV URL is passed directly to Kodi with a `|Authorization=Basic …` pipe-separated header suffix. `li.setContentLookup(False)` prevents Kodi from issuing a HEAD request (nzbdav does not advertise `Accept-Ranges` on HEAD, which would break `CFileCache`).

### Playback monitoring (`playback_monitor.py`)

If `stream_auto_retry = true` in settings, `PlaybackMonitor` (a `xbmc.Player` subclass) wraps playback:

- Hooks `onAVStarted`, `onPlayBackStopped`, `onPlayBackEnded`, `onPlayBackError`.
- On `onPlayBackError`, saves the current position and retries up to `max_retries` times (default 3) with a `retry_delay`-second pause between attempts.
- Resumes from the last saved position using `ListItem.setProperty("StartOffset", …)`.
- After `max_retries` failures, shows a notification and gives up.

**Why a `xbmc.Player` subclass instead of `NzbdavPlayer`?** `PlaybackMonitor` is only responsible for error recovery and position tracking — it does not need to intercept item resolution. `NzbdavPlayer` (if it existed) would be the resolver hook; these concerns are kept separate.

---

## Retry Summary

| Layer | Retries | Delay | Terminal condition |
|-------|---------|-------|-------------------|
| NZB submit (`submit_nzb`) | 3 | 2 s | All 3 fail → error notification + abort |
| Poll cycle | Up to 720 × poll_interval | configurable (default 5 s) | Timeout, `Failed`/`Deleted` status, auth error, user cancel |
| WebDAV probe | 1 (error detection only) | — | `401` → abort; `5xx` → continue |
| Stream retry (`PlaybackMonitor`) | 3 (if enabled) | 5 s | After 3 playback errors → notification |

---

## Key Design Decisions

### Why ffmpeg remux for MP4?

Kodi's `CFileCache` implementation is compiled as a 32-bit process on some platforms (notably older CoreELEC/LibreELEC builds). When it caches an HTTP response, the internal buffer can overflow while seeking to parse the MP4 moov atom if it is large (several MB at the end of the file). The resulting error (`corrupted STCO atom`) is a Kodi bug, not a server issue. Remuxing to MKV eliminates the problem because MKV uses a sequential seek header.

### Why two Player subclasses?

The codebase separates playback concerns:

- **`resolver.py`** handles the resolve pipeline (NZB submission, polling, stream URL construction). It calls either `setResolvedUrl` or `xbmc.Player().play()`.
- **`PlaybackMonitor`** handles post-playback concerns (error detection, retry, position tracking). It is only instantiated when `stream_auto_retry` is enabled.

Combining them would couple the resolver's polling logic with the player's event callbacks, making both harder to test and maintain.

### Why are there two resolve paths (`resolve` vs `resolve_and_play`)?

- **`resolve(handle, params)`** is used when TMDBHelper calls the addon via a plugin URL. It must call `xbmcplugin.setResolvedUrl()` to fulfil the Kodi resolver contract; omitting this call causes Kodi to hang indefinitely waiting for resolution.
- **`resolve_and_play(nzb_url, title)`** is used for the `/resolve` deep-link path (e.g., direct NZB links, context menu actions) where there is no active plugin handle. It calls `xbmc.Player().play()` directly.

Both paths share the same submission and polling logic to avoid duplication.

### Why is PTT vendored?

PTT (parse-torrent-title) is a pure-Python parsing library. It was vendored (`resources/lib/ptt/`) rather than declared as a Kodi addon dependency for two reasons:

1. Kodi's Python environment does not include `pip`, so addon dependencies must be bundled.
2. The upstream library uses the third-party `regex` and `arrow` packages. The vendored copy replaces `regex` with the standard `re` module and `arrow` with `datetime` so no compiled C extensions are needed — a requirement for ARM64 CoreELEC targets.

---

## Module Reference

| Module | Responsibility |
|--------|---------------|
| `addon.py` | Entry point; calls `router.route(sys.argv)` |
| `service.py` | Background service: starts `StreamProxy`, runs `PlaybackMonitor` |
| `router.py` | URL dispatcher for all `plugin://` paths |
| `hydra.py` | NZBHydra2 Newznab API client (search, XML parsing) |
| `nzbdav_api.py` | nzbdav SABnzbd-compatible API (submit, queue, history) |
| `webdav.py` | WebDAV HEAD/PROPFIND, file discovery, auth header builder |
| `resolver.py` | Submit → poll → play orchestration (both resolve paths) |
| `filter.py` | PTT parsing + quality/keyword filtering + relevance sort |
| `results_dialog.py` | Full-screen Kodi dialog for NZB selection |
| `stream_proxy.py` | Local HTTP server; MP4→MKV remux via ffmpeg, range proxy |
| `playback_monitor.py` | `xbmc.Player` subclass; stream error detection and retry |
| `cache.py` | JSON file cache with TTL and LRU eviction |
| `player_installer.py` | Writes `nzbdav.json` player file into TMDBHelper |
| `http_util.py` | `http_get()`, `notify()`, `redact_url()` shared utilities |
| `i18n.py` | Localisation helpers (`string()`, `fmt()`, `addon_name()`) |
| `ptt/` | Vendored parse-torrent-title (no `regex`/`arrow` dependency) |
