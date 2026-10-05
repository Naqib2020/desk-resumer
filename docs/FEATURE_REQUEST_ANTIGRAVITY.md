# Feature Request: Native Quota-Aware Sleep Prevention & Autonomous Task Resumption

## 1. Problem Statement
When executing multi-step agentic workflows in Google Antigravity, tasks frequently reach the standard model quota limit (e.g. the 5-hour window). When this occurs:
1. **Unattended Execution Halts**: The agent stops and displays a countdown (e.g., *"Usage limit reached. Resets in 2h 15m"*), but requires manual human intervention to resume once the reset time arrives. If the user is away or asleep, hours of potential development time are lost.
2. **System Sleep Interrupts Execution**: Operating systems (macOS/Windows) enter sleep mode during inactive periods, dropping network sockets and pausing background processes.
3. **Lack of Out-of-Band Visibility**: Developers working away from their desk have no native way to receive alerts when a cooldown begins, when work resumes, or when a task is finished.

---

## 2. Proposed Solution
We propose building native quota-aware autonomous resumption and sleep management directly into Google Antigravity:

### A. Dynamic Sleep Prevention (Power Assertions)
- When a task is actively generating or in a rate-limit cooldown, Antigravity should automatically assert an OS-level wake lock:
  - **macOS**: `IOPMAssertionCreateWithName(kIOPMAssertionTypePreventUserIdleSystemSleep, ...)` or managed `caffeinate`.
  - **Windows**: `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`.
- Release the wake lock as soon as the execution queue completes or user cancels.

### B. Autonomous Cooldown Countdown & Self-Resume
- Parse the exact reset timestamp directly from the backend API response headers (`x-ratelimit-reset` / reset time).
- Run an internal timer within the IDE/agent runtime.
- Automatically trigger a continuation prompt (e.g., `"Continue working on the current task"`) the moment the reset window expires, without requiring user presence.

### C. Native Sequential Task Checklist Integration
- Support auto-advancing through project plans or markdown task queues (e.g., `TASKS.md` or workspace plan checklists).
- Once a task or milestone passes verification, the agent automatically marks it complete and dispatches the next pending item.

### D. Mobile Alerts & Remote Status (Webhooks / Push)
- Optional configurable webhook (Slack, Discord, Telegram, or `ntfy.sh`) allowing developers to receive notifications on their phone:
  - ⏳ *"Quota reached. Cooldown until 3:45 PM. Mac sleep prevented."*
  - 🚀 *"Cooldown complete. Resumed subtask: 'Implement database schema'."*
  - ✅ *"Milestone complete (3/5 tasks finished)."*

---

## 3. Working Proof-of-Concept
An external open-source supervisor tool, **DeskResumer**, was built to solve this exact problem externally:
* **Architecture**: A lightweight background supervisor with native macOS Menu Bar (SwiftUI) and Windows Tray interfaces.
* **Capabilities**: Watches process states, acquires OS power assertions, tracks relative & absolute cooldown timers, auto-injects prompts upon wake, parses markdown task queues (`TASKS.md`), and sends push alerts.
* **Repository**: https://github.com/Naqib2020/desk-resumer

Integrating this natively into Antigravity would eliminate the need for external supervisor wrappers, providing an unmatched "fire-and-forget" developer experience for overnight and long-running autonomous coding sessions.
