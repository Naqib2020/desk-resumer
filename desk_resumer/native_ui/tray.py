"""
Native System Tray integration using QSystemTrayIcon.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from .window import DeskResumerMainWindow


def create_tray_icon_pixmap(color_hex="#10b981") -> QPixmap:
    """Dynamically creates a high-res monochrome geometric tray icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Base shape: sharp hexagon
    painter.setBrush(QColor("#ffffff"))
    painter.setPen(Qt.NoPen)
    from PySide6.QtGui import QPolygonF
    from PySide6.QtCore import QPointF
    points = [
        QPointF(16, 2), QPointF(29, 9), QPointF(29, 23),
        QPointF(16, 30), QPointF(3, 23), QPointF(3, 9)
    ]
    painter.drawPolygon(QPolygonF(points))

    # Inner cutout
    painter.setBrush(QColor("#000000"))
    inner_points = [
        QPointF(16, 8), QPointF(23, 12), QPointF(23, 20),
        QPointF(16, 24), QPointF(9, 20), QPointF(9, 12)
    ]
    painter.drawPolygon(QPolygonF(inner_points))

    # Status indicator dot in bottom-right corner
    painter.setBrush(QColor(color_hex))
    painter.drawEllipse(18, 18, 12, 12)
    painter.end()
    return pixmap


def run_native_app(config_path="config.yaml"):
    """Launches the PySide6 Native System Tray Application."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = DeskResumerMainWindow(config_path)

    # Override closeEvent to minimize to tray instead of quitting
    original_close = window.closeEvent
    def _close_event(event):
        window.hide()
        event.ignore()
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray.showMessage(
                "DeskResumer",
                "Application minimized to menu bar. Monitoring remains active.",
                QSystemTrayIcon.Information,
                2000
            )
    window.closeEvent = _close_event

    # Create System Tray Icon
    tray = QSystemTrayIcon(QIcon(create_tray_icon_pixmap("#64748b")), app)
    tray.setToolTip("DeskResumer - Autonomous Cooldown Supervisor")

    # Tray Menu
    menu = QMenu()
    act_show = QAction("Show Dashboard", menu)
    act_show.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
    menu.addAction(act_show)

    menu.addSeparator()

    act_toggle = QAction("Start / Stop Watchdog", menu)
    act_toggle.triggered.connect(window.toggle_monitoring)
    menu.addAction(act_toggle)

    act_prefs = QAction("Preferences...", menu)
    act_prefs.triggered.connect(window.open_preferences)
    menu.addAction(act_prefs)

    menu.addSeparator()

    act_quit = QAction("Quit DeskResumer", menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)

    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: (
        window.show(), window.raise_(), window.activateWindow()
    ) if reason in [QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick] else None)

    tray.show()
    window.show()

    sys.exit(app.exec())
