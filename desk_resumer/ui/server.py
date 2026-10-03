"""
Lightweight embedded UI server with REST API for DeskResumer.
Zero external dependencies (pure Python standard library).
"""

import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..platform import get_platform_adapter
from ..targets import get_configured_targets
from ..core.parser import CooldownParser
from ..core.notifier import Notifier
from ..core.queue import TaskQueue
from ..core.watcher import Watchdog


class AppState:
    """Shared application state accessible by UI and background watchdog."""
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.adapter = get_platform_adapter()
        self.watchdog: Optional[Watchdog] = None
        self.watchdog_thread: Optional[threading.Thread] = None
        self.is_watchdog_running = False
        self.recent_logs: List[str] = []
        self.log_lock = threading.Lock()

    def log(self, message: str):
        with self.log_lock:
            ts = time.strftime("%H:%M:%S")
            entry = f"[{ts}] {message}"
            self.recent_logs.append(entry)
            if len(self.recent_logs) > 50:
                self.recent_logs.pop(0)

    def load_config(self) -> dict:
        p = Path(self.config_path)
        if not p.exists():
            ex = p.parent / "config.example.yaml"
            if ex.exists():
                p = ex
            else:
                return {}
        try:
            import yaml
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def save_config(self, data: dict):
        try:
            import yaml
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            self.log(f"Failed to save config: {e}")

    def start_watchdog(self):
        if self.is_watchdog_running:
            return
        cfg = self.load_config()
        queue_file = "TASKS.md" if Path("TASKS.md").exists() else None
        self.watchdog = Watchdog(cfg, queue_path=queue_file)
        self.is_watchdog_running = True

        def _run():
            self.log("Watchdog background service started.")
            try:
                self.watchdog.run()
            except Exception as e:
                self.log(f"Watchdog stopped: {e}")
            finally:
                self.is_watchdog_running = False

        self.watchdog_thread = threading.Thread(target=_run, daemon=True)
        self.watchdog_thread.start()

    def stop_watchdog(self):
        if not self.is_watchdog_running:
            return
        self.is_watchdog_running = False
        if self.watchdog:
            self.watchdog.paused = True
            self.adapter.stop_wake_lock()
        self.log("Watchdog background service stopped.")


STATE = AppState()


class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default request logging to keep console clean
        return

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            static_file = Path(__file__).parent / "static" / "index.html"
            if static_file.exists():
                with open(static_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

        elif path == "/api/status":
            targets = get_configured_targets("all", STATE.adapter)
            target_data = []
            for t in targets:
                running = t.is_running()
                busy = False
                is_limited = False
                wait_sec = 0
                desc = None
                if running:
                    busy = t.is_busy()
                    is_limited, wait_sec, desc = t.check_status()
                target_data.append({
                    "name": t.name,
                    "running": running,
                    "busy": busy,
                    "is_limited": is_limited,
                    "wait_seconds": wait_sec,
                    "desc": desc,
                })

            queue = TaskQueue("TASKS.md")
            done, total = queue.get_progress() if queue.exists() else (0, 0)
            next_task = queue.get_next_task() if queue.exists() else None

            self._send_json({
                "watchdog_running": STATE.is_watchdog_running,
                "targets": target_data,
                "queue": {
                    "exists": queue.exists(),
                    "completed": done,
                    "total": total,
                    "next_task": next_task,
                },
                "logs": STATE.recent_logs[-15:],
            })

        elif path == "/api/tasks":
            queue_file = Path("TASKS.md")
            tasks = []
            if queue_file.exists():
                with open(queue_file, "r", encoding="utf-8") as f:
                    for idx, line in enumerate(f):
                        check_match = re.match(r"^\s*-\s*\[([ xX])\]\s+(.+)$", line)
                        if check_match:
                            done = check_match.group(1).lower() == "x"
                            text = check_match.group(2).strip()
                            tasks.append({"id": idx, "text": text, "completed": done})
            self._send_json({"tasks": tasks})

        elif path == "/api/settings":
            cfg = STATE.load_config()
            self._send_json(cfg)

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path == "/api/watchdog/toggle":
            action = body.get("action")
            if action == "start":
                STATE.start_watchdog()
            else:
                STATE.stop_watchdog()
            self._send_json({"status": "ok", "running": STATE.is_watchdog_running})

        elif path == "/api/tasks/toggle":
            task_id = body.get("id")
            queue_file = Path("TASKS.md")
            if queue_file.exists():
                lines = []
                with open(queue_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if 0 <= task_id < len(lines):
                    line = lines[task_id]
                    if "[x]" in line.lower():
                        lines[task_id] = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
                    else:
                        lines[task_id] = re.sub(r"\[\s*\]", "[x]", line, count=1)
                    with open(queue_file, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                STATE.log(f"Updated task checklist item #{task_id + 1}")
            self._send_json({"status": "ok"})

        elif path == "/api/tasks/add":
            text = body.get("text", "").strip()
            if text:
                queue_file = Path("TASKS.md")
                with open(queue_file, "a", encoding="utf-8") as f:
                    f.write(f"\n- [ ] {text}")
                STATE.log(f"Added new task to checklist: '{text}'")
            self._send_json({"status": "ok"})

        elif path == "/api/tasks/delete":
            task_id = body.get("id")
            queue_file = Path("TASKS.md")
            if queue_file.exists():
                lines = []
                with open(queue_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if 0 <= task_id < len(lines):
                    del lines[task_id]
                    with open(queue_file, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                STATE.log(f"Deleted task item #{task_id + 1}")
            self._send_json({"status": "ok"})

        elif path == "/api/settings":
            STATE.save_config(body)
            STATE.log("Configuration updated via UI.")
            self._send_json({"status": "ok"})

        elif path == "/api/test/notify":
            cfg = STATE.load_config()
            notifier = Notifier(cfg.get("notifications", {}))
            msg = body.get("message", "⚡ Test notification from DeskResumer UI!")
            notifier.send(msg, title="DeskResumer Test")
            STATE.log(f"Dispatched test alert: '{msg}'")
            self._send_json({"status": "ok"})

        elif path == "/api/test/resume":
            app_name = body.get("app", "chatgpt")
            prompt = body.get("prompt", "Testing DeskResumer UI injection.")
            targets = get_configured_targets(app_name, STATE.adapter)
            if targets:
                success = targets[0].resume_task(prompt)
                STATE.log(f"Tested injection into {targets[0].name}: {'Success' if success else 'Failed'}")
                self._send_json({"status": "ok" if success else "error"})
            else:
                self._send_json({"status": "error", "message": "App not found"})

        else:
            self.send_error(404, "Endpoint not found")


def start_ui_server(port: int = 5242, open_browser: bool = True):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), RequestHandler)
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("⚡ DeskResumer UI Server Running")
    print(f"• Local Dashboard: {url}")
    print("• Press Ctrl+C to stop the UI server.")
    print("=" * 60)

    if open_browser:
        # On macOS, try launching in dedicated app mode or default browser
        if sys.platform == "darwin":
            chrome_app = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if Path(chrome_app).exists():
                import subprocess
                subprocess.Popen([chrome_app, f"--app={url}"])
            else:
                webbrowser.open(url)
        else:
            webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[UI] Shutting down UI server...")
        STATE.stop_watchdog()
        server.server_close()
