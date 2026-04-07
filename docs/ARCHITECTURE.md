# NZB-DAV Architecture

End-to-end flow for TMDBHelper → NZBHydra2 → nzbdav → Kodi playback, including what data moves between layers, where caching happens, and how failures are handled.

## Data Flow

### 1. Search Phase (`router._handle_play`)
- **Inputs:** TMDBHelper plugin URL (`plugin://plugin.video.nzbdav/play`), containing title/year/IMDB/season/episode params (placeholders `_` are cleaned to empty strings).
- **Lookup / enrichment:** Falls back to Kodi InfoLabels for missing season/episode and optionally looks up a title from IMDB if only an ID is provided.
- **Cache read:** `cache.get_cached()` loads JSON results from the addon profile cache if still fresh (TTL from `cache_ttl`, default 300s, capped at 50MB total with oldest-eviction).
- **Remote search:** On cache miss, `hydra.search_hydra()` calls NZBHydra2’s Newznab API. If an IMDB search returns nothing it retries once with a title search. Network/parse errors surface a notification and stop resolution.
- **Cache write:** Successful results are persisted via `cache.set_cached()` (same keying as the read).
- **Filter & present:** `filter.filter_results()` applies quality/keyword constraints. Optional auto-select picks the top result; otherwise `results_dialog.show_results_dialog()` displays the list (tagging items already completed in nzbdav history).

### 2. Download Phase (`resolver.resolve` and `resolve_and_play`)
- **Skip if already done:** `nzbdav_api.find_completed_by_name()` checks nzbdav history; if found, `webdav.find_video_file()` locates the video and playback starts immediately.
- **Submit to nzbdav:** `nzbdav_api.submit_nzb()` posts the NZB URL (up to 3 attempts with 2s waits via `xbmc.Monitor.waitForAbort`). Failure after 3 tries notifies the user and aborts.
- **Polling loop:** Polls every `poll_interval` seconds (default 5) until `download_timeout` (default 3600s) or user cancel:
  - `get_job_status()` (queue) and `get_job_history()` (history) run in parallel each iteration.
  - If both are empty, `webdav.check_file_available_with_retry(title, max_retries=1, retry_delay=1)` distinguishes auth/server/connection errors.
  - Queue statuses drive the progress dialog; `Failed`/`Deleted` status or history `Failed` stops with a notification.
- **Completion:** On history `Completed`, `_storage_to_webdav_path()` maps nzbdav storage → WebDAV path, `webdav.find_video_file()` picks the largest video, then `get_webdav_stream_url_for_path()` builds the stream URL + auth headers. A HEAD-based range validation is attempted before playback starts.
- **Timeouts & aborts:** Exceeding `download_timeout`, hitting the hard poll cap (`MAX_POLL_ITERATIONS`), or dialog cancellation all terminate with `setResolvedUrl(False)` so Kodi does not hang waiting for a stream.

### 3. Playback Phase (`service.py`, `stream_proxy.py`)
- **MP4 remux path:** `_play_direct()` routes MP4/M4V through the background `StreamProxy` service. The proxy probes size (HEAD/range) and duration (ffmpeg `Duration:` parse) and, if ffmpeg is available, remuxes to MKV on the fly with `-c copy` and optional subtitle conversion. Each GET supports range-based seeks by restarting ffmpeg at the calculated timestamp; network breakages simply cause a new GET/remux on reconnect.
- **Direct proxy path:** MKV/other formats bypass remux and proxy HTTP range requests straight to WebDAV with 206 responses.
- **Service hand-off:** Resolver sets window properties (`nzbdav.stream_url`, `...stream_title`, `...active`) for the always-on `NzbdavPlayer` in `service.py`. The service also owns the proxy so it survives beyond the short-lived plugin script.
- **Playback retries:** `NzbdavPlayer` watches for `onPlayBackError` and, if `stream_auto_retry` is enabled (default true), retries up to `stream_max_retries` (default 3) with `stream_retry_delay` seconds between attempts, resuming from the last known timestamp via `StartOffset`. If retries are exhausted it notifies the user.
- **Alternate path:** `resolve_and_play()` (used when invoked via `RunPlugin` instead of directory playback) starts playback via `xbmc.Player()` and can be paired with the standalone `PlaybackMonitor` class for on-demand retry logic when the service context is unavailable.

## Key Design Decisions

- **MP4 remux via ffmpeg:** Kodi’s 32-bit `CFileCache` struggles with large MP4 moov atoms over HTTP. Remuxing MP4 to MKV locally (no re-encode) avoids that parsing path, preserves quality, and enables reliable seeking and subtitle conversion before sending bytes to Kodi.
- **Two Player subclasses:** `NzbdavPlayer` lives in the long-running service to monitor any stream launched via `setResolvedUrl`, keeping retry state and the proxy alive across script lifetimes. `PlaybackMonitor` is a lightweight, request-scoped helper for contexts where the service may not be running (e.g., direct `RunPlugin` entry points or testing).
- **Two resolve entry points:** `resolve()` (via `/play`) uses `setResolvedUrl` because Kodi directory handlers require it to attach the stream to the current list item. `resolve_and_play()` (via `/resolve` or `RunPlugin`) plays immediately with `xbmc.Player()` for cases where no directory handle exists, reusing the same submission/polling logic.
