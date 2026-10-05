"""
Unit tests for notification dispatcher (notifier.py).
Compatible with both unittest and pytest.
"""

import unittest
from unittest.mock import patch, MagicMock
from desk_resumer.core.notifier import Notifier


class TestNotifier(unittest.TestCase):
    def test_notifier_disabled(self):
        config = {
            "enabled": False,
            "ntfy": {"topic": "test-topic"},
        }
        notifier = Notifier(config)
        with patch("urllib.request.urlopen") as mock_urlopen:
            notifier.send("This should not be sent")
            mock_urlopen.assert_not_called()

    def test_notifier_ntfy_send(self):
        config = {
            "enabled": True,
            "ntfy": {"topic": "test-channel"},
        }
        notifier = Notifier(config)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = MagicMock()
            notifier.send("Task resumed!", title="Test Alert")
            self.assertTrue(mock_urlopen.called)
            req = mock_urlopen.call_args[0][0]
            self.assertIn("ntfy.sh/test-channel", req.full_url)
            self.assertEqual(req.headers["Title"], "Test Alert")

    def test_notifier_discord_send(self):
        config = {
            "enabled": True,
            "discord": {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
        }
        notifier = Notifier(config)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = MagicMock()
            notifier.send("Task resumed!")
            self.assertTrue(mock_urlopen.called)
            req = mock_urlopen.call_args[0][0]
            self.assertIn("discord.com", req.full_url)

    def test_notifier_telegram_send(self):
        config = {
            "enabled": True,
            "telegram": {"bot_token": "123:ABC", "chat_id": "999888"},
        }
        notifier = Notifier(config)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = MagicMock()
            notifier.send("Task completed!")
            self.assertTrue(mock_urlopen.called)
            req = mock_urlopen.call_args[0][0]
            self.assertIn("api.telegram.org/bot123:ABC/sendMessage", req.full_url)


if __name__ == "__main__":
    unittest.main()
