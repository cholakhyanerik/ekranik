"""The main window."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ekranik.ui import theme

if TYPE_CHECKING:
    from ekranik.ui.settings_dialog import SettingsDialog

SETTINGS_SHORTCUT = QKeySequence("Ctrl+,")
"""Opens the settings, as in Windows Terminal and Visual Studio Code."""


class MainWindow(QMainWindow):
    """Ekranik's main window; the recording controls go here."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The app's name, a brand that stays the same in every language.
        self.setWindowTitle(QGuiApplication.applicationDisplayName())
        self.resize(theme.MAIN_WINDOW_SIZE)

        self._settings_action = QAction(self)
        self._settings_action.setShortcut(SETTINGS_SHORTCUT)
        self._settings_action.triggered.connect(self.open_settings)
        self.addAction(self._settings_action)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self.open_settings)

        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(self.settings_button)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(*(theme.Spacing.L,) * 4)
        layout.addLayout(top)
        layout.addStretch()
        self.setCentralWidget(central)
        self.retranslate()

    def retranslate(self) -> None:
        """Set every text in the current language."""
        settings = self.tr("Settings")
        self.settings_button.setText(settings)
        shortcut = SETTINGS_SHORTCUT.toString(QKeySequence.SequenceFormat.NativeText)
        self.settings_button.setToolTip(f"{settings} ({shortcut})")

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)

    def open_settings(self) -> SettingsDialog:
        """Open the settings window over this one; it is deleted when it closes."""
        # Imported on first use: loading its widget classes cost 7-10 ms at
        # startup (2026-11-20), for a window most starts never open.
        from ekranik.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()
        return dialog
