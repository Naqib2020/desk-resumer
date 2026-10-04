"""
Sleek dark theme stylesheets and palette for DeskResumer Native UI.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QWidget {
    background-color: #0b0d12;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    font-size: 13px;
    outline: none;
}

/* Main Dashboard Panel */
#MainContainer {
    background-color: #0b0d12;
    border: 1px solid #1e2433;
    border-radius: 10px;
}

/* Header */
#HeaderFrame {
    background-color: #121620;
    border-bottom: 1px solid #1e2433;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
}

#AppTitle {
    font-size: 13px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.2px;
}

#AppSubtitle {
    font-size: 11px;
    color: #64748b;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
}

/* Cards */
.CardFrame {
    background-color: #12151f;
    border: 1px solid #1e2433;
    border-radius: 8px;
}
.CardFrame:hover {
    border: 1px solid #2d354a;
}

.CardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #cbd5e1;
}

/* Data Labels */
.DataKey {
    font-size: 11px;
    color: #64748b;
}

.DataVal {
    font-size: 12px;
    font-weight: 500;
    color: #f1f5f9;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
}

/* Status Badges */
.BadgePill {
    font-size: 10px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    letter-spacing: 0.5px;
}
.BadgeActive {
    background-color: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
}
.BadgeAmber {
    background-color: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.25);
}
.BadgeMuted {
    background-color: #1a202c;
    color: #94a3b8;
    border: 1px solid #2d3748;
}

/* Push Buttons */
QPushButton {
    background-color: #171c28;
    color: #e2e8f0;
    border: 1px solid #262e42;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #1f2638;
    border-color: #3b4664;
}
QPushButton:pressed {
    background-color: #131722;
}

QPushButton#PrimaryButton {
    background-color: #f8fafc;
    color: #0b0d12;
    border: 1px solid #f8fafc;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background-color: #e2e8f0;
    border-color: #e2e8f0;
}

QPushButton#StopButton {
    background-color: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.25);
}
QPushButton#StopButton:hover {
    background-color: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
}

/* Task Checklist */
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    background-color: transparent;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.02);
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #334155;
    border-radius: 3px;
    background-color: #0f121a;
}
QCheckBox::indicator:hover {
    border-color: #475569;
}
QCheckBox::indicator:checked {
    background-color: #f8fafc;
    border-color: #f8fafc;
}

/* Line Inputs */
QLineEdit, QSpinBox, QComboBox {
    background-color: #121622;
    border: 1px solid #232b3d;
    border-radius: 5px;
    padding: 6px 10px;
    color: #f1f5f9;
    font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #3b82f6;
}

/* Progress Bar */
QProgressBar {
    background-color: #171c28;
    border: none;
    border-radius: 2px;
    height: 3px;
    text-align: right;
}
QProgressBar::chunk {
    background-color: #f8fafc;
    border-radius: 2px;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #283144;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #3c4964;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
