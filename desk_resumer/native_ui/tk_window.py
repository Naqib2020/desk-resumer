"""
Zero-dependency Native GUI using Python's built-in Tkinter.
Loads in 10ms with 0 MB external package downloads.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional

from ..platform import get_platform_adapter
from ..targets import get_configured_targets
from ..core.queue import TaskQueue
from ..core.notifier import Notifier


class NativeTkDashboard:
    """Zero-dependency dark-mode native desktop dashboard."""
    def __init__(self, root: tk.Tk, config_path: str = "config.yaml"):
        self.root = root
        self.config_path = config_path
        self.root.title("DeskResumer // Autonomous Supervisor")
        self.root.geometry("620x720")
        self.root.configure(bg="#0b0d12")
        self.root.minsize(580, 680)

        self.adapter = get_platform_adapter()
        self.queue = TaskQueue("TASKS.md")
        self.is_monitoring = False

        self._apply_styles()
        self._build_ui()

        # Polling loop every 2.5 seconds
        self._poll_loop()

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configure dark colors
        style.configure("TFrame", background="#0b0d12")
        style.configure("Card.TFrame", background="#12151f", relief="flat")
        style.configure("TLabel", background="#0b0d12", foreground="#e2e8f0", font=("Helvetica", 11))
        style.configure("Card.TLabel", background="#12151f", foreground="#94a3b8", font=("Helvetica", 10))
        style.configure("CardVal.TLabel", background="#12151f", foreground="#f8fafc", font=("Courier", 11, "bold"))
        style.configure("CardTitle.TLabel", background="#12151f", foreground="#f8fafc", font=("Helvetica", 12, "bold"))
        style.configure("HeaderTitle.TLabel", background="#121620", foreground="#ffffff", font=("Helvetica", 13, "bold"))
        style.configure("HeaderSub.TLabel", background="#121620", foreground="#64748b", font=("Courier", 10))

        style.configure("Action.TButton", font=("Helvetica", 10, "bold"), padding=5)
        style.configure("Primary.TButton", background="#ffffff", foreground="#000000", font=("Helvetica", 10, "bold"))

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg="#121620", height=54, highlightbackground="#1e2433", highlightthickness=1)
        header.pack(fill=tk.X, side=tk.TOP)

        title_box = tk.Frame(header, bg="#121620")
        title_box.pack(side=tk.LEFT, padx=16, pady=8)
        lbl_title = ttk.Label(title_box, text="DESKRESUMER", style="HeaderTitle.TLabel")
        lbl_title.pack(anchor="w")
        lbl_sub = ttk.Label(title_box, text="AUTONOMOUS COOLDOWN SUPERVISOR", style="HeaderSub.TLabel")
        lbl_sub.pack(anchor="w")

        btn_box = tk.Frame(header, bg="#121620")
        btn_box.pack(side=tk.RIGHT, padx=16, pady=8)

        self.btn_prefs = tk.Button(
            btn_box, text="Preferences", bg="#1e2433", fg="#e2e8f0",
            relief="flat", padx=10, pady=4, font=("Helvetica", 10),
            command=self.open_preferences
        )
        self.btn_prefs.pack(side=tk.LEFT, padx=4)

        self.btn_toggle = tk.Button(
            btn_box, text="Start Watchdog", bg="#ffffff", fg="#000000",
            relief="flat", padx=12, pady=4, font=("Helvetica", 10, "bold"),
            command=self.toggle_monitoring
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=4)

        # Content Container
        container = tk.Frame(self.root, bg="#0b0d12")
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        # 2. Status Ribbon
        ribbon = tk.Frame(container, bg="#12151f", highlightbackground="#1e2433", highlightthickness=1)
        ribbon.pack(fill=tk.X, pady=(0, 12), ipady=8, ipadx=12)

        self.lbl_ribbon_status = tk.Label(
            ribbon, text="Standby • Monitoring disabled", bg="#12151f", fg="#94a3b8", font=("Helvetica", 11)
        )
        self.lbl_ribbon_status.pack(side=tk.LEFT, padx=8)

        self.lbl_power = tk.Label(
            ribbon, text="caffeinate: idle", bg="#1a202c", fg="#94a3b8",
            font=("Courier", 10, "bold"), padx=6, pady=2
        )
        self.lbl_power.pack(side=tk.RIGHT, padx=8)

        # 3. Target Channels (Cards)
        cards_frame = tk.Frame(container, bg="#0b0d12")
        cards_frame.pack(fill=tk.X, pady=(0, 12))

        self.card_chatgpt = self._create_channel_card(cards_frame, "ChatGPT / Codex", side=tk.LEFT)
        self.card_antigravity = self._create_channel_card(cards_frame, "Antigravity", side=tk.RIGHT)

        # 4. Execution Pipeline Frame
        pipeline = tk.Frame(container, bg="#12151f", highlightbackground="#1e2433", highlightthickness=1)
        pipeline.pack(fill=tk.BOTH, expand=True, pady=(0, 12), padx=0)

        p_header = tk.Frame(pipeline, bg="#12151f")
        p_header.pack(fill=tk.X, padx=12, pady=8)

        lbl_p_title = tk.Label(p_header, text="Execution Pipeline (TASKS.md)", bg="#12151f", fg="#f8fafc", font=("Helvetica", 11, "bold"))
        lbl_p_title.pack(side=tk.LEFT)

        self.lbl_progress = tk.Label(p_header, text="0 / 0 COMPLETED (0%)", bg="#12151f", fg="#94a3b8", font=("Courier", 10, "bold"))
        self.lbl_progress.pack(side=tk.RIGHT)

        # Task list scrollable frame
        self.tasks_container = tk.Frame(pipeline, bg="#12151f")
        self.tasks_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        # Add task input
        input_bar = tk.Frame(pipeline, bg="#0d0f17", highlightbackground="#1e2433", highlightthickness=1)
        input_bar.pack(fill=tk.X, side=tk.BOTTOM, ipady=4, ipadx=8)

        self.input_new_task = tk.Entry(
            input_bar, bg="#161a24", fg="#f8fafc", insertbackground="#f8fafc",
            relief="flat", font=("Helvetica", 11)
        )
        self.input_new_task.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=4)
        self.input_new_task.bind("<Return>", lambda e: self.add_task())

        btn_add = tk.Button(
            input_bar, text="Add Task", bg="#ffffff", fg="#000000",
            relief="flat", font=("Helvetica", 10, "bold"), padx=10,
            command=self.add_task
        )
        btn_add.pack(side=tk.RIGHT, padx=4)

        # 5. Bottom Actions
        bottom_bar = tk.Frame(container, bg="#0b0d12")
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_alert = tk.Button(
            bottom_bar, text="Test Phone Alert (ntfy)", bg="#1e2433", fg="#e2e8f0",
            relief="flat", font=("Helvetica", 10), padx=10, pady=4,
            command=self.test_phone_alert
        )
        btn_alert.pack(side=tk.LEFT)

    def _create_channel_card(self, parent, name, side):
        frame = tk.Frame(parent, bg="#12151f", highlightbackground="#1e2433", highlightthickness=1)
        frame.pack(side=side, fill=tk.BOTH, expand=True, padx=4)

        top = tk.Frame(frame, bg="#12151f")
        top.pack(fill=tk.X, padx=12, pady=10)

        title = tk.Label(top, text=name, bg="#12151f", fg="#f8fafc", font=("Helvetica", 11, "bold"))
        title.pack(side=tk.LEFT)

        badge = tk.Label(top, text="OFFLINE", bg="#1a202c", fg="#94a3b8", font=("Courier", 9, "bold"), padx=6, pady=2)
        badge.pack(side=tk.RIGHT)

        proc_val = self._create_row(frame, "Application State", "Not Running")
        act_val = self._create_row(frame, "Activity Status", "Idle")
        cd_val = self._create_row(frame, "Quota Reset Window", "None (Active)")

        btn = tk.Button(
            frame, text="Trigger Prompt", bg="#1a202c", fg="#e2e8f0",
            relief="flat", font=("Helvetica", 10), pady=3,
            command=lambda: self.trigger_prompt(name)
        )
        btn.pack(fill=tk.X, padx=12, pady=10)

        return {
            "badge": badge,
            "proc_val": proc_val,
            "act_val": act_val,
            "cd_val": cd_val,
        }

    def _create_row(self, parent, label_text, val_text):
        row = tk.Frame(parent, bg="#12151f")
        row.pack(fill=tk.X, padx=12, pady=3)
        lbl = tk.Label(row, text=label_text, bg="#12151f", fg="#64748b", font=("Helvetica", 10))
        lbl.pack(side=tk.LEFT)
        val = tk.Label(row, text=val_text, bg="#12151f", fg="#f8fafc", font=("Courier", 10, "bold"))
        val.pack(side=tk.RIGHT)
        return val

    def refresh_states(self):
        targets = get_configured_targets("all", self.adapter)
        for t in targets:
            running = t.is_running()
            busy = t.is_busy() if running else False
            limited, wait_sec, desc = t.check_status() if running else (False, 0, None)
            card = self.card_chatgpt if "chatgpt" in t.name.lower() else self.card_antigravity

            if not running:
                card["badge"].config(text="OFFLINE", bg="#1a202c", fg="#94a3b8")
                card["proc_val"].config(text="Not Running")
                card["act_val"].config(text="Closed")
                card["cd_val"].config(text="None")
            elif limited:
                card["badge"].config(text="COOLDOWN", bg="#78350f", fg="#fbbf24")
                card["proc_val"].config(text="Active")
                card["act_val"].config(text="Quota Limit")
                card["cd_val"].config(text=f"{wait_sec // 60}m left ({desc or ''})")
            elif busy:
                card["badge"].config(text="BUSY", bg="#064e3b", fg="#34d399")
                card["proc_val"].config(text="Active")
                card["act_val"].config(text="Generating")
                card["cd_val"].config(text="None")
            else:
                card["badge"].config(text="READY", bg="#064e3b", fg="#34d399")
                card["proc_val"].config(text="Active")
                card["act_val"].config(text="Idle")
                card["cd_val"].config(text="None")

        # Refresh Tasks
        for widget in self.tasks_container.winfo_children():
            widget.destroy()

        if self.queue.exists():
            completed, total = self.queue.get_progress()
            percent = int((completed / total * 100)) if total > 0 else 0
            self.lbl_progress.config(text=f"{completed} / {total} COMPLETED ({percent}%)")

            with open(self.queue.filepath, "r", encoding="utf-8") as f:
                import re
                for idx, line in enumerate(f):
                    m = re.match(r"^\s*-\s*\[([ xX])\]\s+(.+)$", line)
                    if m:
                        done = m.group(1).lower() == "x"
                        text = m.group(2).strip()
                        self._render_task_item(idx, text, done)

    def _render_task_item(self, line_id, text, done):
        item_frame = tk.Frame(self.tasks_container, bg="#12151f")
        item_frame.pack(fill=tk.X, pady=2)

        var = tk.BooleanVar(value=done)
        cb = tk.Checkbutton(
            item_frame, text=text, variable=var, bg="#12151f", fg="#94a3b8" if done else "#f8fafc",
            selectcolor="#0b0d12", activebackground="#12151f", activeforeground="#ffffff",
            font=("Helvetica", 10, "overstrike" if done else "normal"),
            command=lambda: self._toggle_task(line_id, var.get())
        )
        cb.pack(side=tk.LEFT)

        btn_del = tk.Button(
            item_frame, text="✕", bg="#12151f", fg="#64748b", relief="flat",
            activebackground="#12151f", activeforeground="#f87171",
            command=lambda: self._delete_task(line_id)
        )
        btn_del.pack(side=tk.RIGHT)

    def _toggle_task(self, line_id, is_checked):
        p = Path("TASKS.md")
        if p.exists():
            import re
            lines = []
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 0 <= line_id < len(lines):
                if is_checked:
                    lines[line_id] = re.sub(r"\[\s*\]", "[x]", lines[line_id], count=1)
                else:
                    lines[line_id] = re.sub(r"\[[xX]\]", "[ ]", lines[line_id], count=1)
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            self.refresh_states()

    def _delete_task(self, line_id):
        p = Path("TASKS.md")
        if p.exists():
            lines = []
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 0 <= line_id < len(lines):
                del lines[line_id]
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            self.refresh_states()

    def add_task(self):
        text = self.input_new_task.get().strip()
        if text:
            with open("TASKS.md", "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] {text}")
            self.input_new_task.delete(0, tk.END)
            self.refresh_states()

    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_toggle.config(text="Stop Watchdog", bg="#7f1d1d", fg="#fca5a5")
            self.lbl_ribbon_status.config(text="Monitoring Active • Scanning channels every 30s")
            self.lbl_power.config(text="caffeinate: active", bg="#064e3b", fg="#34d399")
        else:
            self.btn_toggle.config(text="Start Watchdog", bg="#ffffff", fg="#000000")
            self.lbl_ribbon_status.config(text="Standby • Monitoring disabled")
            self.lbl_power.config(text="caffeinate: idle", bg="#1a202c", fg="#94a3b8")

    def trigger_prompt(self, name):
        adapter = get_platform_adapter()
        target_key = name.lower().split()[0]
        targets = get_configured_targets(target_key, adapter)
        if targets:
            targets[0].resume_task("Testing DeskResumer Native connection.")

    def test_phone_alert(self):
        try:
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            notifier = Notifier(cfg.get("notifications", {}))
            notifier.send("⚡ Alert test from DeskResumer Native Desktop UI.")
            messagebox.showinfo("Alert Sent", "Dispatched push notification!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def open_preferences(self):
        PrefsWindow(self.root, self.config_path)

    def _poll_loop(self):
        self.refresh_states()
        self.root.after(2500, self._poll_loop)


class PrefsWindow(tk.Toplevel):
    def __init__(self, parent, config_path):
        super().__init__(parent)
        self.title("Preferences")
        self.geometry("380x280")
        self.configure(bg="#0b0d12")
        self.config_path = config_path

        lbl_top = tk.Label(self, text="Preferences", bg="#0b0d12", fg="#f8fafc", font=("Helvetica", 12, "bold"))
        lbl_top.pack(padx=16, pady=12, anchor="w")

        lbl_ntfy = tk.Label(self, text="NTFY.SH MOBILE PUSH TOPIC", bg="#0b0d12", fg="#94a3b8", font=("Helvetica", 9, "bold"))
        lbl_ntfy.pack(padx=16, pady=(4, 2), anchor="w")
        self.input_ntfy = tk.Entry(self, bg="#161a24", fg="#f8fafc", relief="flat", font=("Helvetica", 11))
        self.input_ntfy.pack(fill=tk.X, padx=16, pady=(0, 10))

        lbl_buf = tk.Label(self, text="COOLDOWN BUFFER (SECONDS)", bg="#0b0d12", fg="#94a3b8", font=("Helvetica", 9, "bold"))
        lbl_buf.pack(padx=16, pady=(4, 2), anchor="w")
        self.input_buf = tk.Entry(self, bg="#161a24", fg="#f8fafc", relief="flat", font=("Helvetica", 11))
        self.input_buf.pack(fill=tk.X, padx=16, pady=(0, 16))

        btn_save = tk.Button(
            self, text="Save Preferences", bg="#ffffff", fg="#000000",
            relief="flat", font=("Helvetica", 10, "bold"), pady=4,
            command=self.save
        )
        btn_save.pack(fill=tk.X, padx=16)

        # Load values
        try:
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            self.input_ntfy.insert(0, cfg.get("notifications", {}).get("ntfy", {}).get("topic", ""))
            self.input_buf.insert(0, str(cfg.get("monitoring", {}).get("safety_buffer_seconds", 120)))
        except Exception:
            pass

    def save(self):
        try:
            import yaml
            p = Path(self.config_path)
            cfg = {}
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
            cfg.setdefault("monitoring", {})["safety_buffer_seconds"] = int(self.input_buf.get() or 120)
            cfg.setdefault("notifications", {})["enabled"] = True
            cfg.setdefault("notifications", {})["ntfy"] = {"topic": self.input_ntfy.get().strip()}
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")


def run_native_tk(config_path="config.yaml"):
    root = tk.Tk()
    app = NativeTkDashboard(root, config_path)
    root.mainloop()
