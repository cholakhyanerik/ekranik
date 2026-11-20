"""The settings window: every setting in one place, applied as soon as it changes.

OK or Enter keeps the changes; Cancel, Esc or closing the window takes back
everything changed since it opened. Only what the user changes is stored: an
assignment pins a value (CLAUDE.md, decision log), so a folder left alone keeps
following Windows.
"""

from pathlib import PureWindowsPath
from typing import NamedTuple

from PySide6.QtCore import QDir, QEvent, QFileInfo, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ekranik import settings
from ekranik.settings import FrameRate, Setting, Settings
from ekranik.ui import theme
from ekranik.ui.folder_picker import pick_folder
from ekranik.ui.widgets import Card, ComboBox, ElidedLabel


class Folder(NamedTuple):
    """The card of one recording folder."""

    setting: Setting[str]
    card: Card
    browse: QPushButton
    restore: QPushButton


def page(*sections: tuple[QLabel, tuple[QWidget, ...]]) -> QScrollArea:
    """A settings page: headed groups of cards, scrolling when they don't fit."""
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, theme.Spacing.L, 0, 0)
    layout.setSpacing(theme.Spacing.XS)
    for number, (heading, cards) in enumerate(sections):
        theme.set_role(heading, theme.Role.HEADING)
        if number:
            layout.addSpacing(theme.Spacing.XL - theme.Spacing.XS)
        layout.addWidget(heading)
        layout.addSpacing(theme.Spacing.S - theme.Spacing.XS)
        for card in cards:
            layout.addWidget(card)
    layout.addStretch()
    area = QScrollArea()
    area.setWidget(content)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    # The cards' controls take the focus; the area itself would be a dead stop.
    area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return area


class SettingsDialog(QDialog):
    """Ekranik's settings window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings.install(QApplication.instance())
        self._before: dict[str, tuple[Setting[object], object | None]] = {}
        """What the file held before this window changed a setting, for Cancel."""
        self._refused: set[str] = set()
        """Folders whose last pick could not be used."""

        self._folders = tuple(
            self._folder(setting)
            for setting in (Settings.screen_folder, Settings.audio_folder)
        )
        self._frame_rate = ComboBox()
        for rate in FrameRate:
            self._frame_rate.addItem("", rate.value)
        self._frame_rate.activated.connect(self._frame_rate_chosen)
        self._frame_rate_card = Card(self._frame_rate)
        self._microphone = QCheckBox()
        self._microphone.clicked.connect(self._microphone_chosen)
        self._microphone_card = Card(self._microphone)
        self._folders_heading = QLabel()
        self._screen_heading = QLabel()

        self._tabs = QTabWidget()
        # No pane frame: the cards lie on the window's background, as in Windows 11.
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(
            page(
                (self._folders_heading, tuple(folder.card for folder in self._folders)),
                (self._screen_heading, (self._frame_rate_card, self._microphone_card)),
            ),
            "",
        )
        # Our own buttons, not Qt's standard ones: Qt has no Armenian for those,
        # and it resets their texts on every language change.
        buttons = QDialogButtonBox()
        self._ok = buttons.addButton("", QDialogButtonBox.ButtonRole.AcceptRole)
        self._cancel = buttons.addButton("", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(theme.Spacing.XL,) * 4)
        layout.setSpacing(theme.Spacing.XL)
        layout.addWidget(self._tabs)
        layout.addWidget(buttons)
        size = theme.for_text_size(
            theme.SETTINGS_WINDOW_SIZE, theme.install(QApplication.instance()).body_px
        )
        self.resize(size.boundedTo(self.screen().availableGeometry().size()))

        self._settings.changed.connect(self._load)
        self.retranslate()
        self._load()

    def _folder(self, setting: Setting[str]) -> Folder:
        browse = QPushButton()
        restore = QPushButton()
        folder = Folder(
            setting, Card(browse, restore, hint=ElidedLabel()), browse, restore
        )
        browse.clicked.connect(lambda: self._browse(folder))
        restore.clicked.connect(lambda: self._restore_default(folder))
        return folder

    def retranslate(self) -> None:
        """Set every text in the current language."""
        self.setWindowTitle(self.tr("Settings"))
        self._tabs.setTabText(0, self.tr("Recording"))
        self._folders_heading.setText(self.tr("Folders"))
        screen, audio = self._folders
        screen.card.set_title(self.tr("Screen recordings"))
        audio.card.set_title(self.tr("Audio recordings"))
        for folder in self._folders:
            folder.browse.setText(self.tr("Browse…"))
            folder.restore.setText(self.tr("Restore default"))
        self._show_refused()
        self._screen_heading.setText(self.tr("Screen recording"))
        self._frame_rate_card.set_title(self.tr("Frame rate"))
        self._frame_rate_card.set_hint(
            self.tr("Frames per second in screen recordings.")
        )
        for index, text in enumerate(
            (self.tr("Screen refresh rate"), self.tr("60 fps"), self.tr("30 fps"))
        ):
            self._frame_rate.setItemText(index, text)
        self._microphone_card.set_title(self.tr("Microphone"))
        self._microphone_card.set_hint(
            self.tr("Include the sound from your microphone in new screen recordings.")
        )
        self._ok.setText(self.tr("OK"))
        self._cancel.setText(self.tr("Cancel"))

    def _show_refused(self) -> None:
        for folder in self._folders:
            folder.card.set_error(
                self.tr("Recordings can't be saved there. Choose another folder.")
                if folder.setting.key in self._refused
                else ""
            )

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)

    def _load(self, _key: str = "") -> None:
        """Show the settings in effect."""
        for folder in self._folders:
            path = getattr(self._settings, folder.setting.name)
            folder.card.set_hint(QDir.toNativeSeparators(path))
            folder.restore.setEnabled(folder.setting.stored(self._settings) is not None)
        self._frame_rate.setCurrentIndex(
            list(FrameRate).index(self._settings.frame_rate)
        )
        self._microphone.setChecked(self._settings.microphone)

    def _remember(self, setting: Setting[object]) -> None:
        self._before.setdefault(setting.key, (setting, setting.raw(self._settings)))

    def _choose(self, setting: Setting[object], value: object) -> None:
        self._remember(setting)
        setattr(self._settings, setting.name, value)
        self._load()

    def _frame_rate_chosen(self, index: int) -> None:
        self._choose(Settings.frame_rate, list(FrameRate)[index])

    def _microphone_chosen(self, checked: bool) -> None:
        self._choose(Settings.microphone, checked)

    def _browse(self, folder: Folder) -> None:
        current = getattr(self._settings, folder.setting.name)
        start = current
        if (
            folder.setting.stored(self._settings) is None
            and not QFileInfo(current).isDir()
        ):
            # The default folder is made with the first recording: open in Videos or Music.
            start = str(PureWindowsPath(current).parent)
        chosen = pick_folder(self, folder.card.title.text(), start)
        if not chosen:
            return
        try:
            value = folder.setting.parse(chosen)
        except ValueError:
            self._refused.add(folder.setting.key)
        else:
            self._refused.discard(folder.setting.key)
            self._choose(folder.setting, value)
        self._show_refused()

    def _restore_default(self, folder: Folder) -> None:
        if self.focusWidget() is folder.restore:
            # It is disabled next; keep the focus in this card, not the next one.
            folder.browse.setFocus(Qt.FocusReason.OtherFocusReason)
        self._remember(folder.setting)
        self._refused.discard(folder.setting.key)
        delattr(self._settings, folder.setting.name)
        self._show_refused()
        self._load()

    def reject(self) -> None:
        """Take back every change made in this window, then close it."""
        for setting, raw in self._before.values():
            setting.restore(self._settings, raw)
        self._before.clear()
        super().reject()
