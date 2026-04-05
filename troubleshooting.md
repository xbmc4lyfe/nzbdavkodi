# NZB-DAV Kodi Addon - Troubleshooting Log

## Current Status: Two blocking errors in search results display

### Error 1: `No module named 'ptt'`
**Status:** Partially mitigated (fallback regex parser works, but PTT is preferred)

**Root cause:** When Kodi runs the addon, the Python path includes the addon root (`plugin.video.nzbdav/`) but NOT `plugin.video.nzbdav/resources/lib/`. The PTT library is at `resources/lib/ptt/` and its internal imports do `from ptt.handlers import ...` which fails because `resources/lib/` isn't on `sys.path`.

**In tests:** `conftest.py` adds both paths to `sys.path`, so PTT works fine in tests.

**In Kodi:** The addon entry point (`addon.py`) does `from resources.lib.router import route` which works because Kodi adds the addon root to the path. But PTT's internal imports need `resources/lib/` on the path.

**Fix needed:** Add `sys.path` modification in `addon.py`:
```python
import sys, os
addon_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(addon_dir, "resources", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
```

**Previous fix attempt:** `functools.cache` -> `lru_cache(maxsize=None)` fallback in `adult.py` (this was a separate Python 3.8 compat issue, now fixed).

---

### Error 2: `'xbmc.InfoTagVideo' object has no attribute 'setWidth'`
**Status:** Blocking - crashes the search results page

**Root cause:** Kodi 21.3 (Omega) on macOS does NOT have `setWidth()` on `InfoTagVideo`. The code in `router.py` `_display_results()` calls `info_tag.setWidth(width)` which throws `AttributeError` and kills the entire directory listing.

**Methods that DON'T exist:** `setWidth`, `setHeight`

**Methods that likely DO exist:** `setTitle`, `setPlot`, `addVideoStream`, `addAudioStream`

**Fix needed:** Replace `info_tag.setWidth()` with a try/except or use only `addVideoStream(xbmc.VideoStreamDetail(width=W, height=H, codec=C))` which bundles resolution info into the stream detail.

Also need to wrap ALL InfoTagVideo calls in try/except to be safe:
```python
try:
    info_tag = li.getVideoInfoTag()
    info_tag.setTitle(label)
    info_tag.setPlot(filename)
    # Use addVideoStream instead of setWidth
    info_tag.addVideoStream(xbmc.VideoStreamDetail(width=1920, height=1080, codec="hevc"))
    info_tag.addAudioStream(xbmc.AudioStreamDetail(channels=6, codec="dts"))
except Exception as e:
    xbmc.log("NZB-DAV: InfoTagVideo error: {}".format(e), xbmc.LOGDEBUG)
    # Fall back to deprecated setInfo
    li.setInfo("video", {"title": label, "plot": filename})
```

---

## Resolved Issues

### Zip install failure: `itemsize: 4, first item is folder: false`
**Resolution:** Multiple issues:
1. Zip needed `plugin.video.nzbdav/` as top-level folder (not files at root)
2. `.txt` files inside `ptt/keywords/` broke Kodi's zip VFS - renamed to `.dat`
3. Explicit directory entries in zip confused Kodi - removed them
4. After failed installs, Kodi caches the old zip and needs a restart

### Settings GUI not showing
**Resolution:**
- Settings v2 XML format (`<settings version="2">` with `<section>/<category>/<group>`) didn't render in Arctic Zephyr skin
- Switched to classic flat format (`<settings>` with `<category>/<setting>`) matching plugin.video.pov

### Settings not being saved / player install "no targets"
**Resolution:**
- Settings toggles weren't persisted when action button was clicked from same dialog
- Replaced settings-based target selection with `xbmcgui.Dialog().multiselect()` popup

### TMDBHelper not showing results
**Resolution:** Multiple iterations:
1. `is_resolvable: "true"` with directory listing didn't work (TMDBHelper expected `setResolvedUrl`)
2. `is_resolvable: "false"` didn't show directory either
3. `is_resolvable: "select"` not a valid TMDBHelper value
4. **Final fix:** Use `executebuiltin://RunPlugin(plugin://...)` pattern (same as POV addon) so the addon takes full control via `xbmc.Player().play()`

### `addon.py` `if __name__ == "__main__"` guard
**Resolution:** Kodi doesn't run addon scripts as `__main__`. Removed the guard so `route(sys.argv)` always runs.

### PTT `functools.cache` Python 3.8 incompatibility
**Resolution:** Added fallback: `from functools import cache` -> `lru_cache(maxsize=None)`

### Kodi freeze on playback stop
**Resolution:** `PlaybackMonitor.start_monitoring()` was blocking the script thread. Removed PlaybackMonitor calls - just play and return.

### WebDAV stream URL wrong path
**Resolution:** nzbdav serves files at `/content/{category}/{name}/{videofile}.mkv`, not at `/{nzb_title}`. Fixed by:
1. Polling nzbdav history API for `storage` path on completion
2. Converting storage path to WebDAV content path
3. Using PROPFIND to find the actual video file in the folder

### Overlapping lines in result list
**Status:** The `\n` character in labels causes overlapping in Kodi's list view. Newlines don't create proper two-line items. Need to use `label` + `label2` with `useDetails=True` in a `Dialog.select()`, OR use `setPlot()` on InfoTagVideo which some skins show as secondary text in directory listings.

---

## Architecture Notes

### Player JSON flow (TMDBHelper integration)
```
TMDBHelper -> executebuiltin://RunPlugin(plugin://plugin.video.nzbdav/play?...)
  -> _handle_play: shows progress bar, searches NZBHydra, caches results
  -> ActivateWindow(videos, plugin://plugin.video.nzbdav/search?..., return)
    -> _handle_search: creates full-screen directory listing
      -> User clicks item -> /resolve route
        -> resolve_and_play: submits to nzbdav, polls history, finds video via PROPFIND, plays
```

### Two-line display approach
The current skin (Arctic Zephyr mod) does NOT show `label2` in list view. Options:
1. `setPlot()` on InfoTagVideo - shown by some skins as plot text
2. Custom window XML (complex, skin-dependent)
3. Accept single-line with all info packed in

### Movie artwork
Using IMDB suggestion API (`v2.sg.media-imdb.com/suggestion/t/{imdb_id}.json`) to fetch poster URL. This works but adds ~0.5s latency to the search results page. The poster is set via `li.setArt({"thumb": url, "poster": url, "fanart": url})`.

---

## Test Environment
- Kodi 21.3 (Omega) on macOS ARM 64-bit
- Skin: Arctic Zephyr Mod
- Python: 3.x (exact version in Kodi TBD)
- nzbdav at <local-ip>:3333
- NZBHydra2 at <local-ip>:5076
