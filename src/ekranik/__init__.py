"""Ekranik: screen and audio recorder for Windows."""

import sys

from PySide6.QtWidgets import QApplication

from ekranik.ui.main_window import MainWindow

APP_NAME = "Ekranik"
"""Organization and application name: the QSettings location and the window title."""

STYLE = "windows11"
"""Qt's native Windows 11 style (CLAUDE.md, rule 15)."""


def configure_app(app: QApplication) -> None:
    """Give the app its name, which QSettings and window titles use, and its style."""
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle(STYLE)


def main() -> int:
    """Start Ekranik; the return value is the process exit code."""
    app = QApplication(sys.argv)
    configure_app(app)
    window = MainWindow()
    window.show()
    return app.exec()
