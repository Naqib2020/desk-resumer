"""
Regex and timestamp parser for extracting usage limit reset windows.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


class CooldownParser:
    """
    Parses rate limit banners from ChatGPT and Antigravity.
    Extracts whether limit is reached and the exact remaining cooldown in seconds.
    """

    LIMIT_KEYWORDS = [
        "usage limit",
        "reached your limit",
        "try again at",
        "try again after",
        "try again in",
        "limit resets",
        "rate limit",
        "too many requests",
        "quota exceeded",
    ]

    @classmethod
    def is_rate_limited(cls, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in cls.LIMIT_KEYWORDS)

    @classmethod
    def extract_cooldown_seconds(
        cls, text: str, default_fallback_seconds: int = 7200
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Parses text for reset time.
        Returns:
            (is_limited, wait_seconds, human_readable_description)
        """
        if not cls.is_rate_limited(text):
            return False, 0, None

        now = datetime.now()

        # 1. Check relative format: "in X hours [and] Y minutes"
        rel_match = re.search(
            r"in\s+(?:(\d+)\s*h(?:ours?)?)?\s*(?:and\s*)?(?:(\d+)\s*m(?:inutes?)?)?",
            text,
            re.IGNORECASE,
        )
        if rel_match and (rel_match.group(1) or rel_match.group(2)):
            hours = int(rel_match.group(1)) if rel_match.group(1) else 0
            minutes = int(rel_match.group(2)) if rel_match.group(2) else 0
            total_seconds = hours * 3600 + minutes * 60
            if total_seconds > 0:
                desc = f"Relative: {hours}h {minutes}m"
                return True, total_seconds, desc

        # 2. Check absolute format: "at/until/after HH:MM [AM/PM]"
        time_match = re.search(
            r"(?:at|until|after)\s+(\d{1,2}):(\d{2})\s*(AM|PM)?",
            text,
            re.IGNORECASE,
        )
        if time_match:
            raw_hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            meridiem = time_match.group(3)

            hour = raw_hour
            if meridiem:
                meridiem = meridiem.upper()
                if meridiem == "PM" and raw_hour < 12:
                    hour += 12
                elif meridiem == "AM" and raw_hour == 12:
                    hour = 0

            # Construct target datetime today
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If target_dt is in the past, it resets tomorrow
            if target_dt <= now:
                target_dt += timedelta(days=1)

            diff_seconds = int((target_dt - now).total_seconds())
            desc = f"Target reset: {target_dt.strftime('%I:%M %p')}"
            return True, diff_seconds, desc

        # 3. Fallback when limit is detected but time could not be parsed
        desc = f"Fallback cooldown: {default_fallback_seconds // 3600}h"
        return True, default_fallback_seconds, desc
