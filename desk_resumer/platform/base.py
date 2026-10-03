"""
Abstract base class for platform-specific OS interactions.
"""

from abc import ABC, abstractmethod
from typing import Optional


class PlatformAdapter(ABC):
    """
    Abstract platform adapter defining how DeskResumer interacts
    with the host operating system (macOS, Windows, etc.).
    """

    @abstractmethod
    def is_process_running(self, process_name: str) -> bool:
        """Check if an application process is currently running."""
        pass

    @abstractmethod
    def focus_app_window(self, app_name: str) -> bool:
        """Bring the application window to the foreground."""
        pass

    @abstractmethod
    def inject_text_and_submit(self, app_name: str, text: str) -> bool:
        """Focus the input area, paste/type the given text, and send return/submit."""
        pass

    @abstractmethod
    def get_window_text_content(self, app_name: str) -> Optional[str]:
        """Inspect and return UI text elements from the active window if accessible."""
        pass

    @abstractmethod
    def start_wake_lock(self, duration_seconds: int, keep_display_on: bool = False):
        """Prevent the OS from sleeping for the specified duration."""
        pass

    @abstractmethod
    def stop_wake_lock(self):
        """Release any active sleep inhibition."""
        pass
