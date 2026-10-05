# Feature Request: Native Quota-Aware Sleep Prevention & Autonomous Task Resumption for Codex / ChatGPT Desktop

## 1. Problem Statement
When running autonomous coding workflows or complex multi-turn tasks with Codex / ChatGPT Desktop, sessions frequently encounter usage limits (e.g., standard 5-hour rolling rate limits).

This causes significant developer friction:
1. **Unattended Idling**: When the quota clears, the app remains idle. If a developer starts an overnight coding session or leaves their desk, the task halts permanently until manual interaction occurs.
2. **OS Sleep Interruptions**: Modern laptops (macOS and Windows) enter system sleep during long pauses, breaking active connections or halting background terminal jobs.
3. **Queue Stalls**: Without automated task stepping, multi-step engineering checklists cannot progress independently across rate limit resets.

---

## 2. Proposed Feature
Incorporate native rate-limit awareness and power management into Codex and ChatGPT Desktop:

### A. Automatic Sleep Prevention (OS Wake-Lock)
- During active token generation or rate-limit cooldown, the application asserts an OS wake lock:
  - **macOS**: `IOPMAssertionCreateWithName` (prevent system idle sleep while allowing display sleep).
  - **Windows**: `SetThreadExecutionState` (`ES_SYSTEM_REQUIRED | ES_CONTINUOUS`).
- Once tasks are completed or manually paused, the wake lock is automatically released.

### B. Auto-Resume on Quota Replenishment
- Read rate-limit reset metadata directly from response headers or client state.
- Display a native countdown timer in the client UI.
- Provide a toggle: **"Auto-resume when quota replenishes"** (defaulting to enabled for unattended sessions).
- Automatically re-trigger the pending prompt or continuation signal upon timer expiration.

### C. Sequential Task List Progression (`TASKS.md`)
- Allow Codex to bind to a project markdown checklist (e.g., `TASKS.md` or `TODO.md`).
- When a task milestone is finished, Codex automatically updates the checklist (`- [x]`) and dispatches the subsequent item.

### D. Out-of-Band Notification Integration
- Webhook or mobile push notifications (via ChatGPT mobile app push notifications, Discord, or generic webhooks) to notify users:
  - *"Rate limit reached. Sleeping prevented. Resuming at 14:30."*
  - *"Task #3 completed. 4/5 tasks finished."*

---

## 3. Reference Implementation
This workflow has been validated in the open-source community via **DeskResumer**, an external supervisor app designed specifically for Codex and Antigravity:
* Demonstrates OS-level wake locking on macOS & Windows.
* Implements reliable countdown parsing, automated prompt injection, markdown task queue progression, and two-way remote bot management.
* **Repository Reference**: https://github.com/Naqib2020/desk-resumer

Native support within ChatGPT Desktop / Codex would transform long-running autonomous development into a seamless, unattended experience.
