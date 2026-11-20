"""The settings window: values in effect, live changes, Cancel, keyboard (EKR-5)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import QDir, Qt, QTranslator
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QLabel,
    QPushButton,
    QTabBar,
    QTabWidget,
    QWidget,
)
from pytestqt.qtbot import QtBot

from ekranik import settings
from ekranik.settings import FrameRate, Settings
from ekranik.ui import settings_dialog, theme
from ekranik.ui.main_window import SETTINGS_SHORTCUT, MainWindow
from ekranik.ui.settings_dialog import SettingsDialog
from ekranik.ui.widgets import Card, ElidedLabel


@pytest.fixture
def current(qapp: QApplication) -> Settings:
    return settings.install(qapp)


class Picker:
    """Stands in for the folder picker: answers what the test queued, records the start."""

    def __init__(self) -> None:
        self.answers: list[str] = []
        self.starts: list[str] = []

    def __call__(self, _parent: QWidget, _caption: str, start: str) -> str:
        self.starts.append(start)
        return self.answers.pop(0)


@pytest.fixture
def picker(monkeypatch: pytest.MonkeyPatch) -> Picker:
    picker = Picker()
    monkeypatch.setattr(settings_dialog, "pick_folder", picker)
    return picker


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    """The main window; the test holds it, since pytest-qt keeps only weak references."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture
def open_dialog(qtbot: QtBot, window: MainWindow) -> Callable[[], SettingsDialog]:
    """Opens the settings from the main window, once the test has set things up."""

    def open_dialog() -> SettingsDialog:
        dialog = window.open_settings()
        qtbot.waitExposed(dialog)
        return dialog

    return open_dialog


def button(dialog: QDialog, text: str, index: int = 0) -> QPushButton:
    found = [b for b in dialog.findChildren(QPushButton) if b.text() == text]
    return found[index]


def card_of(widget: QWidget) -> Card:
    parent = widget.parentWidget()
    assert isinstance(parent, Card)
    return parent


def frame_rate_box(dialog: QDialog) -> QComboBox:
    (box,) = dialog.findChildren(QComboBox)
    return box


def microphone_box(dialog: QDialog) -> QCheckBox:
    (box,) = dialog.findChildren(QCheckBox)
    return box


def file_text(current: Settings) -> str:
    return Path(current.store.fileName()).read_text(encoding="utf-8")


def test_the_window_shows_the_settings_in_effect(
    qtbot: QtBot, open_dialog: Callable[[], SettingsDialog], current: Settings
) -> None:
    current.frame_rate = FrameRate.FPS_30
    current.microphone = False
    dialog = open_dialog()
    assert dialog.windowTitle() == "Settings"
    assert frame_rate_box(dialog).currentText() == "30 fps"
    assert not microphone_box(dialog).isChecked()
    screen = card_of(button(dialog, "Browse…", 0))
    audio = card_of(button(dialog, "Browse…", 1))
    assert screen.title.text() == "Screen recordings"
    assert screen.hint.text() == QDir.toNativeSeparators(current.screen_folder)
    assert audio.hint.text() == QDir.toNativeSeparators(current.audio_folder)
    # A screen reader names each control after its card.
    assert frame_rate_box(dialog).accessibleName() == "Frame rate"
    # A button says which card it belongs to: there are two "Browse…".
    assert button(dialog, "Browse…").accessibleDescription() == (
        f"Screen recordings\n{screen.hint.text()}"
    )


def test_a_change_applies_at_once_and_enter_keeps_it(
    qtbot: QtBot, open_dialog: Callable[[], SettingsDialog], current: Settings
) -> None:
    current.frame_rate = FrameRate.SCREEN
    dialog = open_dialog()
    box = frame_rate_box(dialog)
    with qtbot.waitSignal(current.changed) as changed:
        qtbot.keyClick(box, Qt.Key.Key_Down)  # from the keyboard, as a user would
    assert changed.args == [Settings.frame_rate.key]
    assert current.frame_rate is FrameRate.FPS_60
    with qtbot.waitSignal(dialog.finished):
        qtbot.keyClick(box, Qt.Key.Key_Return)
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert current.frame_rate is FrameRate.FPS_60
    # Written by the event loop, as in the app.
    qtbot.waitUntil(lambda: "frame_rate=60" in file_text(current))


@pytest.mark.parametrize("close", ["escape", "cancel", "window"])
def test_cancel_takes_back_every_change(
    qtbot: QtBot,
    open_dialog: Callable[[], SettingsDialog],
    current: Settings,
    picker: Picker,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close: str,
) -> None:
    current.frame_rate = FrameRate.FPS_30
    current.microphone = True
    del current.audio_folder  # follows Windows: must not get pinned by Cancel
    monkeypatch.setattr(Settings.audio_folder, "default", lambda: "E:/Music/Ekranik")
    chosen_screen = current.screen_folder
    dialog = open_dialog()

    qtbot.keyClick(frame_rate_box(dialog), Qt.Key.Key_Up)
    qtbot.mouseClick(microphone_box(dialog), Qt.MouseButton.LeftButton)
    picker.answers.append(str(tmp_path))
    qtbot.mouseClick(button(dialog, "Browse…", 1), Qt.MouseButton.LeftButton)
    qtbot.mouseClick(button(dialog, "Restore default", 0), Qt.MouseButton.LeftButton)
    assert current.frame_rate is FrameRate.FPS_60
    assert current.microphone is False
    assert current.audio_folder == QDir.fromNativeSeparators(str(tmp_path))
    assert not current.store.contains(Settings.screen_folder.key)

    announced: list[str] = []
    current.changed.connect(announced.append)
    with qtbot.waitSignal(dialog.finished):
        match close:
            case "escape":
                qtbot.keyClick(dialog, Qt.Key.Key_Escape)
            case "cancel":
                qtbot.mouseClick(button(dialog, "Cancel"), Qt.MouseButton.LeftButton)
            case "window":
                dialog.close()
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert current.frame_rate is FrameRate.FPS_30
    assert current.microphone is True
    assert current.screen_folder == chosen_screen
    assert current.audio_folder == "E:/Music/Ekranik"
    assert not current.store.contains(Settings.audio_folder.key)
    assert sorted(announced) == sorted(
        setting.key
        for setting in (
            Settings.frame_rate,
            Settings.microphone,
            Settings.audio_folder,
            Settings.screen_folder,
        )
    )


def test_a_picked_folder_is_chosen_and_restore_default_unpins_it(
    qtbot: QtBot,
    open_dialog: Callable[[], SettingsDialog],
    current: Settings,
    picker: Picker,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del current.screen_folder
    missing = tmp_path / "Videos" / "Ekranik"  # made by the first recording
    monkeypatch.setattr(Settings.screen_folder, "default", lambda: missing.as_posix())
    dialog = open_dialog()
    browse, restore = button(dialog, "Browse…", 0), button(dialog, "Restore default", 0)
    assert not restore.isEnabled()

    # Cancelled: nothing changes, and the folder still follows Windows.
    picker.answers.append("")
    qtbot.mouseClick(browse, Qt.MouseButton.LeftButton)
    assert not current.store.contains(Settings.screen_folder.key)
    # The default folder doesn't exist yet: the picker opens in its parent.
    assert picker.starts == [str(missing.parent)]

    picker.answers.append(str(tmp_path))
    qtbot.mouseClick(browse, Qt.MouseButton.LeftButton)
    assert current.screen_folder == tmp_path.as_posix()
    assert card_of(browse).hint.text() == str(tmp_path)
    assert restore.isEnabled()

    qtbot.mouseClick(restore, Qt.MouseButton.LeftButton)
    assert not current.store.contains(Settings.screen_folder.key)
    assert card_of(browse).hint.text() == str(missing)
    assert not restore.isEnabled()


def test_a_folder_that_cant_be_used_is_refused_with_a_message(
    qtbot: QtBot,
    open_dialog: Callable[[], SettingsDialog],
    current: Settings,
    picker: Picker,
    tmp_path: Path,
) -> None:
    before = current.screen_folder
    dialog = open_dialog()
    browse = button(dialog, "Browse…", 0)
    picker.answers.append("D:/\u202ecer")  # a hidden text-direction character
    qtbot.mouseClick(browse, Qt.MouseButton.LeftButton)
    assert current.screen_folder == before
    assert card_of(browse).error.isVisibleTo(dialog)
    assert "Choose another folder" in card_of(browse).error.text()
    picker.answers.append(str(tmp_path))
    qtbot.mouseClick(browse, Qt.MouseButton.LeftButton)
    assert current.screen_folder == tmp_path.as_posix()
    assert not card_of(browse).error.isVisibleTo(dialog)


def tab_cycle(qtbot: QtBot, dialog: QDialog, start: QWidget) -> list[QWidget]:
    """The widgets Tab visits, from ``start`` until it comes back."""
    start.setFocus()
    seen = [start]
    for _ in range(100):
        qtbot.keyClick(dialog.focusWidget(), Qt.Key.Key_Tab)
        if dialog.focusWidget() is start:
            return seen
        seen.append(dialog.focusWidget())
    raise AssertionError(f"Tab never came back: {seen}")


def test_every_control_is_reachable_with_the_keyboard(
    qtbot: QtBot, open_dialog: Callable[[], SettingsDialog]
) -> None:
    dialog = open_dialog()
    tabs = dialog.findChild(QTabWidget)
    tab_bar = tabs.findChild(QTabBar)
    for index in range(tabs.count()):
        if index:
            qtbot.keyClick(
                dialog.focusWidget(),
                Qt.Key.Key_Tab,
                Qt.KeyboardModifier.ControlModifier,
            )
        assert tabs.currentIndex() == index
        reached = tab_cycle(qtbot, dialog, tab_bar)
        controls = [
            widget
            for widget in dialog.findChildren(QWidget)
            if isinstance(widget, (QAbstractButton, QComboBox))
            and widget.isVisibleTo(dialog)
            and widget.isEnabled()
            and not isinstance(widget.parentWidget(), QTabBar)  # its scroll arrows
        ]
        assert controls
        assert [w for w in controls if w not in reached] == []


def test_the_main_window_opens_the_settings(qtbot: QtBot, window: MainWindow) -> None:
    assert window.settings_button.text() == "Settings"
    assert "Ctrl+," in window.settings_button.toolTip()
    qtbot.mouseClick(window.settings_button, Qt.MouseButton.LeftButton)
    (dialog,) = window.findChildren(SettingsDialog)
    assert dialog.isVisible()
    assert dialog.windowModality() == Qt.WindowModality.WindowModal
    with qtbot.waitSignal(dialog.destroyed):
        dialog.reject()  # deleted on close: the next opening starts fresh
    (action,) = [a for a in window.actions() if a.shortcut() == SETTINGS_SHORTCUT]
    action.trigger()
    assert len(window.findChildren(SettingsDialog)) == 1


class Brackets(QTranslator):
    """A language where every text is its English source in brackets."""

    def translate(
        self,
        context: str,
        source: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        return f"[{source}]"

    def isEmpty(self) -> bool:
        return False


def visible_texts(window: QWidget) -> dict[str, str]:
    """Every text a user or a screen reader gets from a window and its children."""
    texts = {"title": window.windowTitle()}
    for number, widget in enumerate(window.findChildren(QWidget)):
        if isinstance(widget, ElidedLabel):
            continue  # a folder path: data, not text
        if isinstance(widget.parentWidget(), QTabBar):
            continue  # its scroll arrows: Qt's own texts, in Qt's translations
        if isinstance(widget, QLabel | QAbstractButton) and widget.text():
            texts[f"{number}:{type(widget).__name__}"] = widget.text()
        if isinstance(widget, QComboBox):
            for item in range(widget.count()):
                texts[f"{number}:item {item}"] = widget.itemText(item)
        if isinstance(widget, QTabWidget):
            for tab in range(widget.count()):
                texts[f"{number}:tab {tab}"] = widget.tabText(tab)
        if widget.accessibleName():
            texts[f"{number}:name"] = widget.accessibleName()
    return texts


def test_every_text_follows_a_language_change(
    qtbot: QtBot,
    qapp: QApplication,
    window: MainWindow,
    open_dialog: Callable[[], SettingsDialog],
    picker: Picker,
) -> None:
    dialog = open_dialog()
    picker.answers.append("D:/\u202ecer")  # so the error text shows too
    qtbot.mouseClick(button(dialog, "Browse…"), Qt.MouseButton.LeftButton)
    english = visible_texts(dialog) | visible_texts(window)
    brackets = Brackets()
    qapp.installTranslator(brackets)
    try:
        qtbot.waitUntil(lambda: dialog.windowTitle() == "[Settings]")
        qtbot.wait(10)  # every posted language change has arrived
        translated = visible_texts(dialog)
        translated |= {
            key: text
            for key, text in visible_texts(window).items()
            if key != "title"  # the main window's title is the brand
        }
        assert {
            key: text
            for key, text in translated.items()
            if not (text.startswith("[") and text.endswith("]"))
        } == {}
        assert window.settings_button.toolTip().startswith("[Settings] (")
    finally:
        qapp.removeTranslator(brackets)
    qtbot.waitUntil(lambda: dialog.windowTitle() == "Settings")
    qtbot.wait(10)
    assert visible_texts(dialog) | visible_texts(window) == english


def test_push_buttons_keep_their_own_name_for_screen_readers(
    open_dialog: Callable[[], SettingsDialog],
) -> None:
    dialog = open_dialog()
    for name in ("Browse…", "Restore default"):
        for index in (0, 1):
            control = button(dialog, name, index)
            assert control.accessibleName() in ("", name)
            # The folder it is about, in the description.
            card = card_of(control)
            assert control.accessibleDescription() == (
                f"{card.title.text()}\n{card.hint.text()}"
            )


def test_restore_default_keeps_the_focus_in_its_card(
    qtbot: QtBot, open_dialog: Callable[[], SettingsDialog]
) -> None:
    dialog = open_dialog()
    restore = button(dialog, "Restore default", 0)
    restore.setFocus()
    qtbot.keyClick(restore, Qt.Key.Key_Space)
    assert not restore.isEnabled()
    # Not the next card's "Browse…", where Enter would open the wrong picker.
    assert dialog.focusWidget() is button(dialog, "Browse…", 0)


def test_the_window_grows_with_the_windows_text_size(
    qapp: QApplication,
    open_dialog: Callable[[], SettingsDialog],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(theme.install(qapp), "_body_px", 2 * theme.WINDOWS_BODY_PX)
    dialog = open_dialog()
    screen = dialog.screen().availableGeometry().size()
    expected = (2 * theme.SETTINGS_WINDOW_SIZE).boundedTo(screen)
    assert dialog.size() == expected


def test_a_refused_folder_is_told_to_screen_readers_too(
    qtbot: QtBot, open_dialog: Callable[[], SettingsDialog], picker: Picker
) -> None:
    dialog = open_dialog()
    browse = button(dialog, "Browse…", 0)
    picker.answers.append("D:/\u202ecer")
    qtbot.mouseClick(browse, Qt.MouseButton.LeftButton)
    assert browse.accessibleDescription().endswith(card_of(browse).error.text())
