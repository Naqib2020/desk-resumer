"""
Unit tests for cooldown banner regex parser (parser.py).
Compatible with both unittest and pytest.
"""

import unittest
from desk_resumer.core.parser import CooldownParser


class TestCooldownParser(unittest.TestCase):
    def test_parse_relative_hours_and_minutes(self):
        text = "Usage limit reached. Resets in 2h 15m."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        # 2 hours 15 mins = 2 * 3600 + 15 * 60 = 8100 seconds
        self.assertEqual(seconds, 8100)
        self.assertIn("2h 15m", desc)

    def test_parse_relative_minutes_only(self):
        text = "You have reached the rate limit. Please try again in 45m."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        self.assertEqual(seconds, 2700)
        self.assertIn("45m", desc)

    def test_parse_relative_words(self):
        text = "Limit reached: try again in 1 hour and 30 minutes."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        self.assertEqual(seconds, 5400)

    def test_parse_relative_simple_minutes(self):
        text = "Usage limit reached: try again in 10 minutes."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        self.assertEqual(seconds, 600)

    def test_parse_absolute_12h_format(self):
        text = "You've reached your current quota limit. Try again at 3:45 PM."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        self.assertGreater(seconds, 0)
        self.assertLessEqual(seconds, 86400)
        self.assertIn("Target reset", desc)

    def test_parse_absolute_after_format(self):
        text = "Rate limit reached. Try again after 11:30 AM."
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertTrue(is_limited)
        self.assertGreater(seconds, 0)
        self.assertLessEqual(seconds, 86400)

    def test_parse_no_cooldown_found(self):
        text = "Everything is running smoothly! How can I help you today?"
        is_limited, seconds, desc = CooldownParser.extract_cooldown_seconds(text)
        self.assertFalse(is_limited)
        self.assertEqual(seconds, 0)
        self.assertIsNone(desc)


if __name__ == "__main__":
    unittest.main()
