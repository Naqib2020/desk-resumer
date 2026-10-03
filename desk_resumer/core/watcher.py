"""
Main watchdog loop monitoring AI desktop applications with Rate-Limit recovery, Queue & Telegram Bot support.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..platform import get_platform_adapter
from ..targets import get_configured_targets, TargetApp
from .notifier import Notifier
from .queue import TaskQueue
from .bot import TelegramRemoteBot


class Watchdog:
    def __init__(self, config: Dict[str, Any], queue_path: Optional[str] = None):
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

        # Queue / Checklist mode
        self.queue = TaskQueue(queue_path) if queue_path else None
        self.active_tasks: Dict[str, Optional[str]] = {t.name: None for t in self.targets}
        self.paused = False

        # Two-Way Telegram Remote Control
        self.bot = TelegramRemoteBot(config.get("notifications", {}), self)

    def run(self):
        """Main monitoring loop."""
        print("=" * 60)
        print("⚡ DeskResumer Watchdog Started")
        print(f"• Active Targets: {[t.name for t in self.targets]}")
        print(f"• Polling Interval: {self.poll_interval}s")
        print(f"• Safety Buffer: {self.safety_buffer}s")
        print(f"• Sleep Prevention: {'Enabled' if self.prevent_sleep else 'Disabled'}")
        if self.queue and self.queue.exists():
            done, total = self.queue.get_progress()
            print(f"• Queue Mode: Active ({self.queue.filepath} - {done}/{total} done)")
        else:
            print("• Queue Mode: Inactive (Standard auto-resume)")
        print("=" * 60)

        # Start two-way Telegram listener if configured
        self.bot.start()

        try:
            while True:
                if not self.paused:
                    for target in self.targets:
                        self._check_target(target)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[Watchdog] Interrupted by user. Cleaning up...")
        finally:
            self.bot.stop()
            self.adapter.stop_wake_lock()
            print("[Watchdog] Stopped.")

    def _check_target(self, target: TargetApp):
        if not target.is_running():
            return

        # 1. Check for Rate Limit Banner
        is_limited, wait_seconds, desc = target.check_status()
        if is_limited:
            self._handle_rate_limit(target, wait_seconds, desc)
            return

        # 2. Check Queue Mode (if active)
        if self.queue and self.queue.exists():
            self._handle_queue_step(target)

    def _handle_rate_limit(self, target: TargetApp, wait_seconds: int, desc: Optional[str]):
        total_wait = wait_seconds + self.safety_buffer
        resume_time = datetime.now() + timedelta(seconds=total_wait)
        resume_str = resume_time.strftime("%I:%M:%S %p")

        alert_msg = (
            f"🚨 {target.name} usage limit detected! ({desc})\n"
            f"Waiting {total_wait // 60} minutes (resets ~{resume_str}).\n"
            f"Laptop keep-awake: {'Active' if self.prevent_sleep else 'Inactive'}."
        )
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {alert_msg}")
        self.notifier.send(alert_msg, title="Usage Limit Reached")

        # Acquire OS Wake Lock
        if self.prevent_sleep:
            self.adapter.start_wake_lock(
                duration_seconds=total_wait + 60,
                keep_display_on=self.keep_display_on,
            )

        # Wait out the cooldown period with countdown logs
        self._sleep_countdown(total_wait, target.name)

        # Resume Prompt Selection
        in_flight_task = self.active_tasks.get(target.name)
        prompt_to_send = (
            f"Continue working on: {in_flight_task}"
            if in_flight_task
            else self.default_prompt
        )

        wake_msg = f"⏰ Cooldown finished! Resuming {target.name} with prompt: '{prompt_to_send}'"
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {wake_msg}")
        self.notifier.send(wake_msg, title="Resuming Assistant")

        success = target.resume_task(prompt_to_send)

        # Release Wake Lock
        if self.prevent_sleep:
            self.adapter.stop_wake_lock()

        if success:
            done_msg = f"✅ {target.name} task resumed successfully."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {done_msg}")
            self.notifier.send(done_msg, title="Task Resumed")
        else:
            fail_msg = f"❌ Failed to focus/inject prompt into {target.name}."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {fail_msg}")
            self.notifier.send(fail_msg, title="Resumption Error")

        time.sleep(15)

    def _handle_queue_step(self, target: TargetApp):
        """Processes sequential tasks from the queue checklist."""
        if target.is_busy():
            return

        in_flight = self.active_tasks.get(target.name)

        # If it was running a task and is now no longer busy, that task is done!
        if in_flight:
            self.queue.mark_completed(in_flight)
            done, total = self.queue.get_progress()
            msg = f"✅ Finished: {in_flight} ({done}/{total} completed)"
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            self.notifier.send(msg, title="Subtask Completed")
            self.active_tasks[target.name] = None
            time.sleep(5)

        # Check for next pending task
        next_task = self.queue.get_next_task()
        if not next_task:
            return  # Queue is completed!

        # Dispatch next task
        done, total = self.queue.get_progress()
        dispatch_msg = f"📋 [{target.name}] Dispatching task ({done + 1}/{total}):\n\"{next_task}\""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {dispatch_msg}")
        self.notifier.send(dispatch_msg, title="Dispatching Next Task")

        success = target.resume_task(next_task)
        if success:
            self.active_tasks[target.name] = next_task
        else:
            print(f"[Queue] Failed to inject next task into {target.name}")

    def _sleep_countdown(self, total_seconds: int, app_name: str):
        remaining = total_seconds
        step = 60
        while remaining > 0:
            minutes_left = remaining // 60
            secs_left = remaining % 60
            print(f"  [Waiting on {app_name}] {minutes_left:02d}m {secs_left:02d}s remaining...", end="\r")
            sleep_chunk = min(step, remaining)
            time.sleep(sleep_chunk)
            remaining -= sleep_chunk
        print()

    # --- Remote Control Bot Methods ---

    def get_status_summary(self) -> str:
        lines = ["*📊 DeskResumer Live Status*"]
        lines.append(f"• Watchdog State: {'*Paused*' if self.paused else '*Active*'}")

        for t in self.targets:
            running = t.is_running()
            if not running:
                lines.append(f"• `{t.name}`: Offline")
                continue

            busy = t.is_busy()
            is_limited, wait_sec, desc = t.check_status()
            current_task = self.active_tasks.get(t.name)

            status = "⏳ Rate Limited" if is_limited else ("⚙️ Busy" if busy else "🟢 Idle")
            lines.append(f"• `{t.name}`: {status}")
            if is_limited:
                lines.append(f"  └ Cooldown: {wait_sec // 60}m remaining ({desc})")
            if current_task:
                lines.append(f"  └ Task: _{current_task}_")

        if self.queue and self.queue.exists():
            done, total = self.queue.get_progress()
            next_t = self.queue.get_next_task()
            lines.append(f"\n*📋 Queue Progress:* {done}/{total} completed")
            if next_t:
                lines.append(f"Next: _{next_t}_")

        return "\n".join(lines)

    def skip_current_task(self) -> str:
        if not self.queue or not self.queue.exists():
            return "No active queue file found."

        for app_name, task in self.active_tasks.items():
            if task:
                self.queue.mark_completed(task)
                self.active_tasks[app_name] = None
                return f"⏩ Skipped task: _{task}_"

        next_t = self.queue.get_next_task()
        if next_t:
            self.queue.mark_completed(next_t)
            return f"⏩ Skipped pending task: _{next_t}_"

        return "No pending tasks to skip."

    def force_trigger_prompt(self) -> str:
        for t in self.targets:
            if t.is_running():
                prompt = self.queue.get_next_task() if (self.queue and self.queue.exists()) else self.default_prompt
                success = t.resume_task(prompt)
                if success:
                    return f"⚡ Forced prompt injection into `{t.name}`:\n_{prompt}_"
                return f"❌ Failed to focus/inject prompt into `{t.name}`."
        return "No running target applications found."
