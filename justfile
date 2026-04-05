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
    #!/usr/bin/env bash
    set -euo pipefail
    rm -f plugin.video.nzbdav.zip
    cd plugin.video.nzbdav && zip -r ../plugin.video.nzbdav.zip . \
        -x "*.pyc" \
        -x "*__pycache__*" \
        -x "*.pytest_cache*" \
        -x ".DS_Store"
    echo ""
    echo "Created plugin.video.nzbdav.zip"
    echo "Install in Kodi: Settings > Add-ons > Install from zip file"

# Run tests then build release
ship: test release

# Clean build artifacts
clean:
    rm -f plugin.video.nzbdav.zip
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
