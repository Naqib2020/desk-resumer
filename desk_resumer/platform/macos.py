"""
macOS implementation using AppleScript, caffeinate, and System Events.
"""

import subprocess
import time
from typing import Optional
from .base import PlatformAdapter


class MacOSAdapter(PlatformAdapter):
    def __init__(self):
        self._caffeinate_process: Optional[subprocess.Popen] = None

    def is_process_running(self, process_name: str) -> bool:
        """Check if process exists using pgrep."""
        try:
            res = subprocess.run(
                ["pgrep", "-if", process_name],
                capture_output=True,
                text=True,
            )
            return res.returncode == 0
        except Exception:
            return False

    def focus_app_window(self, app_name: str) -> bool:
        """Activate the application window via AppleScript."""
        script = f'tell application "{app_name}" to activate'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return res.returncode == 0

    def inject_text_and_submit(self, app_name: str, text: str) -> bool:
        """
        Activates the app, copies text to clipboard (to handle special characters cleanly),
        pastes it (Cmd+V), and hits Return.
        """
        if not self.focus_app_window(app_name):
            return False

        time.sleep(1.0)

        # 1. Copy text to clipboard via pbcopy
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
        except Exception as e:
            print(f"[Error] Failed to copy to clipboard: {e}")
            return False

        # 2. Paste and hit Return using AppleScript System Events
        applescript = f'''
        tell application "System Events"
            tell process "{app_name}"
                set frontmost to true
                -- Send Cmd+V to paste the prompt
                keystroke "v" using command down
                delay 0.5
                -- Send Return to execute
                key code 36
            end tell
        end tell
        '''
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        return res.returncode == 0

    def get_window_text_content(self, app_name: str) -> Optional[str]:
        """
        Query window text using AppleScript Accessibility.
        Extracts static texts and values from the frontmost window.
        """
        applescript = f'''
        tell application "System Events"
            if exists process "{app_name}" then
                tell process "{app_name}"
                    try
                        set win to window 1
                        set allTexts to value of every static text of win
                        return allTexts as string
                    on error
                        return ""
                    end try
                end tell
            else
                return ""
            end if
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def start_wake_lock(self, duration_seconds: int, keep_display_on: bool = False):
        """
        Prevents sleep using macOS 'caffeinate'.
        If keep_display_on is False, allows display sleep while keeping system, disk, and idle awake.
        """
        self.stop_wake_lock()  # Stop any prior lock

        flags = ["-imsu"]
        if keep_display_on:
            flags.append("-d")

        cmd = ["caffeinate"] + flags + ["-t", str(int(duration_seconds))]
        try:
            self._caffeinate_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[Power] macOS caffeinate wake-lock started (PID: {self._caffeinate_process.pid}, duration: {duration_seconds}s)")
        except Exception as e:
            print(f"[Power] Failed to start caffeinate: {e}")

    def stop_wake_lock(self):
        """Terminates active caffeinate process if running."""
        if self._caffeinate_process and self._caffeinate_process.poll() is None:
            try:
                self._caffeinate_process.terminate()
                self._caffeinate_process.wait(timeout=2)
                print("[Power] macOS wake-lock released.")
            except Exception:
                self._caffeinate_process.kill()
            finally:
                self._caffeinate_process = None
