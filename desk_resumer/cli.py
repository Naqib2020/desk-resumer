"""
Command-line interface for DeskResumer.
"""

import argparse
import sys
import os
from pathlib import Path

from .core.watcher import Watchdog
from .platform import get_platform_adapter
from .targets import get_configured_targets
from .core.parser import CooldownParser
from .core.notifier import Notifier
from .core.queue import TaskQueue
from .core.service import ServiceManager


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        example_path = path.parent / "config.example.yaml"
        if example_path.exists():
            path = example_path
        else:
            return {}
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="DeskResumer: Autonomous task resumer & queue manager for AI Desktop IDEs"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to config.yaml file"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Command: watch
    watch_p = subparsers.add_parser("watch", help="Start the background watchdog")
    watch_p.add_argument(
        "--app",
        choices=["all", "chatgpt", "antigravity"],
        default=None,
        help="Target app override",
    )
    watch_p.add_argument(
        "--queue",
        nargs="?",
        const="TASKS.md",
        default=None,
        help="Path to markdown checklist queue file (default: TASKS.md if present)",
    )

    # Command: test-detect
    test_detect_p = subparsers.add_parser(
        "test-detect", help="Inspect open app windows and test rate-limit detection"
    )

    # Command: test-resume
    test_resume_p = subparsers.add_parser(
        "test-resume", help="Test focusing window and injecting prompt"
    )
    test_resume_p.add_argument(
        "--app",
        choices=["chatgpt", "antigravity"],
        required=True,
        help="Which application to test",
    )
    test_resume_p.add_argument(
        "--prompt",
        default="Testing DeskResumer connection. Please ignore.",
        help="Prompt to inject",
    )

    # Command: test-power
    test_power_p = subparsers.add_parser(
        "test-power", help="Test sleep-prevention wake lock for 10 seconds"
    )

    # Command: test-notify
    test_notify_p = subparsers.add_parser(
        "test-notify", help="Test sending an alert to phone via Discord, Telegram, or ntfy"
    )
    test_notify_p.add_argument(
        "--message",
        default="Hello from DeskResumer! Your alerts are working.",
        help="Message to dispatch",
    )

    # Command: queue-status
    queue_status_p = subparsers.add_parser(
        "queue-status", help="Show current checklist progress from TASKS.md"
    )
    queue_status_p.add_argument(
        "--file", default="TASKS.md", help="Checklist file to inspect"
    )

    # Command: service
    service_p = subparsers.add_parser(
        "service", help="Manage background OS service (launchd on Mac, Task Scheduler on Windows)"
    )
    service_p.add_argument(
        "action",
        choices=["install", "start", "stop", "status", "uninstall"],
        help="Action to perform on the service",
    )

    # Command: status-json (Machine-readable state for native frontends)
    subparsers.add_parser(
        "status-json", help="Output current state as JSON for native app frontends"
    )

    # Command: toggle-task
    toggle_p = subparsers.add_parser("toggle-task", help="Toggle a task by line index in TASKS.md")
    toggle_p.add_argument("task_id", type=int, help="Task line index")

    # Command: add-task
    add_task_p = subparsers.add_parser("add-task", help="Append a new task to TASKS.md")
    add_task_p.add_argument("text", help="Task description text")

    # Command: save-config-json
    save_cfg_p = subparsers.add_parser("save-config-json", help="Save config from JSON")
    save_cfg_p.add_argument("data", help="JSON configuration string")

    # Command: clear-completed
    subparsers.add_parser("clear-completed", help="Remove completed tasks from TASKS.md")

    args = parser.parse_args()







    if not args.command or args.command == "watch":
        cfg = load_config(args.config)
        if hasattr(args, "app") and args.app:
            cfg.setdefault("monitoring", {})["target_apps"] = args.app
        
        # Check queue flag or auto-detect TASKS.md
        queue_file = args.queue
        if queue_file is None and Path("TASKS.md").exists():
            queue_file = "TASKS.md"

        watchdog = Watchdog(cfg, queue_path=queue_file)
        watchdog.run()

    elif args.command == "test-detect":
        adapter = get_platform_adapter()
        targets = get_configured_targets("all", adapter)
        print("🔍 Checking application states:\n")
        for target in targets:
            running = target.is_running()
            print(f"• {target.name}: {'RUNNING' if running else 'NOT RUNNING'}")
            if running:
                text = adapter.get_window_text_content(target.name)
                is_limited, wait_sec, desc = CooldownParser.extract_cooldown_seconds(text or "")
                busy = target.is_busy()
                print(f"   Busy (Generating): {busy}")
                print(f"   Rate-limited: {is_limited}")
                if is_limited:
                    print(f"   Wait time: {wait_sec}s ({desc})")
                else:
                    print(f"   Status: Active / Idle (ready for tasks)")
        print()

    elif args.command == "test-resume":
        adapter = get_platform_adapter()
        targets = get_configured_targets(args.app, adapter)
        if not targets:
            print(f"App {args.app} not found.")
            sys.exit(1)
        target = targets[0]
        print(f"🚀 Injecting prompt into {target.name}...")
        success = target.resume_task(args.prompt)
        if success:
            print(f"✅ Success! Injected prompt into {target.name}.")
        else:
            print(f"❌ Failed to inject prompt.")

    elif args.command == "test-power":
        adapter = get_platform_adapter()
        print("⚡ Testing 10-second OS wake-lock...")
        adapter.start_wake_lock(duration_seconds=10, keep_display_on=True)
        import time
        time.sleep(10)
        adapter.stop_wake_lock()
        print("✅ Power lock test completed successfully.")

    elif args.command == "test-notify":
        cfg = load_config(args.config)
        notifier = Notifier(cfg.get("notifications", {}))
        if not notifier.enabled:
            print("⚠️ Notifications are currently disabled in config.")
            print("To enable, edit config.yaml and set notifications.enabled = true")
            print("Or provide an ntfy topic (e.g. ntfy: { topic: 'your-topic-name' })")
            return
        print(f"📡 Sending test notification: '{args.message}'...")
        notifier.send(args.message, title="DeskResumer Test")
        print("✅ Sent! Check your mobile device.")

    elif args.command == "queue-status":
        queue = TaskQueue(args.file)
        if not queue.exists():
            print(f"Checklist file '{args.file}' not found.")
            return
        done, total = queue.get_progress()
        next_task = queue.get_next_task()
        print(f"📋 Checklist Progress ({args.file}):")
        print(f"• Completed: {done}/{total} ({(done / total * 100) if total else 0:.0f}%)")
        print(f"• Next up: {next_task or 'All tasks completed! 🎉'}\n")

    elif args.command == "service":
        action = args.action
        if action == "install":
            ServiceManager.install()
        elif action == "start":
            ServiceManager.start()
        elif action == "stop":
            ServiceManager.stop()
        elif action == "status":
            ServiceManager.status()
        elif action == "uninstall":
            ServiceManager.uninstall()

    elif args.command == "status-json":
        import json
        import re
        adapter = get_platform_adapter()
        targets = get_configured_targets("all", adapter)
        target_data = []
        for t in targets:
            running = t.is_running()
            busy = t.is_busy() if running else False
            limited, wait_sec, desc = t.check_status() if running else (False, 0, None)
            target_data.append({
                "name": t.name,
                "running": running,
                "busy": busy,
                "is_limited": limited,
                "wait_seconds": wait_sec,
                "desc": desc,
            })

        tasks = []
        p = Path("TASKS.md")
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    m = re.match(r"^\s*-\s*\[([ xX])\]\s+(.+)$", line)
                    if m:
                        done = m.group(1).lower() == "x"
                        tasks.append({"id": idx, "text": m.group(2).strip(), "completed": done})

        completed = sum(1 for t in tasks if t["completed"])
        cfg = load_config(args.config)
        print(json.dumps({
            "targets": target_data,
            "queue": {
                "completed": completed,
                "total": len(tasks),
                "tasks": tasks
            },
            "config": cfg
        }))

    elif args.command == "save-config-json":
        import json
        import yaml
        try:
            new_cfg = json.loads(args.data)
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(new_cfg, f, default_flow_style=False, sort_keys=False)
            print("Config saved successfully.")
        except Exception as e:
            print(f"Failed to save config: {e}")

    elif args.command == "toggle-task":
        import re
        p = Path("TASKS.md")
        if p.exists():
            lines = []
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 0 <= args.task_id < len(lines):
                line = lines[args.task_id]
                if "[x]" in line.lower():
                    lines[args.task_id] = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
                else:
                    lines[args.task_id] = re.sub(r"\[\s*\]", "[x]", line, count=1)
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print(f"Toggled task #{args.task_id}")

    elif args.command == "add-task":
        text = args.text.strip()
        if text:
            with open("TASKS.md", "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] {text}")
            print(f"Added task: {text}")

    elif args.command == "clear-completed":
        import re
        p = Path("TASKS.md")
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                lines = [line for line in f if not re.match(r"^\s*-\s*\[[xX]\]\s+", line)]
            with open(p, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print("Cleared completed tasks from TASKS.md")








if __name__ == "__main__":
    main()
