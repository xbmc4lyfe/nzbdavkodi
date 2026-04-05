# NZB-DAV Kodi Addon

# Run all tests
test:
    python3 -m pytest tests/ -v --tb=short

# Run tests with coverage
test-verbose:
    python3 -m pytest tests/ -v --tb=long

# Lint the codebase
lint:
    ruff check plugin.video.nzbdav/ tests/ --exclude="plugin.video.nzbdav/resources/lib/ptt/"
    black --check plugin.video.nzbdav/ tests/ --exclude="ptt/"

# Auto-fix lint issues
lint-fix:
    ruff check plugin.video.nzbdav/ tests/ --exclude="plugin.video.nzbdav/resources/lib/ptt/" --fix
    black plugin.video.nzbdav/ tests/ --exclude="ptt/"

# Build the addon zip for Kodi installation
release:
    #!/usr/bin/env python3
    import zipfile, os, time
    zip_path = "plugin.video.nzbdav.zip"
    addon_dir = "plugin.video.nzbdav"
    skip_dirs = {"__pycache__", ".pytest_cache"}
    skip_files = {".DS_Store"}
    skip_ext = {".pyc"}
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Walk and collect all directories and files
        for root, dirs, files in os.walk(addon_dir):
            dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
            # Add explicit directory entry (Kodi requires these)
            dir_entry = root.replace(os.sep, "/") + "/"
            zf.mkdir(dir_entry.rstrip("/"))
            for f in sorted(files):
                if f in skip_files or os.path.splitext(f)[1] in skip_ext:
                    continue
                filepath = os.path.join(root, f)
                arcname = filepath.replace(os.sep, "/")
                zf.write(filepath, arcname)
    # Verify structure
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        first = names[0] if names else ""
        assert first == "plugin.video.nzbdav/", "Bad zip: first entry is " + repr(first)
    size = os.path.getsize(zip_path)
    print("Created {} ({} entries, {:.0f} KB)".format(zip_path, len(names), size/1024))
    print("First entry: " + repr(first))
    print("Install in Kodi: Settings > Add-ons > Install from zip file")

# Run tests then build release
ship: test release

# Clean build artifacts
clean:
    rm -f plugin.video.nzbdav.zip
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
