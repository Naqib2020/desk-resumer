"""
Two-way interactive Telegram Bot listener allowing remote control via mobile chat.
Uses standard library urllib (no heavy telegram packages required).
"""

import json
import threading
import time
import urllib.request
import urllib.parse
from typing import Optional, Any


class TelegramRemoteBot:
    """
    Background long-polling listener that enables two-way remote control
    via Telegram. Supports commands: /status, /skip, /pause, /resume, /help.
    """

    def __init__(self, config: dict, watchdog_instance: Any):
        self.token = config.get("telegram", {}).get("bot_token", "").strip()
        self.allowed_chat_id = str(config.get("telegram", {}).get("chat_id", "")).strip()
        self.watchdog = watchdog_instance
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update_id = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.allowed_chat_id)

    def start(self):
        """Starts the Telegram polling worker in a background thread."""
        if not self.is_configured:
            return

        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print(f"[Remote] Telegram two-way control active for chat ID: {self.allowed_chat_id}")

    def stop(self):
        self.running = False

    def send_reply(self, chat_id: str, text: str):
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[Remote] Failed to send Telegram reply: {e}")

    def _poll_loop(self):
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates?offset={self._last_update_id + 1}&timeout=15"
                req = urllib.request.Request(url, headers={"User-Agent": "DeskResumer/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if not data.get("ok"):
                    time.sleep(3)
                    continue

                for update in data.get("result", []):
                    self._last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg or "text" not in msg:
                        continue

                    sender_id = str(msg.get("chat", {}).get("id", "")).strip()
                    if sender_id != self.allowed_chat_id:
                        # Reject unauthorized users
                        continue

                    text = msg.get("text", "").strip()
                    self._handle_command(sender_id, text)

            except Exception as e:
                time.sleep(3)

    def _handle_command(self, chat_id: str, text: str):
        cmd = text.split()[0].lower() if text else ""

        if cmd in ["/start", "/help"]:
            reply = (
                "🤖 *DeskResumer Remote Control*\n\n"
                "Commands:\n"
                "• `/status` - Check app status, active task & cooldowns\n"
                "• `/skip` - Skip current task and move to the next\n"
                "• `/pause` - Pause autonomous task execution\n"
                "• `/resume` - Resume autonomous execution\n"
                "• `/trigger` - Force prompt injection into active app"
            )
            self.send_reply(chat_id, reply)

        elif cmd == "/status":
            reply = self.watchdog.get_status_summary()
            self.send_reply(chat_id, reply)

        elif cmd == "/skip":
            msg = self.watchdog.skip_current_task()
            self.send_reply(chat_id, msg)

        elif cmd == "/pause":
            self.watchdog.paused = True
            self.send_reply(chat_id, "⏸️ Watchdog has been *paused*. No prompts will be dispatched.")

        elif cmd == "/resume":
            self.watchdog.paused = False
            self.send_reply(chat_id, "▶️ Watchdog has been *resumed*. Monitoring active.")

        elif cmd == "/trigger":
            msg = self.watchdog.force_trigger_prompt()
            self.send_reply(chat_id, msg)

        else:
            self.send_reply(chat_id, f"Unknown command: `{text}`. Type /help for options.")
