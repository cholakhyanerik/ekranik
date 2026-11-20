"""Ekranik: screen and audio recorder for Windows."""

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ekranik import i18n, settings
from ekranik.ui import theme
from ekranik.ui.main_window import MainWindow

APP_NAME = "Ekranik"
"""Organization and application name: the QSettings location and the window title."""

STYLE = "windows11"
"""Qt's native Windows 11 style (CLAUDE.md, rule 15)."""


def configure_app(app: QApplication) -> None:
    """Set the app up: its name (for settings and window titles), style, theme,
    settings and language."""
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle(STYLE)
    # QSettings() and QSettings(scope) then use INI too. QSettings(org, app)
    # ignores this and writes the registry: open settings through settings.py.
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    theme.install(app)
    settings.install(app)
    i18n.install(app)


def main() -> int:
    """Start Ekranik; the return value is the process exit code."""
    app = QApplication(sys.argv)
    configure_app(app)
    window = MainWindow()
    window.show()
    return app.exec()
