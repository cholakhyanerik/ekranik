"""The main window."""

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow, QWidget

DEFAULT_SIZE = QSize(640, 400)
"""Size on first open, in device-independent pixels; EKR-3 moves it into the theme."""


class MainWindow(QMainWindow):
    """Ekranik's main window; the recording controls go here."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The app's name, a brand that stays the same in every language.
        self.setWindowTitle(QGuiApplication.applicationDisplayName())
        self.resize(DEFAULT_SIZE)
