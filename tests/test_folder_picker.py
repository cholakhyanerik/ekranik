"""The folder picker: Windows' own dialog, and nothing in Qt's shared registry key."""

import ctypes
import uuid
import winreg
from ctypes import wintypes
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget
from pytestqt.qtbot import QtBot

from ekranik.ui import folder_picker
from ekranik.ui.folder_picker import FolderDialog

SRC = Path(__file__).parents[1] / "src" / "ekranik"
WM_CLOSE = 0x10
WM_COMMAND = 0x111
IDOK = 1

user32 = ctypes.WinDLL("user32")
user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
user32.FindWindowW.restype = wintypes.HWND
user32.PostMessageW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
user32.PostMessageW.restype = wintypes.BOOL


def qt_shared_file_dialog_key() -> tuple[int, int] | None:
    r"""When Qt's shared file-dialog key last changed, and its number of values.

    Only these: the values are other apps' folders. Opened read-only with
    winreg, since QSettings would create the key just by reading it.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\QtProject\OrganizationDefaults\FileDialog",
            0,
            winreg.KEY_READ,
        ) as key:
            _subkeys, values, changed = winreg.QueryInfoKey(key)
    except FileNotFoundError:
        return None
    return values, changed


@pytest.mark.parametrize("spelling", ["windows", "qt"])
def test_the_dialog_picks_folders_and_opens_in_the_start_folder(
    tmp_path: Path, spelling: str
) -> None:
    # Settings keep folders with Qt's forward slashes.
    start = str(tmp_path) if spelling == "windows" else tmp_path.as_posix()
    with FolderDialog("Screen recordings", start) as dialog:
        assert dialog.options() & folder_picker.OPTIONS == folder_picker.OPTIONS
        assert Path(dialog.folder()) == tmp_path


def test_a_missing_start_folder_is_left_to_windows(tmp_path: Path) -> None:
    with FolderDialog("Screen recordings", str(tmp_path / "missing")) as dialog:
        assert Path(dialog.folder()) != tmp_path / "missing"


@pytest.mark.parametrize("answer", ["cancel", "select"])
def test_the_dialog_returns_the_folder_and_qt_keeps_nothing(
    qtbot: QtBot, qapp: QApplication, tmp_path: Path, answer: str
) -> None:
    if qapp.platformName() == "offscreen":
        pytest.skip("the dialog needs a real window to show over")
    owner = QWidget()
    qtbot.addWidget(owner)
    with qtbot.waitExposed(owner):
        owner.show()
    before = qt_shared_file_dialog_key()
    caption = f"Ekranik test {uuid.uuid4()}"
    found: list[int] = []

    def answer_once_shown() -> None:
        # What the user does, as soon as Windows shows the dialog: closes it, or
        # presses "Select Folder" in the folder it opened in.
        if hwnd := user32.FindWindowW("#32770", caption):
            poll.stop()
            found.append(hwnd)
            if answer == "cancel":
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            else:
                user32.PostMessageW(hwnd, WM_COMMAND, IDOK, 0)

    poll = QTimer()
    poll.setInterval(20)
    poll.timeout.connect(answer_once_shown)
    poll.start()
    try:
        chosen = folder_picker.pick_folder(owner, caption, str(tmp_path))
    finally:
        poll.stop()
    assert found
    assert chosen == ("" if answer == "cancel" else str(tmp_path))
    assert qt_shared_file_dialog_key() == before


def test_no_qfiledialog_anywhere() -> None:
    # Every QFileDialog writes to the registry key all Qt apps share.
    users = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if "QFileDialog"
        in path.read_text(encoding="utf-8").replace("``QFileDialog``", "")
    ]
    assert users == []
