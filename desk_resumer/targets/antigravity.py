"""
Antigravity Desktop application target.
"""

from .base import TargetApp


class AntigravityTarget(TargetApp):
    @property
    def name(self) -> str:
        return "Antigravity"

    @property
    def process_names(self) -> list[str]:
        return ["Antigravity", "Antigravity.exe", "antigravity"]
