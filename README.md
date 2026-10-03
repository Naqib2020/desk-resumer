# DeskResumer ⏳⚡

> An open-source autonomous task resumer & cooldown supervisor for AI Desktop IDEs (**ChatGPT / Codex** & **Google Antigravity**).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-blue.svg)]()

When working with state-of-the-art coding assistants like **ChatGPT (Codex)** or **Antigravity**, hitting the 5-hour usage/quota limit interrupts long-running workflows. If you step away from your desk or leave your computer overnight, hours are wasted waiting for the limit to reset before you can manually type "continue".

**DeskResumer** acts as an autonomous background watchdog:
1. 🔍 **Detects Rate Limits**: Monitors target desktop windows for usage limit banners and cooldown messages.
2. ⏱️ **Parses Reset Timestamps**: Accurately calculates how many hours/minutes remain until quota resets.
3. ☕ **Prevents OS Sleep**: Keeps macOS (`caffeinate`) or Windows (`SetThreadExecutionState`) awake in low-power state so work doesn't stop while you are away.
4. 📲 **Sends Mobile Alerts**: Dispatches real-time status updates via Discord Webhook or Telegram Bot.
5. 🚀 **Auto-Resumes Task**: Once cooldown expires (+ safety buffer), focuses the application window, inputs your continuation prompt, and resumes execution seamlessly.

---

## Supported Desktop Applications

| Application | Platform | Detection Method | Resumption Trigger |
| :--- | :--- | :--- | :--- |
| **ChatGPT / Codex Desktop App** | macOS, Windows | Accessibility API / Window Inspection | Window Focus + Return Key Injection |
| **Antigravity Desktop App** | macOS, Windows | Accessibility API / Transcript Watcher | Window Focus + Return Key Injection |

---

## Quickstart

### Prerequisites
- Python 3.10+
- macOS (tested on Sonoma/Sequoia) or Windows 10/11

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/desk-resumer.git
cd desk-resumer

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

Copy the example configuration:
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to specify:
- Which applications to monitor (`chatgpt`, `antigravity`, or `all`).
- Safety buffer (default: 2 minutes after stated reset time).
- Optional Telegram or Discord webhook credentials for mobile alerts.

### Usage

```bash
# 1. Start the watchdog in queue mode (processes TASKS.md automatically)
desk-resumer watch --queue TASKS.md

# 2. Check task checklist progress
desk-resumer queue-status

# 3. Test open window detection
desk-resumer test-detect

# 4. Run as a persistent background OS service (survives terminal close)
desk-resumer service install
desk-resumer service start
desk-resumer service status

# 5. Test mobile alerts
desk-resumer test-notify --message "Testing mobile alert"
```

---

## 📱 Mobile Alerts & Two-Way Telegram Control

- **Push Notifications via ntfy.sh**: Zero account setup. Just subscribe to your topic on iOS/Android.
- **Two-Way Remote Control via Telegram**: Send commands from your phone while away:
  - `/status` – Live target states, active step & remaining cooldown.
  - `/skip` – Skip current task in `TASKS.md` if stuck.
  - `/pause` / `/resume` – Pause or unpause autonomous execution.
  - `/trigger` – Force injection into the active app.

---

## 🪟 Windows PC Support

DeskResumer is fully tested on Windows 10 and 11 using native Win32 `SetThreadExecutionState` and `pywinauto`.
- Run `setup-windows.bat` for one-click installation.
- Double-click `run-windows.bat` to launch.
- See the complete [Windows Setup Guide](docs/WINDOWS_GUIDE.md) for details.


---

## Architecture

For a deep dive into the cross-platform power management, accessibility APIs, and state machine, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Contributing

Pull requests are welcome! Please check out the [Issues](https://github.com/your-username/desk-resumer/issues) tab for active tasks (e.g., Linux support, OCR fallbacks, Web UI extension).

## License

MIT License. See [LICENSE](LICENSE) for details.
