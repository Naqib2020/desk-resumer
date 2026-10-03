"""
Platform factory returning the appropriate OS adapter.
"""

import sys
from .base import PlatformAdapter


def get_platform_adapter() -> PlatformAdapter:
    """Detect current OS and instantiate the corresponding PlatformAdapter."""
    if sys.platform == "darwin":
        from .macos import MacOSAdapter
        return MacOSAdapter()
    elif sys.platform == "win32":
        from .windows import WindowsAdapter
        return WindowsAdapter()
    else:
        raise NotImplementedError(f"Unsupported operating system: {sys.platform}")
