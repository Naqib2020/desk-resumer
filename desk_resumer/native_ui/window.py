"""
Main native desktop dashboard window for DeskResumer.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QLineEdit, QFrame, QDialog, QComboBox, QSpinBox, QMessageBox,
    QScrollArea
)

from ..platform import get_platform_adapter
from ..targets import get_configured_targets
from ..core.queue import TaskQueue
from ..core.notifier import Notifier
from ..core.watcher import Watchdog
from .style import DARK_THEME_QSS


class PreferencesDialog(QDialog):
    """Native preferences modal dialog."""
    def __init__(self, parent=None, config_path="config.yaml"):
        super().__init__(parent)
        self.setWindowTitle("DeskResumer Preferences")
        self.setFixedSize(420, 320)
        self.config_path = config_path
        self.setStyleSheet(DARK_THEME_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Preferences & Channels")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        # Target apps
        lbl_targets = QLabel("ACTIVE MONITORING TARGETS")
        lbl_targets.setProperty("class", "DataKey")
        layout.addWidget(lbl_targets)

        self.combo_targets = QComboBox()
        self.combo_targets.addItem("All Channels (ChatGPT & Antigravity)", "all")
        self.combo_targets.addItem("ChatGPT / Codex Only", "chatgpt")
        self.combo_targets.addItem("Antigravity Only", "antigravity")
        layout.addWidget(self.combo_targets)

        # Mobile Push Topic
        lbl_ntfy = QLabel("NTFY.SH MOBILE PUSH TOPIC")
        lbl_ntfy.setProperty("class", "DataKey")
        layout.addWidget(lbl_ntfy)

        self.input_ntfy = QLineEdit()
        self.input_ntfy.setPlaceholderText("e.g. desk-resumer-naqib")
        layout.addWidget(self.input_ntfy)

        # Safety Buffer
        lbl_buffer = QLabel("COOLDOWN BUFFER (SECONDS)")
        lbl_buffer.setProperty("class", "DataKey")
        layout.addWidget(lbl_buffer)

        self.spin_buffer = QSpinBox()
        self.spin_buffer.setRange(0, 1800)
        self.spin_buffer.setSingleStep(30)
        self.spin_buffer.setValue(120)
        layout.addWidget(self.spin_buffer)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Changes")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.save)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        self.load_current_values()

    def load_current_values(self):
        try:
            import yaml
            p = Path(self.config_path)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                t = cfg.get("monitoring", {}).get("target_apps", "all")
                idx = self.combo_targets.findData(t)
                if idx >= 0:
                    self.combo_targets.setCurrentIndex(idx)
                self.input_ntfy.setText(cfg.get("notifications", {}).get("ntfy", {}).get("topic", ""))
                self.spin_buffer.setValue(cfg.get("monitoring", {}).get("safety_buffer_seconds", 120))
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

            cfg.setdefault("monitoring", {})["target_apps"] = self.combo_targets.currentData()
            cfg.setdefault("monitoring", {})["safety_buffer_seconds"] = self.spin_buffer.value()
            cfg.setdefault("notifications", {})["enabled"] = True
            cfg.setdefault("notifications", {})["ntfy"] = {"topic": self.input_ntfy.text().strip()}

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")


class ChannelCard(QFrame):
    """Channel status card for ChatGPT or Antigravity."""
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.channel_name = name
        self.setProperty("class", "CardFrame")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top identity
        top = QHBoxLayout()
        title = QLabel(name)
        title.setProperty("class", "CardTitle")
        self.badge = QLabel("OFFLINE")
        self.badge.setProperty("class", "BadgePill BadgeMuted")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.badge)
        layout.addLayout(top)

        # Data rows
        self.val_proc = self._create_row(layout, "Application State", "Not Running")
        self.val_act = self._create_row(layout, "Activity Status", "Idle")
        self.val_cd = self._create_row(layout, "Quota Reset Window", "None (Active)")

        # Button
        self.btn_test = QPushButton("Trigger Prompt")
        self.btn_test.clicked.connect(self._trigger_prompt)
        layout.addWidget(self.btn_test)

    def _create_row(self, layout, label_text, val_text):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setProperty("class", "DataKey")
        val = QLabel(val_text)
        val.setProperty("class", "DataVal")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def update_state(self, running: bool, busy: bool, limited: bool, wait_sec: int, desc: Optional[str]):
        if not running:
            self.badge.setText("OFFLINE")
            self.badge.setProperty("class", "BadgePill BadgeMuted")
            self.val_proc.setText("Not Running")
            self.val_act.setText("Closed")
            self.val_cd.setText("None")
        elif limited:
            self.badge.setText("COOLDOWN")
            self.badge.setProperty("class", "BadgePill BadgeAmber")
            self.val_proc.setText("Process Active")
            self.val_act.setText("Quota Reached")
            self.val_cd.setText(f"{wait_sec // 60}m remaining ({desc or ''})")
        elif busy:
            self.badge.setText("BUSY")
            self.badge.setProperty("class", "BadgePill BadgeActive")
            self.val_proc.setText("Process Active")
            self.val_act.setText("Actively Generating")
            self.val_cd.setText("None")
        else:
            self.badge.setText("READY")
            self.badge.setProperty("class", "BadgePill BadgeActive")
            self.val_proc.setText("Process Active")
            self.val_act.setText("Idle (Awaiting task)")
            self.val_cd.setText("None")

        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def _trigger_prompt(self):
        adapter = get_platform_adapter()
        targets = get_configured_targets(self.channel_name.lower().split()[0], adapter)
        if targets:
            targets[0].resume_task("Testing DeskResumer Native UI connection.")


class DeskResumerMainWindow(QMainWindow):
    """Main native window."""
    def __init__(self, config_path="config.yaml"):
        super().__init__()
        self.setWindowTitle("DeskResumer")
        self.resize(680, 760)
        self.setStyleSheet(DARK_THEME_QSS)
        self.config_path = config_path

        self.adapter = get_platform_adapter()
        self.queue = TaskQueue("TASKS.md")
        self.watchdog: Optional[Watchdog] = None
        self.is_monitoring = False

        self._build_ui()

        # Polling Timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_states)
        self.poll_timer.start(2500)
        self.refresh_states()

    def _build_ui(self):
        central = QWidget(self)
        central.setObjectName("MainContainer")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("DESKRESUMER")
        title.setObjectName("AppTitle")
        sub = QLabel("AUTONOMOUS COOLDOWN SUPERVISOR")
        sub.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_prefs = QPushButton("Preferences")
        self.btn_prefs.clicked.connect(self.open_preferences)
        header.addWidget(self.btn_prefs)

        self.btn_toggle = QPushButton("Start Watchdog")
        self.btn_toggle.setObjectName("PrimaryButton")
        self.btn_toggle.clicked.connect(self.toggle_monitoring)
        header.addWidget(self.btn_toggle)

        main_layout.addLayout(header)

        # Status Ribbon
        ribbon = QFrame()
        ribbon.setProperty("class", "CardFrame")
        r_layout = QHBoxLayout(ribbon)
        r_layout.setContentsMargins(12, 10, 12, 10)
        self.lbl_ribbon_status = QLabel("Standby • Monitoring disabled")
        self.lbl_ribbon_status.setStyleSheet("font-size: 12px; font-weight: 500; color: #94a3b8;")
        self.pill_power = QLabel("caffeinate: idle")
        self.pill_power.setProperty("class", "BadgePill BadgeMuted")
        r_layout.addWidget(self.lbl_ribbon_status)
        r_layout.addStretch()
        r_layout.addWidget(self.pill_power)
        main_layout.addWidget(ribbon)

        # Channel Cards
        cards_layout = QHBoxLayout()
        self.card_chatgpt = ChannelCard("ChatGPT / Codex", self)
        self.card_antigravity = ChannelCard("Antigravity", self)
        cards_layout.addWidget(self.card_chatgpt)
        cards_layout.addWidget(self.card_antigravity)
        main_layout.addLayout(cards_layout)

        # Pipeline Box
        pipeline_frame = QFrame()
        pipeline_frame.setProperty("class", "CardFrame")
        p_layout = QVBoxLayout(pipeline_frame)
        p_layout.setContentsMargins(14, 12, 14, 12)
        p_layout.setSpacing(8)

        p_top = QHBoxLayout()
        p_title = QLabel("Execution Pipeline (TASKS.md)")
        p_title.setProperty("class", "CardTitle")
        self.lbl_progress = QLabel("0 / 0 COMPLETED (0%)")
        self.lbl_progress.setProperty("class", "DataVal")
        p_top.addWidget(p_title)
        p_top.addStretch()
        p_top.addWidget(self.lbl_progress)
        p_layout.addLayout(p_top)

        self.meter = QProgressBar()
        self.meter.setValue(0)
        self.meter.setTextVisible(False)
        p_layout.addWidget(self.meter)

        self.task_list = QListWidget()
        self.task_list.setFixedHeight(160)
        p_layout.addWidget(self.task_list)

        input_row = QHBoxLayout()
        self.input_task = QLineEdit()
        self.input_task.setPlaceholderText("Append subtask to pipeline...")
        self.input_task.returnPressed.connect(self.add_task)
        btn_add = QPushButton("Add Task")
        btn_add.setObjectName("PrimaryButton")
        btn_add.clicked.connect(self.add_task)
        input_row.addWidget(self.input_task)
        input_row.addWidget(btn_add)
        p_layout.addLayout(input_row)

        main_layout.addWidget(pipeline_frame)

        # Bottom Actions
        bottom = QHBoxLayout()
        btn_test_alert = QPushButton("Test Phone Alert (ntfy)")
        btn_test_alert.clicked.connect(self.test_phone_alert)
        bottom.addWidget(btn_test_alert)
        bottom.addStretch()
        main_layout.addLayout(bottom)

    def refresh_states(self):
        targets = get_configured_targets("all", self.adapter)
        for t in targets:
            running = t.is_running()
            busy = t.is_busy() if running else False
            limited, wait_sec, desc = t.check_status() if running else (False, 0, None)
            if "chatgpt" in t.name.lower():
                self.card_chatgpt.update_state(running, busy, limited, wait_sec, desc)
            elif "antigravity" in t.name.lower():
                self.card_antigravity.update_state(running, busy, limited, wait_sec, desc)

        # Refresh Tasks
        self.task_list.clear()
        if self.queue.exists():
            completed, total = self.queue.get_progress()
            percent = int((completed / total * 100)) if total > 0 else 0
            self.lbl_progress.setText(f"{completed} / {total} COMPLETED ({percent}%)")
            self.meter.setValue(percent)

            with open(self.queue.filepath, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    import re
                    m = re.match(r"^\s*-\s*\[([ xX])\]\s+(.+)$", line)
                    if m:
                        done = m.group(1).lower() == "x"
                        text = m.group(2).strip()
                        item = QListWidgetItem(self.task_list)
                        chk = CustomTaskItem(idx, text, done, self)
                        self.task_list.setItemWidget(item, chk)

    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_toggle.setText("Stop Watchdog")
            self.btn_toggle.setObjectName("StopButton")
            self.lbl_ribbon_status.setText("Monitoring Active • Scanning channels every 30s")
            self.pill_power.setText("caffeinate: active")
            self.pill_power.setProperty("class", "BadgePill BadgeActive")
        else:
            self.btn_toggle.setText("Start Watchdog")
            self.btn_toggle.setObjectName("PrimaryButton")
            self.lbl_ribbon_status.setText("Standby • Monitoring disabled")
            self.pill_power.setText("caffeinate: idle")
            self.pill_power.setProperty("class", "BadgePill BadgeMuted")

        self.btn_toggle.style().unpolish(self.btn_toggle)
        self.btn_toggle.style().polish(self.btn_toggle)
        self.pill_power.style().unpolish(self.pill_power)
        self.pill_power.style().polish(self.pill_power)

    def add_task(self):
        text = self.input_task.text().strip()
        if text:
            with open("TASKS.md", "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] {text}")
            self.input_task.clear()
            self.refresh_states()

    def test_phone_alert(self):
        try:
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            notifier = Notifier(cfg.get("notifications", {}))
            notifier.send("⚡ Test alert dispatched from DeskResumer Native Desktop UI.")
            QMessageBox.information(self, "Alert Sent", "Dispatched test push notification!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send alert: {e}")

    def open_preferences(self):
        dlg = PreferencesDialog(self, self.config_path)
        dlg.exec()


class CustomTaskItem(QWidget):
    """Custom checklist item with real checkbox."""
    def __init__(self, line_id: int, text: str, completed: bool, window_ref):
        super().__init__()
        self.line_id = line_id
        self.window = window_ref
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        from PySide6.QtWidgets import QCheckBox
        self.cb = QCheckBox(text)
        self.cb.setChecked(completed)
        self.cb.stateChanged.connect(self._toggle)
        layout.addWidget(self.cb)
        layout.addStretch()

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(20, 20)
        btn_del.setStyleSheet("border: none; color: #64748b; font-size: 11px;")
        btn_del.clicked.connect(self._delete)
        layout.addWidget(btn_del)

    def _toggle(self, state):
        p = Path("TASKS.md")
        if p.exists():
            import re
            lines = []
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 0 <= self.line_id < len(lines):
                if state:
                    lines[self.line_id] = re.sub(r"\[\s*\]", "[x]", lines[self.line_id], count=1)
                else:
                    lines[self.line_id] = re.sub(r"\[[xX]\]", "[ ]", lines[self.line_id], count=1)
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            self.window.refresh_states()

    def _delete(self):
        p = Path("TASKS.md")
        if p.exists():
            lines = []
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if 0 <= self.line_id < len(lines):
                del lines[self.line_id]
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            self.window.refresh_states()
