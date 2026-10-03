"""
Windows implementation using Win32 API, SetThreadExecutionState, and UI Automation.
"""

import sys
import time
from typing import Optional
from .base import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    def __init__(self):
        self._es_continuous = 0x80000000
        self._es_system_required = 0x00000001
        self._es_awaymode_required = 0x00000040
        self._es_display_required = 0x00000002

    def is_process_running(self, process_name: str) -> bool:
        """Check if process is running via psutil."""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    return True
        except Exception:
            pass
        return False

    def focus_app_window(self, app_name: str) -> bool:
        """Find and bring window to the front using pywinauto."""
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            window = desktop.window(title_re=f".*{app_name}.*")
            if window.exists():
                window.set_focus()
                return True
        except Exception as e:
            print(f"[Windows] Could not focus window for {app_name}: {e}")
        return False

    def inject_text_and_submit(self, app_name: str, text: str) -> bool:
        """Focus the window, paste the text into the active input, and press Enter."""
        try:
            from pywinauto import Desktop
            import pywinauto.keyboard as keyboard
            import subprocess

            if not self.focus_app_window(app_name):
                return False

            time.sleep(1.0)

            # Copy text to clipboard via clip
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-16"))

            # Paste with Ctrl+V and send Return
            keyboard.send_keys("^v")
            time.sleep(0.5)
            keyboard.send_keys("{ENTER}")
            return True
        except Exception as e:
            print(f"[Windows] Text injection failed: {e}")
            return False

    def get_window_text_content(self, app_name: str) -> Optional[str]:
        """Extract visible text from the UI tree using UIA."""
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            window = desktop.window(title_re=f".*{app_name}.*")
            if window.exists():
                texts = window.texts()
                return " ".join([t for t in texts if t.strip()])
        except Exception:
            pass
        return None

    def start_wake_lock(self, duration_seconds: int, keep_display_on: bool = False):
        """
        Prevents Windows from entering sleep or suspension using SetThreadExecutionState.
        """
        if sys.platform != "win32":
            return

        import ctypes
        flags = self._es_continuous | self._es_system_required | self._es_awaymode_required
        if keep_display_on:
            flags |= self._es_display_required

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
            print("[Power] Windows SetThreadExecutionState lock acquired.")
        except Exception as e:
            print(f"[Power] Failed to set thread execution state: {e}")

    def stop_wake_lock(self):
        """Reset execution state to default continuous."""
        if sys.platform != "win32":
            return

        import ctypes
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(self._es_continuous)
            print("[Power] Windows wake-lock released.")
        except Exception:
            pass
