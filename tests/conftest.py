"""Mock Kodi modules for testing outside of Kodi."""

import sys
from unittest.mock import MagicMock

# Mock all xbmc* modules that Kodi provides at runtime
for module_name in ["xbmc", "xbmcgui", "xbmcplugin", "xbmcaddon", "xbmcvfs"]:
    sys.modules[module_name] = MagicMock()

# Add plugin.video.nzbdav to the path so imports work
sys.path.insert(0, "plugin.video.nzbdav")
# Add resources/lib so PTT's internal imports resolve
sys.path.insert(0, "plugin.video.nzbdav/resources/lib")
