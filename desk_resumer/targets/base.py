"""
Base interface for desktop application targets.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from ..platform.base import PlatformAdapter
from ..core.parser import CooldownParser


class TargetApp(ABC):
    def __init__(self, platform_adapter: PlatformAdapter):
        self.adapter = platform_adapter

    @property
    @abstractmethod
    def name(self) -> str:
        """Friendly name of the application."""
        pass

    @property
    @abstractmethod
    def process_names(self) -> list[str]:
        """Process names to search for across OS platforms."""
        pass

    def is_running(self) -> bool:
        """Check if any of the process names are currently running."""
        return any(self.adapter.is_process_running(p) for p in self.process_names)

    BUSY_KEYWORDS = [
        "working for",
        "thinking",
        "generating",
        "compacting context",
        "in progress",
    ]

    def is_busy(self) -> bool:
        """Checks if the application is currently actively working on a prompt."""
        window_text = self.adapter.get_window_text_content(self.name)
        if not window_text:
            return False
        text_lower = window_text.lower()
        return any(kw in text_lower for kw in self.BUSY_KEYWORDS)

    def check_status(self) -> Tuple[bool, int, Optional[str]]:
        """
        Inspects application window for rate limit status.
        Returns:
            (is_limited, wait_seconds, description)
        """
        window_text = self.adapter.get_window_text_content(self.name)
        if not window_text:
            return False, 0, None
        return CooldownParser.extract_cooldown_seconds(window_text)

    def resume_task(self, prompt: str) -> bool:
        """Focus the application and inject the continuation prompt."""
        return self.adapter.inject_text_and_submit(self.name, prompt)

