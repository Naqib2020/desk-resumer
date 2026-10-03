# DeskResumer Architecture & Design Specification

## Overview

DeskResumer is designed as an OS-level supervisor that bridges the gap between AI desktop IDE usage limits and unattended long-running tasks. 

```
+-------------------------------------------------------------------+
|                           DeskResumer                             |
|                                                                   |
|   +------------------+    +------------------+    +-----------+   |
|   | Target Watchers  |--->| Cooldown Parser  |--->| Scheduler |   |
|   | (ChatGPT/Antigv) |    | (Regex / Timers) |    |  Engine   |   |
|   +------------------+    +------------------+    +-----------+   |
|            |                                            |         |
|            v                                            v         |
|   +------------------+                        +---------------+   |
|   |  Remote Notifier |                        | OS Power Lock |   |
|   | (Discord/Telegram)                       |  (caffeinate) |   |
|   +------------------+                        +---------------+   |
|                                                         |         |
|                                                         v         |
|                                               +---------------+   |
|                                               | Resume Engine |   |
|                                               | (Key Injector)|   |
|                                               +---------------+   |
+-------------------------------------------------------------------+
```

---

## 1. Core Subsystems

### A. Window & State Watcher (`desk_resumer/core/watcher.py`)
- Loops every `poll_interval` seconds (default: 30s).
- Identifies running processes corresponding to supported applications:
  - **ChatGPT Desktop App**: Process name `ChatGPT` (macOS), `ChatGPT.exe` (Windows).
  - **Antigravity Desktop App**: Process name `Antigravity` (macOS), `Antigravity.exe` (Windows).
- Reads UI text elements via platform accessibility abstractions (`OSPlatformAdapter`).

### B. Cooldown Parser (`desk_resumer/core/parser.py`)
- Parses relative and absolute cooldown time stamps:
  - `"You've reached your usage limit until 3:45 PM"` -> calculates remaining delta until 3:45 PM.
  - `"Try again in 2 hours 15 minutes"` -> extracts 2h 15m.
  - `"Limit resets at 04:30 AM"` -> resolves rollover for next-day times.
- Adds configurable `safety_buffer_seconds` (default: 120 seconds) to ensure the API server quota has truly opened up before sending the resume prompt.

### C. OS Power Management (`desk_resumer/platform/`)
When the user is away from the computer, laptops attempt to enter sleep or suspend mode.
- **macOS (`macos.py`)**:
  - Leverages macOS native `caffeinate` utility.
  - Command: `caffeinate -dimsu -t <duration_seconds>`:
    - `-d`: prevent display sleep
    - `-i`: prevent system idle sleep
    - `-m`: prevent disk idle sleep
    - `-s`: prevent system sleep on AC power
    - `-u`: declare user activity
- **Windows (`windows.py`)**:
  - Invokes `ctypes.windll.kernel32.SetThreadExecutionState`.
  - Flags: `ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`.
  - Releases the execution state once resumption completes.

### D. Resume Engine (`desk_resumer/platform/`)
- Brings the target window to the foreground.
- Focuses the chat input area.
- Types the configurable continuation prompt (default: `"Continue working on the task from where you left off."`).
- Injects a return/submit keypress.

### E. Remote Notification Dispatcher (`desk_resumer/core/notifier.py`)
- Provides webhook integrations for **Discord** and **Telegram**.
- Lifecycle events:
  - `COOLDOWN_STARTED`: Notifies user that limit was hit and provides the exact wake-up time.
  - `HEARTBEAT`: Periodic heartbeat (e.g. hourly) confirming system is waiting.
  - `RESUMING`: Fired when wake-up timer finishes and prompt injection starts.
  - `RESUME_SUCCESS`: Confirms the target app is actively working again.
  - `ERROR`: Alert if window cannot be found or accessibility permissions are missing.

---

## 2. Directory Layout

```
desk-resumer/
├── config.example.yaml
├── pyproject.toml
├── docs/
│   └── ARCHITECTURE.md
└── desk_resumer/
    ├── __init__.py
    ├── cli.py
    ├── core/
    │   ├── __init__.py
    │   ├── watcher.py
    │   ├── parser.py
    │   └── notifier.py
    ├── platform/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── macos.py
    │   └── windows.py
    └── targets/
        ├── __init__.py
        ├── base.py
        ├── chatgpt.py
        └── antigravity.py
```
