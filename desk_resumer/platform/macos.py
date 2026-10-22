"""
macOS implementation using CoreGraphics / CGEvent, caffeinate, and clipboard.
"""

import ctypes
import os
import subprocess
import time
from ctypes import c_bool, c_uint16, c_uint32, c_uint64, c_void_p
from typing import Optional
from .base import PlatformAdapter


class MacOSAdapter(PlatformAdapter):
    def __init__(self):
        self._caffeinate_process: Optional[subprocess.Popen] = None
        self._app_services = None
        self._core_foundation = None
        self._init_cgraphics()

    def _init_cgraphics(self):
        try:
            self._app_services = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
            self._core_foundation = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

            self._app_services.CGEventSourceCreate.restype = c_void_p
            self._app_services.CGEventSourceCreate.argtypes = [c_uint32]
            self._app_services.CGEventCreateKeyboardEvent.restype = c_void_p
            self._app_services.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint16, c_bool]
            self._app_services.CGEventSetFlags.restype = None
            self._app_services.CGEventSetFlags.argtypes = [c_void_p, c_uint64]
            self._app_services.CGEventPost.restype = None
            self._app_services.CGEventPost.argtypes = [c_uint32, c_void_p]
            self._core_foundation.CFRelease.argtypes = [c_void_p]
        except Exception as e:
            print(f"[MacOSAdapter] CGEvent init warning: {e}")

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
        """Activate the application window via open -a with AppleScript fallback."""
        try:
            res = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass

        script = f'tell application "{app_name}" to activate'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return res.returncode == 0

    def inject_text_and_submit(self, app_name: str, text: str) -> bool:
        """
        Activates the app, copies text to clipboard (to handle special characters cleanly),
        pastes it (Cmd+V), and hits Return using CoreGraphics CGEvent.
        """
        if not self.focus_app_window(app_name):
            return False

        time.sleep(0.6)

        # 1. Copy text to clipboard via pbcopy
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
        except Exception as e:
            print(f"[Error] Failed to copy to clipboard: {e}")
            return False

        # 2. Inject Cmd+V and Return via native CoreGraphics CGEvent
        if self._app_services and self._core_foundation:
            try:
                src = self._app_services.CGEventSourceCreate(1)  # kCGEventSourceStateHIDSystemState
                if src:
                    kCGEventFlagMaskCommand = 0x00100000

                    # Cmd + V (virtualKey 9)
                    v_down = self._app_services.CGEventCreateKeyboardEvent(src, 9, True)
                    self._app_services.CGEventSetFlags(v_down, kCGEventFlagMaskCommand)
                    self._app_services.CGEventPost(0, v_down)

                    v_up = self._app_services.CGEventCreateKeyboardEvent(src, 9, False)
                    self._app_services.CGEventSetFlags(v_up, kCGEventFlagMaskCommand)
                    self._app_services.CGEventPost(0, v_up)

                    self._core_foundation.CFRelease(v_down)
                    self._core_foundation.CFRelease(v_up)

                    time.sleep(0.35)

                    # Return (virtualKey 36)
                    ret_down = self._app_services.CGEventCreateKeyboardEvent(src, 36, True)
                    self._app_services.CGEventPost(0, ret_down)

                    ret_up = self._app_services.CGEventCreateKeyboardEvent(src, 36, False)
                    self._app_services.CGEventPost(0, ret_up)

                    self._core_foundation.CFRelease(ret_down)
                    self._core_foundation.CFRelease(ret_up)
                    self._core_foundation.CFRelease(src)
                    return True
            except Exception as e:
                print(f"[MacOSAdapter] CGEvent injection warning: {e}, attempting AppleScript fallback")

        # Fallback to AppleScript System Events if CGEvent unavailable
        applescript = f'''
        tell application "System Events"
            tell process "{app_name}"
                set frontmost to true
                keystroke "v" using command down
                delay 0.5
                key code 36
            end tell
        end tell
        '''
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        if res.returncode != 0:
            err = res.stderr.strip()
            print(f"[MacOSAdapter] Keystroke injection error: {err}")
            return False
        return True

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
