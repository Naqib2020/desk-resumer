"""
Notification dispatcher for sending mobile alerts via Discord, Telegram, or ntfy.sh.
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any


class Notifier:
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", False)
        self.discord_url = config.get("discord", {}).get("webhook_url", "").strip()
        self.telegram_token = config.get("telegram", {}).get("bot_token", "").strip()
        self.telegram_chat_id = config.get("telegram", {}).get("chat_id", "").strip()
        self.ntfy_topic = config.get("ntfy", {}).get("topic", "").strip()

    def send(self, message: str, title: str = "DeskResumer Alert"):
        """Dispatches notification to all configured channels."""
        if not self.enabled:
            return

        print(f"[Mobile Alert] {message}")

        if self.ntfy_topic:
            self._send_ntfy(message, title)

        if self.discord_url:
            self._send_discord(message)

        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message)

    def _send_ntfy(self, message: str, title: str):
        """Send push notification via ntfy.sh (zero setup, free push notifications)."""
        try:
            url = f"https://ntfy.sh/{self.ntfy_topic}"
            payload = message.encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Title": title,
                    "Priority": "high",
                    "Tags": "hourglass,robot",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Notifier] ntfy send error: {e}")

    def _send_discord(self, message: str):
        try:
            payload = json.dumps({"content": f"⚡ **DeskResumer**: {message}"}).encode("utf-8")
            req = urllib.request.Request(
                self.discord_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "DeskResumer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Notifier] Discord send error: {e}")

    def _send_telegram(self, message: str):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.telegram_chat_id,
                "text": f"⚡ DeskResumer: {message}",
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Notifier] Telegram send error: {e}")
