# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 nzbdav contributors

"""Error-path tests for cache module.

These tests cover filesystem and JSON corruption scenarios encountered by
users whose cache directory contains stale or damaged files.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from resources.lib.cache import get_cached, set_cached


@patch("resources.lib.cache._get_cache_dir")
@patch("resources.lib.cache.xbmcaddon")
def test_cache_read_handles_corrupted_json(mock_addon_mod, mock_cache_dir):
    """Reading a corrupted cache file should return None, not raise JSONDecodeError.

    User scenario: the device lost power mid-write, leaving a partially written
    (or zero-length) cache file on disk.  The next time the addon starts, reading
    that file raises json.JSONDecodeError.  get_cached() must silently return None
    so the addon falls back to a live search rather than crashing.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_cache_dir.return_value = tmpdir
        addon = MagicMock()
        addon.getSetting.return_value = "300"
        mock_addon_mod.Addon.return_value = addon

        # First write a valid cache entry so the key/path are established
        set_cached("movie", "Corrupted Movie", [{"title": "Corrupted Movie"}])

        # Now corrupt the cache file that was just written
        from resources.lib.cache import _cache_key

        key = _cache_key("movie", "Corrupted Movie")
        cache_path = os.path.join(tmpdir, key + ".json")
        assert os.path.exists(cache_path), "Cache file should exist after set_cached()"

        with open(cache_path, "w") as f:
            f.write("{ this is not valid json !!!")

        # get_cached must not raise and must return None
        result = get_cached("movie", "Corrupted Movie")

        assert (
            result is None
        ), "get_cached() must return None when the cache file contains invalid JSON"
