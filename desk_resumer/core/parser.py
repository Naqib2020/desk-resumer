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

        # 1. Check relative format: "in 2h 15m", "45m", "1 hour and 30 minutes", etc.
        hours = 0
        minutes = 0
        matched_relative = False

        h_match = re.search(r"(\d+)\s*(?:h\b|hours?)", text, re.IGNORECASE)
        if h_match:
            hours = int(h_match.group(1))
            matched_relative = True

        m_match = re.search(r"(\d+)\s*(?:m\b|mins?|minutes?)", text, re.IGNORECASE)
        if m_match:
            minutes = int(m_match.group(1))
            matched_relative = True

        if matched_relative and (hours > 0 or minutes > 0):
            total_seconds = hours * 3600 + minutes * 60
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
