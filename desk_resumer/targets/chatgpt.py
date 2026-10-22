"""
ChatGPT / Codex Desktop application target.
"""

import os
import sqlite3
from typing import Optional, Tuple
from .base import TargetApp
from ..core.parser import CooldownParser


class ChatGPTTarget(TargetApp):
    @property
    def name(self) -> str:
        return "ChatGPT"

    @property
    def process_names(self) -> list[str]:
        return ["ChatGPT", "ChatGPT.exe"]

    def check_status(self) -> Tuple[bool, int, Optional[str]]:
        """
        Inspects Codex logs database and fallback window text for usage limit status.
        """
        # 1. Check local Codex session logs database (highly accurate for Codex Desktop)
        codex_db = os.path.expanduser("~/.codex/logs_2.sqlite")
        if os.path.exists(codex_db):
            try:
                conn = sqlite3.connect(f"file:{codex_db}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT feedback_log_body, ts FROM logs 
                    WHERE feedback_log_body LIKE '%usage limit%' OR feedback_log_body LIKE '%rate limit%' 
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                conn.close()
                if row:
                    body, ts = row
                    is_lim, secs, desc = CooldownParser.extract_cooldown_seconds(body)
                    if is_lim and secs > 0:
                        return True, secs, desc
            except Exception:
                pass

        # 2. Fall back to base window text inspection
        return super().check_status()
