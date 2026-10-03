"""
Command-line interface for DeskResumer.
"""

import argparse
import sys
import os
import yaml
from pathlib import Path

from .core.watcher import Watchdog
from .platform import get_platform_adapter
from .targets import get_configured_targets
from .core.parser import CooldownParser


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        # Fallback to config.example.yaml if config.yaml doesn't exist yet
        example_path = path.parent / "config.example.yaml"
        if example_path.exists():
            path = example_path
        else:
            return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(
        description="DeskResumer: Autonomous task resumer for AI Desktop IDEs"
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

    args = parser.parse_args()

    if not args.command or args.command == "watch":
        cfg = load_config(args.config)
        if hasattr(args, "app") and args.app:
            cfg.setdefault("monitoring", {})["target_apps"] = args.app
        watchdog = Watchdog(cfg)
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
                print(f"   Rate-limited: {is_limited}")
                if is_limited:
                    print(f"   Wait time: {wait_sec}s ({desc})")
                else:
                    print(f"   Status: Active / Idle (no limit banner detected)")
        print()

    elif args.command == "test-resume":
        adapter = get_platform_adapter()
        targets = get_configured_targets(args.app, adapter)
        if not targets:
            print(f"App {args.app} not found.")
            sys.exit(1)
        target = targets[0]
        print(f"🚀 Testing prompt injection into {target.name} in 3 seconds...")
        import time
        time.sleep(3)
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


if __name__ == "__main__":
    main()
