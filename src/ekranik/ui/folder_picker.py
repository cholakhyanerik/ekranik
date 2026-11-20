r"""Windows' folder picker, called directly instead of through Qt.

Qt's ``QFileDialog`` shows this same Windows dialog, but every ``QFileDialog``
writes the folder the user last browsed to ``HKCU\Software\QtProject``, a
registry key that all Qt apps of the user share, and reads it back; nothing
turns that off (Qt 6.12 source, checked 2026-11-20). Ekranik writes nothing to
the registry, so it calls Windows' ``IFileOpenDialog`` itself, through ctypes.
Windows itself remembers the dialog's size per program (``ComDlg32\CIDSizeMRU``,
no paths); the folder stays out of its recent lists (``DONT_ADD_TO_RECENT``).
The dialog speaks the Windows display language; only its title is Ekranik's.

The dialog runs on the GUI thread in its own modal loop, as Qt's does; Qt's
windows keep painting and its timers keep firing meanwhile. Don't use
``QFileDialog`` anywhere (a test checks).
"""

import ctypes
import uuid
from ctypes import wintypes
from enum import IntFlag
from types import TracebackType
from typing import Self

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QWidget


class _GUID(ctypes.Structure):
    _fields_ = (
        ("data1", wintypes.DWORD),
        ("data2", wintypes.WORD),
        ("data3", wintypes.WORD),
        ("data4", ctypes.c_ubyte * 8),
    )


def _guid(text: str) -> _GUID:
    return _GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


_CLSID_FILE_OPEN_DIALOG = _guid("dc1c5a9c-e88a-4dde-a5a1-60f82a20aef7")
_IID_FILE_OPEN_DIALOG = _guid("d57c7288-d4ad-4768-be02-9d969532d960")
_IID_SHELL_ITEM = _guid("43826d1e-e718-42ee-bc55-a1e261c37bfe")
_CLSCTX_INPROC_SERVER = 0x1
_COINIT_APARTMENTTHREADED = 0x2
_SIGDN_FILESYSPATH = -0x7FFA8000  # 0x80058000 as a signed 32-bit value

CANCELLED = -0x7FF8FB39
"""HRESULT_FROM_WIN32(ERROR_CANCELLED), 0x800704C7: the user closed the dialog."""

# Method numbers in the vtables (shobjidl_core.h). IUnknown: 0-2,
# IModalWindow: 3, IFileDialog: 4-26.
_RELEASE = 2
_SHOW = 3
_SET_OPTIONS = 9
_GET_OPTIONS = 10
_SET_FOLDER = 12
_GET_FOLDER = 13
_SET_TITLE = 17
_GET_RESULT = 20
_CLOSE = 23
_SHELL_ITEM_GET_DISPLAY_NAME = 5


class Option(IntFlag):
    """The dialog's FILEOPENDIALOGOPTIONS that Ekranik sets."""

    NO_CHANGE_DIR = 0x8
    """Leave the process's current folder alone."""
    PICK_FOLDERS = 0x20
    FORCE_FILE_SYSTEM = 0x40
    """Only real folders, no libraries or virtual places."""
    PATH_MUST_EXIST = 0x800
    DONT_ADD_TO_RECENT = 0x2000000
    """Keep the folder out of Windows' recent items."""


OPTIONS = (
    Option.NO_CHANGE_DIR
    | Option.PICK_FOLDERS
    | Option.FORCE_FILE_SYSTEM
    | Option.PATH_MUST_EXIST
    | Option.DONT_ADD_TO_RECENT
)

_ole32 = ctypes.WinDLL("ole32")
_ole32.CoInitializeEx.argtypes = (ctypes.c_void_p, wintypes.DWORD)
_ole32.CoInitializeEx.restype = ctypes.HRESULT
_ole32.CoUninitialize.argtypes = ()
_ole32.CoUninitialize.restype = None
_ole32.CoCreateInstance.argtypes = (
    ctypes.POINTER(_GUID),
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_GUID),
    ctypes.POINTER(ctypes.c_void_p),
)
_ole32.CoCreateInstance.restype = ctypes.HRESULT
_ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
_ole32.CoTaskMemFree.restype = None
_shell32 = ctypes.WinDLL("shell32")
_shell32.SHCreateItemFromParsingName.argtypes = (
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    ctypes.POINTER(_GUID),
    ctypes.POINTER(ctypes.c_void_p),
)
_shell32.SHCreateItemFromParsingName.restype = ctypes.HRESULT


def _call(
    interface: ctypes.c_void_p,
    index: int,
    argtypes: tuple[type, ...] = (),
    *args: object,
    restype: type = ctypes.HRESULT,
) -> object:
    """Call a COM method by its vtable index; a failed HRESULT raises OSError."""
    vtable = ctypes.cast(
        interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    ).contents
    method = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])
    return method(interface, *args)


def _release(interface: ctypes.c_void_p) -> None:
    if interface:
        _call(interface, _RELEASE, restype=ctypes.c_ulong)


def _path_of(item: ctypes.c_void_p) -> str:
    """The file-system path of a shell item."""
    text = ctypes.c_void_p()
    _call(
        item,
        _SHELL_ITEM_GET_DISPLAY_NAME,
        (ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)),
        _SIGDN_FILESYSPATH,
        ctypes.byref(text),
    )
    try:
        return ctypes.wstring_at(text.value)
    finally:
        _ole32.CoTaskMemFree(text)


class FolderDialog:
    """One Windows folder picker; use it in a ``with`` block, which releases it."""

    def __init__(self, caption: str, start: str) -> None:
        """Set the dialog up: folders only, with a title, opening in ``start``.

        A ``start`` that doesn't exist is skipped: Windows picks the folder then.
        """
        self._dialog = ctypes.c_void_p()
        # The windows platform has set COM up on the GUI thread already (then
        # this only counts a reference); offscreen hasn't.
        _ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
        try:
            _ole32.CoCreateInstance(
                ctypes.byref(_CLSID_FILE_OPEN_DIALOG),
                None,
                _CLSCTX_INPROC_SERVER,
                ctypes.byref(_IID_FILE_OPEN_DIALOG),
                ctypes.byref(self._dialog),
            )
            _call(
                self._dialog, _SET_OPTIONS, (wintypes.DWORD,), self.options() | OPTIONS
            )
            _call(self._dialog, _SET_TITLE, (wintypes.LPCWSTR,), caption)
            if start:
                self._open_in(start)
        except BaseException:
            self._close_down()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._close_down()

    def _close_down(self) -> None:
        _release(self._dialog)
        self._dialog = ctypes.c_void_p()
        _ole32.CoUninitialize()

    def _open_in(self, folder: str) -> None:
        item = ctypes.c_void_p()
        try:
            # The shell parses backslashes only; settings keep Qt's slashes.
            _shell32.SHCreateItemFromParsingName(
                QDir.toNativeSeparators(folder),
                None,
                ctypes.byref(_IID_SHELL_ITEM),
                ctypes.byref(item),
            )
        except OSError:
            return  # missing or unreachable: Windows chooses where to open
        try:
            _call(self._dialog, _SET_FOLDER, (ctypes.c_void_p,), item)
        finally:
            _release(item)

    def options(self) -> int:
        """The dialog's FILEOPENDIALOGOPTIONS."""
        options = wintypes.DWORD()
        _call(
            self._dialog,
            _GET_OPTIONS,
            (ctypes.POINTER(wintypes.DWORD),),
            ctypes.byref(options),
        )
        return options.value

    def folder(self) -> str:
        """The folder the dialog shows, or would open in."""
        item = ctypes.c_void_p()
        _call(
            self._dialog,
            _GET_FOLDER,
            (ctypes.POINTER(ctypes.c_void_p),),
            ctypes.byref(item),
        )
        try:
            return _path_of(item)
        finally:
            _release(item)

    def show(self, owner: int) -> str:
        """Show the dialog over the window ``owner`` (an HWND) until the user is done.

        Returns the chosen folder, or "" when the user cancels.
        """
        try:
            _call(self._dialog, _SHOW, (wintypes.HWND,), owner)
        except OSError as error:
            if error.winerror == CANCELLED:
                return ""
            raise
        item = ctypes.c_void_p()
        _call(
            self._dialog,
            _GET_RESULT,
            (ctypes.POINTER(ctypes.c_void_p),),
            ctypes.byref(item),
        )
        try:
            return _path_of(item)
        finally:
            _release(item)

    def close(self, result: int) -> None:
        """Close the dialog while it shows; ``show()`` then ends with ``result``."""
        _call(self._dialog, _CLOSE, (ctypes.c_long,), result)


def pick_folder(parent: QWidget, caption: str, start: str) -> str:
    """Ask for a folder over ``parent``'s window; "" when the user cancels."""
    with FolderDialog(caption, start) as dialog:
        return dialog.show(int(parent.window().winId()))
