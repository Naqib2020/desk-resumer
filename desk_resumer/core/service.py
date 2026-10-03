"""
Persistent background daemon management for macOS (launchd) and Windows (Task Scheduler).
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


class ServiceManager:
    """
    Manages running DeskResumer as a persistent, background OS service
    that survives terminal closures and can auto-start on login.
    """

    SERVICE_LABEL = "com.deskresumer.daemon"

    @classmethod
    def install(cls, project_dir: Optional[str] = None):
        """Installs the background service configuration."""
        cwd = project_dir or str(Path.cwd().resolve())

        if sys.platform == "darwin":
            cls._install_macos(cwd)
        elif sys.platform == "win32":
            cls._install_windows(cwd)
        else:
            print(f"[Service] OS {sys.platform} not supported for service automation.")

    @classmethod
    def start(cls):
        """Starts the background service."""
        if sys.platform == "darwin":
            subprocess.run(["launchctl", "start", cls.SERVICE_LABEL])
            print(f"🚀 Started {cls.SERVICE_LABEL} via launchctl.")
        elif sys.platform == "win32":
            subprocess.run(["schtasks", "/Run", "/TN", "DeskResumer"])
            print("🚀 Started DeskResumer scheduled task.")

    @classmethod
    def stop(cls):
        """Stops the background service."""
        if sys.platform == "darwin":
            subprocess.run(["launchctl", "stop", cls.SERVICE_LABEL])
            print(f"🛑 Stopped {cls.SERVICE_LABEL}.")
        elif sys.platform == "win32":
            subprocess.run(["schtasks", "/End", "/TN", "DeskResumer"])
            print("🛑 Stopped DeskResumer scheduled task.")

    @classmethod
    def status(cls):
        """Displays service status and recent logs."""
        if sys.platform == "darwin":
            res = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
            running = cls.SERVICE_LABEL in res.stdout
            print(f"• Service State: {'🟢 RUNNING' if running else '⚪ STOPPED'}")

            log_file = Path.home() / "Library" / "Logs" / "desk-resumer.log"
            if log_file.exists():
                print(f"\n📄 Recent Logs ({log_file}):")
                tail = subprocess.run(["tail", "-n", "15", str(log_file)], capture_output=True, text=True)
                print(tail.stdout or "(No log content)")
            else:
                print(f"Log file not created yet: {log_file}")

        elif sys.platform == "win32":
            res = subprocess.run(["schtasks", "/Query", "/TN", "DeskResumer"], capture_output=True, text=True)
            print(res.stdout)

    @classmethod
    def uninstall(cls):
        """Removes the service configuration."""
        if sys.platform == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"{cls.SERVICE_LABEL}.plist"
            if plist_path.exists():
                subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
                plist_path.unlink()
                print(f"🗑️ Uninstalled and deleted {plist_path}.")
            else:
                print("Service is not installed.")

        elif sys.platform == "win32":
            subprocess.run(["schtasks", "/Delete", "/TN", "DeskResumer", "/F"])
            print("🗑️ Removed DeskResumer Windows scheduled task.")

    # --- Internal Platform Implementations ---

    @classmethod
    def _install_macos(cls, project_dir: str):
        launch_agents = Path.home() / "Library" / "LaunchAgents"
        launch_agents.mkdir(parents=True, exist_ok=True)
        plist_path = launch_agents / f"{cls.SERVICE_LABEL}.plist"

        logs_dir = Path.home() / "Library" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "desk-resumer.log"

        python_bin = sys.executable

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{cls.SERVICE_LABEL}</string>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_bin}</string>
        <string>-m</string>
        <string>desk_resumer.cli</string>
        <string>watch</string>
    </array>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{log_file}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        with open(plist_path, "w", encoding="utf-8") as f:
            f.write(plist_content)

        subprocess.run(["launchctl", "load", str(plist_path)])
        print(f"✅ Created macOS LaunchAgent: {plist_path}")
        print(f"• Log location: {log_file}")
        print(f"• To start: `desk-resumer service start`")

    @classmethod
    def _install_windows(cls, project_dir: str):
        python_bin = sys.executable.replace("python.exe", "pythonw.exe")
        cmd = f'"{python_bin}" -m desk_resumer.cli watch'
        schtasks_cmd = [
            "schtasks", "/Create",
            "/SC", "ONLOGON",
            "/TN", "DeskResumer",
            "/TR", f'cmd /c "cd /d {project_dir} && {cmd}"',
            "/F",
        ]
        subprocess.run(schtasks_cmd)
        print("✅ Registered Windows Scheduled Task: DeskResumer")
        print("• Auto-runs on login in the background without command windows.")
