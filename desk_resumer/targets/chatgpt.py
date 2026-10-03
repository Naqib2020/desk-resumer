"""
ChatGPT / Codex Desktop application target.
"""

from .base import TargetApp


class ChatGPTTarget(TargetApp):
    @property
    def name(self) -> str:
        return "ChatGPT"

    @property
    def process_names(self) -> list[str]:
        return ["ChatGPT", "ChatGPT.exe"]
