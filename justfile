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
    import zipfile, os
    zip_path = "plugin.video.nzbdav.zip"
    addon_dir = "plugin.video.nzbdav"
    skip_dirs = {"__pycache__", ".pytest_cache"}
    skip_files = {".DS_Store"}
    skip_ext = {".pyc"}
    FILE_ATTR = 0o100644 << 16  # Unix rw-r--r-- (matches Kodi repo format)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
            for f in sorted(files):
                if f in skip_files or os.path.splitext(f)[1] in skip_ext:
                    continue
                filepath = os.path.join(root, f)
                arcname = filepath.replace(os.sep, "/")
                info = zipfile.ZipInfo(arcname)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = FILE_ATTR
                with open(filepath, "rb") as fh:
                    zf.writestr(info, fh.read())
    size = os.path.getsize(zip_path)
    entries = len(zipfile.ZipFile(zip_path).namelist())
    print("Created {} ({} entries, {:.0f} KB)".format(zip_path, entries, size/1024))
    print("Install in Kodi: Settings > Add-ons > Install from zip file")

# Run tests then build release
ship: test release

# Clean build artifacts
clean:
    rm -f plugin.video.nzbdav.zip
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
