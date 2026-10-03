"""
Targets package registry.
"""

from typing import List
from ..platform.base import PlatformAdapter
from .base import TargetApp
from .chatgpt import ChatGPTTarget
from .antigravity import AntigravityTarget


def get_configured_targets(target_names: str, adapter: PlatformAdapter) -> List[TargetApp]:
    """Returns list of TargetApp instances based on configuration."""
    available = {
        "chatgpt": ChatGPTTarget(adapter),
        "antigravity": AntigravityTarget(adapter),
    }

    if target_names.lower() == "all":
        return list(available.values())

    selected = []
    for name in target_names.split(","):
        clean_name = name.strip().lower()
        if clean_name in available:
            selected.append(available[clean_name])
    return selected
