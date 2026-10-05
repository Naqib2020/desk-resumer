# DeskResumer

> Autonomous task resumer and rate-limit cooldown supervisor for AI desktop environments (ChatGPT / Codex & Google Antigravity).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-blue.svg)]()
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
[![Swift](https://img.shields.io/badge/Swift-Native%20macOS-orange.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()

When executing long-running autonomous workflows in desktop coding agents like ChatGPT (Codex) or Google Antigravity, hitting 5-hour quota limits halts execution. If you step away from your machine or run tasks overnight, hours of development time are lost waiting for the rate limit to clear before manually prompting the agent to resume.

DeskResumer runs as a lightweight supervisor:
- **Rate-Limit Detection**: Monitors desktop windows for usage limit banners and cooldown messages.
- **Timestamp Parsing**: Extracts relative (`2h 15m`) and absolute (`until 3:45 PM`) reset times.
- **Power Management**: Prevents OS sleep during cooldowns via `caffeinate` (macOS) and `SetThreadExecutionState` (Windows).
- **Sequential Pipeline (`TASKS.md`)**: Automatically dispatches the next checklist task into the active session upon cooldown expiration.
- **Remote Notifications**: Sends alerts and accepts two-way remote control via `ntfy.sh`, Discord, and Telegram (`/status`, `/skip`, `/pause`, `/resume`).

---

## Native User Interfaces

DeskResumer uses native desktop frontends rather than web views or Electron wrappers.

### macOS Menu Bar (SwiftUI)
Built with native SwiftUI and compiled directly with Apple's `swiftc` compiler:
- Compact menu bar popover with Liquid Glass styling (`.ultraThinMaterial`).
- Live target status, interactive task checklist, workspace directory selector, and settings panel.
- Zero extra dependencies or Xcode project setup required.

```bash
./run-macos-menubar.sh
```

### Windows System Tray (.NET / C#)
Built in C# for Windows 10/11:
- System tray status icon, context menu actions, and Win32 power management integration.
- Launch via `run-windows.bat` (see [Windows Setup Guide](docs/WINDOWS_GUIDE.md)).

---

## Quickstart

### Prerequisites
- Python 3.10+
- macOS (Sonoma / Sequoia) or Windows 10/11

### Installation

```bash
git clone https://github.com/your-username/desk-resumer.git
cd desk-resumer

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e .
```

### Running

**macOS Menu Bar App:**
```bash
./run-macos-menubar.sh
```

**CLI Watchdog:**
```bash
desk-resumer watch --queue TASKS.md
```

**Persistent Background Service (launchd / Task Scheduler):**
```bash
desk-resumer service install
desk-resumer service start
desk-resumer service status
```

---

## Task Pipeline (`TASKS.md`)

DeskResumer can optionally drive multi-step workflows from a standard Markdown checklist:

```markdown
- [x] Initial setup and architecture review
- [ ] Implement mobile and desktop preview product mockups
- [ ] Run end-to-end responsiveness validation
```

- **Automatic progression**: When an in-flight task finishes and the agent goes idle, DeskResumer marks it complete (`- [x]`) and dispatches the next item.
- **Self-initializing**: Adding a subtask inside the Menu Bar UI automatically generates `TASKS.md` if one does not exist.
- **Fallback prompt**: If `TASKS.md` is omitted, DeskResumer defaults to injecting `"Continue working on the task from where you left off."` upon wake-up.

---

## Mobile Notifications & Telegram Control

- **ntfy.sh (Push Notifications)**: Free, zero-account mobile push alerts on iOS and Android. Specify a topic in Settings or `config.yaml`.
- **Telegram Bot**: Full two-way control from your phone:
  - `/status` — View active targets, current step, and remaining cooldown.
  - `/skip` — Mark current task skipped and advance to next.
  - `/pause` / `/resume` — Pause or resume the watchdog remotely.

---

## Tests

The test suite runs with zero third-party dependencies using Python's standard `unittest`:

```bash
python3 -m unittest discover tests
```

Includes automated test coverage for relative/absolute cooldown parsing, markdown checklist mutations, and notification dispatchers.

---

## Upstream Feature Requests

Detailed feature request proposals for native integration into both IDEs are included in this repository:
- [Google Antigravity Proposal](docs/FEATURE_REQUEST_ANTIGRAVITY.md)
- [OpenAI Codex / ChatGPT Desktop Proposal](docs/FEATURE_REQUEST_CODEX.md)

---

## Contributing

Pull requests and issues are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)
