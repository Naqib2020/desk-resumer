# Windows Setup & Operating Guide for DeskResumer

This guide explains how to set up and run DeskResumer on **Windows 10 / Windows 11** alongside the **ChatGPT Desktop App** and **Antigravity Desktop App**.

---

## 1. Quick Installation

1. Open PowerShell or Command Prompt.
2. Clone the repository onto your Windows PC:
   ```cmd
   git clone https://github.com/Naqib2020/desk-resumer.git
   cd desk-resumer
   ```
3. Run the automated installer:
   ```cmd
   setup-windows.bat
   ```
   *(This creates a Python `venv` and installs `pywinauto`, `psutil`, and required Windows dependencies).*

---

## 2. Windows UI Automation & Permissions

DeskResumer uses the native **UIAutomation (UIA)** backend on Windows:
* **Detection:** Locates `ChatGPT.exe` and `Antigravity.exe` windows and inspects live text blocks for usage limit banners.
* **Prompt Injection:** Simulates `Ctrl+V` and `Enter` using `pywinauto.keyboard`.

> [!NOTE]
> If you run your IDE or PowerShell with Administrator privileges, ensure you also run DeskResumer in an elevated console so Windows allows cross-process window automation.

---

## 3. Power Management on Windows (`SetThreadExecutionState`)

On Windows laptops or desktops, Windows normally enters Sleep or Modern Standby (S0) after a period of inactivity.

DeskResumer prevents this automatically during rate limit cooldowns by calling the Win32 kernel API:
```python
ctypes.windll.kernel32.SetThreadExecutionState(
    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
)
```
* **`ES_SYSTEM_REQUIRED`**: Prevents the system from entering sleep.
* **`ES_AWAYMODE_REQUIRED`**: Enables Away Mode (the screen can turn off to save power, but CPU background execution remains 100% active).
* Once the cooldown expires and the task resumes, DeskResumer automatically releases the lock.

---

## 4. Running DeskResumer

### Interactive Mode:
Simply double-click `run-windows.bat` or run:
```cmd
venv\Scripts\python -m desk_resumer.cli watch --queue TASKS.md
```

### Background Service Mode (Task Scheduler):
To run DeskResumer silently in the background on Windows without keeping a command prompt open:
```cmd
venv\Scripts\python -m desk_resumer.cli service install
```
To stop or remove:
```cmd
venv\Scripts\python -m desk_resumer.cli service stop
venv\Scripts\python -m desk_resumer.cli service uninstall
```

---

## 5. Verifying Everything Works

Run the diagnostic suite:
```cmd
# 1. Test window detection for ChatGPT & Antigravity
venv\Scripts\python -m desk_resumer.cli test-detect

# 2. Test 10-second Windows wake lock
venv\Scripts\python -m desk_resumer.cli test-power

# 3. Test prompt injection into ChatGPT
venv\Scripts\python -m desk_resumer.cli test-resume --app chatgpt
```
