"""
Native Desktop UI for DeskResumer.
Seamlessly uses PySide6 Native System Tray when available,
or built-in zero-dependency Native Tkinter dashboard.
"""

def run_native_app(config_path="config.yaml"):
    try:
        from .tray import run_native_app as run_pyside
        run_pyside(config_path)
    except ImportError:
        from .tk_window import run_native_tk
        run_native_tk(config_path)
