"""The main window."""

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow, QWidget

from ekranik.ui import theme


class MainWindow(QMainWindow):
    """Ekranik's main window; the recording controls go here."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The app's name, a brand that stays the same in every language.
        self.setWindowTitle(QGuiApplication.applicationDisplayName())
        self.resize(theme.MAIN_WINDOW_SIZE)
