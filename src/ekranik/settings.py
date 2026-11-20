r"""Ekranik's settings: typed values, every default in one place, a schema version.

The values live in the user's own INI file (``%APPDATA%\Ekranik\Ekranik.ini``),
opened through ``open_store()``:

- Never the registry. ``QSettings(org, app)`` and ``QSettings(scope, org, app)``
  ignore ``QSettings.setDefaultFormat()`` and always use it, and the tests
  redirect only INI files (tests/conftest.py).
- Never the system-wide file in ``C:\ProgramData``, which Qt reads as a fallback
  by default and which any user of the PC can write.
- Inside the MSIX package Windows redirects ``%APPDATA%`` into the package's
  private folder: fine for settings, but don't hand that path to other tools.
- Hand-written backslashes are INI escapes (``D:\Rec`` reads as ``D:ec``), so a
  hand-edited path needs ``/`` or ``\\``.

Settings survive updates (CLAUDE.md, rule 4). The file carries a schema
version, and every version that renames or reshapes a key adds one step to
``MIGRATIONS`` that moves the old value over. Keys this version doesn't know are
left as they are, so the settings of a newer Ekranik survive a run of an older
one.

Defaults are never written: until the user chooses a value, a setting follows
its default, and the default folders follow Windows when the Videos or Music
folder moves. A choice is always written, even one equal to the default, so a
chosen folder stays chosen (rule 9); ``del settings.x`` goes back to the default.

The file is a few hundred bytes, read once at startup; ``QSettings`` keeps it
in memory and writes changes back on the next pass of the event loop.
"""

import re
from collections.abc import Callable
from enum import Enum, IntEnum
from pathlib import PureWindowsPath
from typing import Self, overload

from PySide6.QtCore import (
    QCoreApplication,
    QDir,
    QObject,
    QSettings,
    QStandardPaths,
    Signal,
)

VERSION_KEY = "schema_version"
"""The key that holds the file's schema version; a file without it is version 0."""

type Migration = Callable[[QSettings], None]


def _from_version_0(store: QSettings) -> None:
    """Version 0 is a file from before the schema version existed; no key has moved."""


MIGRATIONS: tuple[Migration, ...] = (_from_version_0,)
"""``MIGRATIONS[n]`` turns a version-``n`` file into version ``n + 1``.

Append a step when a key is renamed or its values change meaning; never edit or
remove a step that has shipped.
"""

SCHEMA_VERSION = len(MIGRATIONS)
"""The schema version this Ekranik writes."""


def stored_version(store: QSettings) -> int | None:
    """The file's schema version: 0 when it has none, ``None`` when it is unreadable."""
    raw = store.value(VERSION_KEY)
    if raw is None:
        return 0
    try:
        version = int(str(raw))
    except ValueError:
        return None
    return version if version >= 0 else None


def migrate(store: QSettings, migrations: tuple[Migration, ...] = MIGRATIONS) -> None:
    """Bring the file up to the current schema version, one step per version.

    A new, empty file only gets the version: its defaults are already current.
    A file from a newer Ekranik, or with an unreadable version, is left as it
    is: guessing could change what its values mean.
    """
    if not store.allKeys():
        store.setValue(VERSION_KEY, len(migrations))
        return
    version = stored_version(store)
    if version is None:
        return
    for number, step in enumerate(migrations[version:], start=version):
        step(store)
        store.setValue(VERSION_KEY, number + 1)


def rename(store: QSettings, old: str, new: str) -> None:
    """Move a value to its new key, for a migration step.

    A value already under the new key wins: a newer Ekranik wrote it. INI keys
    ignore case on Windows, so a change of case only respells the key.
    """
    if not store.contains(old):
        return
    value = store.value(old)
    if old.casefold() == new.casefold():
        store.remove(old)
        store.setValue(new, value)
        return
    if not store.contains(new):
        store.setValue(new, value)
    store.remove(old)


class FrameRate(IntEnum):
    """Frames per second of screen recordings."""

    SCREEN = 0
    """The refresh rate of the recorded screen."""
    FPS_60 = 60
    FPS_30 = 30


def _parse_bool(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    match str(raw).strip().lower():
        case "true" | "1":
            return True
        case "false" | "0":
            return False
        case _:
            raise ValueError(raw)


def _parse_frame_rate(raw: object) -> FrameRate:
    return FrameRate(int(str(raw)))


_HIDDEN = re.compile("[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
"""Control characters and bidi overrides: the path shown would differ from the one used."""


def _parse_folder(raw: object) -> str:
    r"""A folder on a drive or a network share, with Qt's forward slashes.

    Refused: relative and drive-relative paths (``Videos``, ``C:Videos``,
    ``\Videos``), Windows device paths (``\\?\``, ``\\.\``), and hidden
    characters. A network share is allowed: only the user's own file or the
    folder picker can name one.
    """
    if (
        not isinstance(raw, str)
        or _HIDDEN.search(raw)
        or raw.replace("\\", "/").startswith(("//?/", "//./"))
    ):
        raise ValueError(raw)
    folder = QDir.cleanPath(raw)
    path = PureWindowsPath(folder)
    if not (path.drive and path.root):
        raise ValueError(raw)
    return folder


def _app_folder(location: QStandardPaths.StandardLocation) -> Callable[[], str]:
    """A default folder: the app's own folder inside a standard user folder."""

    def default() -> str:
        base = QStandardPaths.writableLocation(location) or QDir.homePath()
        return QDir(base).filePath(QCoreApplication.applicationName())

    return default


def _plain[T](value: T) -> object:
    """What goes into the file: enums as their values."""
    return value.value if isinstance(value, Enum) else value


class Setting[T]:
    """One setting: its key in the file, its default and how to read it back.

    A class attribute of ``Settings``:

    - Reading gives the stored value, or the default when the key is missing or
      holds something unreadable, such as a bad hand-edited value.
    - Assigning stores the value, even one equal to the default; an invalid
      value raises ``ValueError``.
    - ``del`` removes the stored value, so the default applies again.

    ``Settings.changed`` is emitted when the value in effect changes.
    """

    def __init__(
        self, key: str, default: Callable[[], T], parse: Callable[[object], T]
    ) -> None:
        self.key = key
        self.default = default
        self.parse = parse
        self.name = ""
        """The attribute's name in ``Settings``, for ``getattr()`` and friends."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def raw(self, settings: Settings) -> object | None:
        """The value as the file holds it, readable or not; ``None`` when missing.

        With ``restore()``, it takes back changes that were only tried out.
        """
        return settings.store.value(self.key)

    def restore(self, settings: Settings, raw: object | None) -> None:
        """Put back a value from ``raw()``, announcing it if the value in effect changes."""
        before = self.__get__(settings, type(settings))
        if raw is None:
            settings.store.remove(self.key)
        else:
            settings.store.setValue(self.key, raw)
        if self.__get__(settings, type(settings)) != before:
            settings.changed.emit(self.key)

    def stored(self, settings: Settings) -> T | None:
        """The stored value; ``None`` when the key is missing or unreadable."""
        raw = settings.store.value(self.key)
        if raw is None:
            return None
        try:
            return self.parse(raw)
        except ValueError, TypeError:
            return None

    @overload
    def __get__(self, settings: None, owner: type) -> Self: ...
    @overload
    def __get__(self, settings: Settings, owner: type) -> T: ...
    def __get__(self, settings: Settings | None, owner: type) -> Self | T:
        if settings is None:
            return self
        value = self.stored(settings)
        return self.default() if value is None else value

    def __set__(self, settings: Settings, value: T) -> None:
        value = self.parse(_plain(value))
        stored = self.stored(settings)
        if value == stored:
            return
        settings.store.setValue(self.key, _plain(value))
        if value != (self.default() if stored is None else stored):
            settings.changed.emit(self.key)

    def __delete__(self, settings: Settings) -> None:
        if not settings.store.contains(self.key):
            return
        before = self.__get__(settings, type(settings))
        settings.store.remove(self.key)
        if self.default() != before:
            settings.changed.emit(self.key)


class Settings(QObject):
    """Ekranik's settings as typed attributes; the defaults are defined here."""

    changed = Signal(str)
    """Emitted with a setting's key after its value changed, so it applies at once."""

    screen_folder = Setting(
        "folders/screen",
        _app_folder(QStandardPaths.StandardLocation.MoviesLocation),
        _parse_folder,
    )
    """Where screen recordings are saved: Videos\\Ekranik unless chosen."""
    audio_folder = Setting(
        "folders/audio",
        _app_folder(QStandardPaths.StandardLocation.MusicLocation),
        _parse_folder,
    )
    """Where audio recordings are saved: Music\\Ekranik unless chosen."""
    frame_rate = Setting(
        "recording/frame_rate", lambda: FrameRate.SCREEN, _parse_frame_rate
    )
    """Frames per second of screen recordings."""
    microphone = Setting("recording/microphone", lambda: True, _parse_bool)
    """Whether a new screen recording includes the microphone."""

    @classmethod
    def all(cls) -> tuple[Setting[object], ...]:
        """Every setting, in the order defined here."""
        return tuple(
            value for value in vars(cls).values() if isinstance(value, Setting)
        )

    def __init__(self, store: QSettings, parent: QObject | None = None) -> None:
        """Read the settings from ``store``, migrating it first; owns the store.

        Only the store's own file counts: Qt's fallbacks to other files are off.
        """
        super().__init__(parent)
        store.setParent(self)
        store.setFallbacksEnabled(False)
        self.store = store
        migrate(store)


def open_store() -> QSettings:
    """The user's settings file, in INI format; the only way to open it."""
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        QCoreApplication.organizationName(),
        QCoreApplication.applicationName(),
    )


def install(app: QCoreApplication) -> Settings:
    """The app's settings, read on the first call; later calls return the same ones."""
    found = app.findChild(Settings)
    return found if found is not None else Settings(open_store(), app)
