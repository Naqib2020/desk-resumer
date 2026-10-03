"""
Main watchdog loop monitoring AI desktop applications.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..platform import get_platform_adapter
from ..targets import get_configured_targets, TargetApp
from .notifier import Notifier


class Watchdog:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adapter = get_platform_adapter()
        self.notifier = Notifier(config.get("notifications", {}))

        monitoring_cfg = config.get("monitoring", {})
        self.poll_interval = monitoring_cfg.get("poll_interval_seconds", 30)
        self.safety_buffer = monitoring_cfg.get("safety_buffer_seconds", 120)
        self.target_names = monitoring_cfg.get("target_apps", "all")

        resumption_cfg = config.get("resumption", {})
        self.default_prompt = resumption_cfg.get(
            "default_prompt", "Continue working on the task from where you left off."
        )

        power_cfg = config.get("power", {})
        self.prevent_sleep = power_cfg.get("prevent_sleep", True)
        self.keep_display_on = power_cfg.get("keep_display_on", False)

        self.targets: List[TargetApp] = get_configured_targets(self.target_names, self.adapter)

    def run(self):
        """Main monitoring loop."""
        print("=" * 60)
        print("⚡ DeskResumer Watchdog Started")
        print(f"• Active Targets: {[t.name for t in self.targets]}")
        print(f"• Polling Interval: {self.poll_interval}s")
        print(f"• Safety Buffer: {self.safety_buffer}s")
        print(f"• Sleep Prevention: {'Enabled' if self.prevent_sleep else 'Disabled'}")
        print("=" * 60)

        try:
            while True:
                for target in self.targets:
                    self._check_target(target)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[Watchdog] Interrupted by user. Cleaning up...")
        finally:
            self.adapter.stop_wake_lock()
            print("[Watchdog] Stopped.")

    def _check_target(self, target: TargetApp):
        if not target.is_running():
            return

        is_limited, wait_seconds, desc = target.check_status()
        if not is_limited:
            return

        total_wait = wait_seconds + self.safety_buffer
        resume_time = datetime.now() + timedelta(seconds=total_wait)
        resume_str = resume_time.strftime("%I:%M:%S %p")

        alert_msg = (
            f"🚨 {target.name} usage limit detected! ({desc})\n"
            f"Waiting {total_wait // 60} minutes (resets ~{resume_str}).\n"
            f"Laptop keep-awake: {'Active' if self.prevent_sleep else 'Inactive'}."
        )
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {alert_msg}")
        self.notifier.send(alert_msg)

        # 1. Acquire OS Wake Lock
        if self.prevent_sleep:
            self.adapter.start_wake_lock(
                duration_seconds=total_wait + 60,
                keep_display_on=self.keep_display_on,
            )

        # 2. Wait out the cooldown period with countdown logs
        self._sleep_countdown(total_wait, target.name)

        # 3. Resume the application
        wake_msg = f"⏰ Cooldown finished! Resuming {target.name} with prompt: '{self.default_prompt}'"
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {wake_msg}")
        self.notifier.send(wake_msg)

        success = target.resume_task(self.default_prompt)

        # 4. Release Wake Lock
        if self.prevent_sleep:
            self.adapter.stop_wake_lock()

        if success:
            done_msg = f"✅ {target.name} task resumed successfully."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {done_msg}")
            self.notifier.send(done_msg)
        else:
            fail_msg = f"❌ Failed to focus/inject prompt into {target.name}."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {fail_msg}")
            self.notifier.send(fail_msg)

        # Brief delay to allow target app to update status before polling again
        time.sleep(15)

    def _sleep_countdown(self, total_seconds: int, app_name: str):
        """Displays periodic status while sleeping."""
        remaining = total_seconds
        step = 60  # Log every minute
        while remaining > 0:
            minutes_left = remaining // 60
            secs_left = remaining % 60
            print(f"  [Waiting on {app_name}] {minutes_left:02d}m {secs_left:02d}s remaining...", end="\r")
            sleep_chunk = min(step, remaining)
            time.sleep(sleep_chunk)
            remaining -= sleep_chunk
        print()
