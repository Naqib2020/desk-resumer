# DeskResumer ⏳⚡

> **Autonomous Task Resumer & Cooldown Supervisor for AI Desktop IDEs**  
> Designed for **Google Antigravity** & **ChatGPT / Codex Desktop**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-blue.svg)]()
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()
[![Swift](https://img.shields.io/badge/Swift-Native%20macOS-orange.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()

When working with autonomous coding assistants like **Google Antigravity** or **ChatGPT Desktop (Codex)**, hitting the 5-hour usage/quota limit brings development to a complete standstill. If you step away from your desk or run overnight sessions, hours of potential productivity are wasted waiting for the limit to clear because the app requires manual interaction to resume.

**DeskResumer** operates as an autonomous supervisor:
1. 🔍 **Rate-Limit Detection**: Continuously monitors assistant windows for usage limit banners and cooldown countdowns.
2. ⏱️ **Timestamp Parsing**: Accurately extracts relative (`2h 15m`) and absolute (`until 3:45 PM`) reset times.
3. ☕ **Dynamic Sleep Prevention**: Asserts OS wake locks via `caffeinate` on macOS and `SetThreadExecutionState` on Windows so your machine never sleeps during active work or countdowns.
4. 📋 **Autonomous Pipeline (`TASKS.md`)**: Auto-steps through sequential project milestones, injecting the next pending task into the AI prompt once quota replenishes.
5. 📲 **Mobile Alerts & Remote Bot**: Delivers push notifications via `ntfy.sh` (zero setup), Discord, or two-way interactive Telegram bot (`/status`, `/skip`, `/pause`, `/resume`).

---

## 🖥️ Native User Interfaces

DeskResumer is designed with a **True Native First** philosophy. No heavy Electron wrappers or resource-draining web views.

### 🍏 Apple Native Menu Bar App (macOS)
Built purely in **SwiftUI** using Apple's modern **Liquid Glass** aesthetic (`.ultraThinMaterial`, specular borders, responsive spring physics).
* **Two Tabs**: Live **Dashboard** (pipeline tracker, channel status, workspace changer) and **Settings** (Telegram/ntfy credentials, safety buffers).
* **Zero External Dependencies**: Compiles in 1.5 seconds using the pre-installed `/usr/bin/swiftc` compiler.
* **Instant Launch**:
  ```bash
  ./run-macos-menubar.sh
  ```

### 🪟 Windows Native System Tray App (Windows)
Built in **C# / .NET** providing a lightweight system tray icon, live context menus, and background worker bridge.
* Double-click `run-windows.bat` or see the [Windows Guide](docs/WINDOWS_GUIDE.md).

---

## 🚀 Quickstart

### 1. Installation

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

### 2. Configuration (Optional)

```bash
cp config.example.yaml config.yaml
```
*(You can also configure Telegram, Discord, and ntfy directly inside the native Menu Bar UI Settings tab).*

### 3. Running DeskResumer

* **macOS Menu Bar App**:
  ```bash
  ./run-macos-menubar.sh
  ```
* **CLI Watchdog**:
  ```bash
  desk-resumer watch --queue TASKS.md
  ```
* **Persistent OS Background Service** (survives terminal close and system reboots):
  ```bash
  desk-resumer service install
  desk-resumer service start
  desk-resumer service status
  ```

---

## 📋 The Execution Pipeline (`TASKS.md`)

DeskResumer includes a native **Autonomous Execution Pipeline**:
* **Completely Optional**: If no `TASKS.md` is present, DeskResumer simply falls back to resuming with *"Continue your work."*
* **Auto-Created**: Adding a subtask inside the Menu Bar UI automatically generates a `TASKS.md` in your project folder.
* **Standard Markdown**: Compatible with standard markdown checklists:
  ```markdown
  - [x] Initial setup and architecture review
  - [ ] Implement mobile and desktop preview product mockups
  - [ ] Run end-to-end responsiveness validation
  ```
* **Autonomous Stepping**: As each task milestone finishes, DeskResumer marks it complete (`- [x]`) and dispatches the next item.

---

## 📱 Mobile Alerts & Two-Way Telegram Control

* **Zero-Setup Push Notifications (`ntfy.sh`)**:
  * Set a topic name in Settings (e.g. `desk-resumer-yourname`).
  * Install the free `ntfy` app on iOS or Android and subscribe to your topic.
* **Two-Way Telegram Bot**:
  * Text `/status` – View remaining cooldown, active AI target, and pipeline progress.
  * Text `/skip` – Skip the currently stalled task and advance to the next.
  * Text `/pause` & `/resume` – Pause or resume watchdog automation remotely.

---

## 🧪 Unit Testing

DeskResumer includes zero-dependency unit tests running on Python's built-in `unittest` runner:
```bash
python3 -m unittest discover tests
```
Runs 15+ automated tests validating parser regexes, markdown checklists, and mock notification payloads.

---

## 💡 Official Feature Requests

We believe these capabilities should eventually be built natively into AI desktop environments. Comprehensive feature request proposals for both engineering teams are included in this repository:
* [**Proposal for Google Antigravity**](docs/FEATURE_REQUEST_ANTIGRAVITY.md)
* [**Proposal for OpenAI Codex & ChatGPT Desktop**](docs/FEATURE_REQUEST_CODEX.md)

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue or pull request.

## 📄 License

Distributed under the [MIT License](LICENSE).
