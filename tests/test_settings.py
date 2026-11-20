"""Settings: typed values, defaults, the schema version and migrations (rule 4)."""

import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QDir, QSettings, QStandardPaths
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ekranik import settings
from ekranik.settings import FrameRate, Language, Settings


def open_file(path: Path) -> Settings:
    return Settings(QSettings(str(path), QSettings.Format.IniFormat))


def write_ini(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def on_disk(store: QSettings, tmp_path: Path) -> dict[str, object]:
    """Every key and value as a restart reads them: from a copy of the file.

    Within one process Qt shares the parsed file between everything that opens
    the same path, so only a copy is really read from disk.
    """
    store.sync()
    copy = QSettings(
        str(shutil.copy(store.fileName(), tmp_path / "copy.ini")),
        QSettings.Format.IniFormat,
    )
    return {key: copy.value(key) for key in copy.allKeys()}


def test_defaults_when_there_is_no_file(tmp_path: Path) -> None:
    current = open_file(tmp_path / "Ekranik.ini")
    videos = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.MoviesLocation
    )
    music = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.MusicLocation
    )
    assert current.screen_folder == QDir(videos).filePath("Ekranik")
    assert current.audio_folder == QDir(music).filePath("Ekranik")
    assert current.frame_rate is FrameRate.SCREEN
    assert current.microphone is True
    assert current.language is Language.SYSTEM
    # Only the version is written; the defaults are not, so the default folders
    # follow a moved Videos or Music folder.
    assert on_disk(current.store, tmp_path) == {
        settings.VERSION_KEY: str(settings.SCHEMA_VERSION)
    }


def test_a_new_file_runs_no_migration_steps(tmp_path: Path) -> None:
    # A step may fill in what an older version meant by a missing key; a new
    # file has nothing older to keep.
    store = QSettings(str(tmp_path / "Ekranik.ini"), QSettings.Format.IniFormat)
    ran: list[int] = []
    settings.migrate(store, (lambda _store: ran.append(1),) * 3)
    assert ran == []
    assert settings.stored_version(store) == 3


def test_settings_survive_a_restart(tmp_path: Path, qtbot: QtBot) -> None:
    path = tmp_path / "Ekranik.ini"
    current = open_file(path)
    # Cyrillic and Armenian names, spaces and a comma, which INI quotes.
    folder = "D:/Записи/Տեսանյութեր, 2026"
    current.screen_folder = folder
    current.audio_folder = "\\\\server\\share\\audio"
    current.frame_rate = FrameRate.FPS_30
    current.language = Language.ARMENIAN
    current.microphone = False
    # Written by the event loop, as in the app: no explicit sync.
    qtbot.waitUntil(
        lambda: path.exists() and "microphone=false" in path.read_text(encoding="utf-8")
    )
    restarted = open_file(Path(shutil.copy(path, tmp_path / "restart.ini")))
    assert restarted.screen_folder == folder
    assert restarted.audio_folder == "//server/share/audio"
    assert restarted.frame_rate is FrameRate.FPS_30
    assert restarted.language is Language.ARMENIAN
    assert restarted.microphone is False


def test_following_windows_can_be_chosen(tmp_path: Path) -> None:
    # Stored as an empty value: it must read back as a choice, not as missing.
    path = tmp_path / "Ekranik.ini"
    current = open_file(path)
    current.language = Language.RUSSIAN
    current.language = Language.SYSTEM
    current.store.sync()
    restarted = open_file(Path(shutil.copy(path, tmp_path / "restart.ini")))
    assert Settings.language.stored(restarted) is Language.SYSTEM
    assert on_disk(restarted.store, tmp_path)[Settings.language.key] == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("ru", Language.RUSSIAN), (" HY ", Language.ARMENIAN), ("En", Language.ENGLISH)],
)
def test_a_hand_written_language_is_read(
    tmp_path: Path, raw: str, expected: Language
) -> None:
    current = open_file(
        write_ini(tmp_path / "Ekranik.ini", f"[interface]\nlanguage={raw}\n")
    )
    assert current.language is expected


def test_a_version_0_file_is_migrated_and_unknown_keys_are_kept(tmp_path: Path) -> None:
    path = write_ini(
        tmp_path / "Ekranik.ini",
        "[General]\nlegacy=1\n\n"
        "[recording]\nframe_rate=60\nmicrophone=false\nquality=high\n\n"
        "[folders]\nscreen=D:/Recordings\n\n"
        "[future]\nthing=kept\n",
    )
    current = open_file(path)
    assert settings.stored_version(current.store) == settings.SCHEMA_VERSION
    assert current.frame_rate is FrameRate.FPS_60
    assert current.microphone is False
    assert current.screen_folder == "D:/Recordings"
    assert on_disk(current.store, tmp_path) == {
        "legacy": "1",
        "recording/frame_rate": "60",
        "recording/microphone": "false",
        "recording/quality": "high",
        "folders/screen": "D:/Recordings",
        "future/thing": "kept",
        settings.VERSION_KEY: str(settings.SCHEMA_VERSION),
    }


@pytest.mark.parametrize("version", [str(settings.SCHEMA_VERSION + 5), "x", "-1"])
def test_a_newer_or_unreadable_version_is_left_alone(
    tmp_path: Path, version: str
) -> None:
    text = (
        f"[General]\nschema_version={version}\n\n[recording]\nframe_rate=30\n\n"
        "[hotkeys]\nnew_action=Ctrl+Alt+R\n"
    )
    current = open_file(write_ini(tmp_path / "Ekranik.ini", text))
    assert current.frame_rate is FrameRate.FPS_30
    ran: list[int] = []
    # As many steps as this version has: none may run on such a file.
    steps = (lambda _store: ran.append(1),) * settings.SCHEMA_VERSION
    settings.migrate(current.store, steps)
    assert ran == []
    assert on_disk(current.store, tmp_path) == {
        settings.VERSION_KEY: version,
        "recording/frame_rate": "30",
        "hotkeys/new_action": "Ctrl+Alt+R",
    }


@pytest.mark.parametrize(
    ("attribute", "key", "raw"),
    [
        ("frame_rate", "recording/frame_rate", "45"),
        ("frame_rate", "recording/frame_rate", "60.0"),
        ("frame_rate", "recording/frame_rate", "sixty"),
        ("microphone", "recording/microphone", "maybe"),
        # A language of a newer Ekranik, or a typo: Windows' language until chosen.
        ("language", "interface/language", "de"),
        ("language", "interface/language", "ru_RU"),
        ("screen_folder", "folders/screen", "Videos"),
        ("screen_folder", "folders/screen", "C:Videos"),
        ("screen_folder", "folders/screen", "//?/rec"),
        ("screen_folder", "folders/screen", "//./pipe/rec"),
        ("screen_folder", "folders/screen", "D:/a, D:/b"),  # unquoted: Qt reads a list
    ],
)
def test_an_unreadable_value_gives_the_default_and_stays(
    tmp_path: Path, attribute: str, key: str, raw: str
) -> None:
    group, name = key.split("/")
    current = open_file(
        write_ini(tmp_path / "Ekranik.ini", f"[{group}]\n{name}={raw}\n")
    )
    default = getattr(open_file(tmp_path / "defaults.ini"), attribute)
    assert getattr(current, attribute) == default
    # Migrating rewrote the file; the value is still there for a newer Ekranik.
    assert key in on_disk(current.store, tmp_path)
    # Choosing a value replaces it, even when the choice is the default.
    setattr(current, attribute, default)
    assert getattr(Settings, attribute).stored(current) == default


@pytest.mark.parametrize(
    ("raw", "expected"), [(None, 0), ("0", 0), ("2", 2), ("-3", None), ("x", None)]
)
def test_stored_version(tmp_path: Path, raw: str | None, expected: int | None) -> None:
    store = QSettings(str(tmp_path / "Ekranik.ini"), QSettings.Format.IniFormat)
    if raw is not None:
        store.setValue(settings.VERSION_KEY, raw)
    assert settings.stored_version(store) == expected


def test_each_migration_step_runs_once_in_order(tmp_path: Path) -> None:
    store = QSettings(str(tmp_path / "Ekranik.ini"), QSettings.Format.IniFormat)
    store.setValue("old/name", "value")
    store.setValue("other/key", "kept")
    ran: list[int] = []

    def step_1(store: QSettings) -> None:
        ran.append(1)
        settings.rename(store, "old/name", "new/name")

    def step_2(store: QSettings) -> None:
        ran.append(2)
        assert store.value("new/name") == "value"

    for _ in range(2):
        settings.migrate(store, (step_1, step_2))
    assert ran == [1, 2]
    assert settings.stored_version(store) == 2
    assert {key: store.value(key) for key in store.allKeys()} == {
        "new/name": "value",
        "other/key": "kept",
        settings.VERSION_KEY: 2,
    }
    # A later version adds a step; only that one runs.
    settings.migrate(store, (step_1, step_2, lambda _store: ran.append(3)))
    assert ran == [1, 2, 3]
    assert settings.stored_version(store) == 3


def test_rename_keeps_a_value_already_under_the_new_key(tmp_path: Path) -> None:
    store = QSettings(str(tmp_path / "Ekranik.ini"), QSettings.Format.IniFormat)
    store.setValue("old", "older")
    store.setValue("new", "newer")
    settings.rename(store, "old", "new")
    assert store.value("new") == "newer"
    assert not store.contains("old")
    settings.rename(store, "missing", "new")
    assert store.value("new") == "newer"


@pytest.mark.parametrize("new", ["recording/microphone", "recording/Microphone"])
def test_rename_to_the_same_key_keeps_the_value(tmp_path: Path, new: str) -> None:
    # INI keys ignore case on Windows: both names are the same key to Qt.
    store = QSettings(str(tmp_path / "Ekranik.ini"), QSettings.Format.IniFormat)
    store.setValue("recording/Microphone", "false")
    settings.rename(store, "recording/Microphone", new)
    assert on_disk(store, tmp_path) == {new: "false"}


def test_a_choice_is_kept_and_announced_once(tmp_path: Path) -> None:
    current = open_file(tmp_path / "Ekranik.ini")
    announced: list[str] = []
    current.changed.connect(announced.append)
    current.frame_rate = FrameRate.FPS_60
    current.frame_rate = FrameRate.FPS_60
    assert announced == [Settings.frame_rate.key]
    # Stored as plain values that any Ekranik version can read back.
    assert current.store.value(Settings.frame_rate.key) == 60
    # Choosing the value in effect stores the choice, with nothing to announce.
    current.microphone = True
    assert Settings.microphone.stored(current) is True
    assert announced == [Settings.frame_rate.key]


def test_a_chosen_folder_stays_when_windows_moves_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Rule 9: recordings go only to the folder the user chose, even when it is
    # the default of the day and Windows later moves Videos to OneDrive.
    current = open_file(tmp_path / "Ekranik.ini")
    chosen = current.screen_folder
    current.screen_folder = "D:/Recordings"
    current.screen_folder = chosen
    monkeypatch.setattr(Settings.screen_folder, "default", lambda: "E:/OneDrive/Videos")
    assert current.screen_folder == chosen
    # Back to the default: from now on it follows Windows again.
    announced: list[str] = []
    current.changed.connect(announced.append)
    del current.screen_folder
    assert current.screen_folder == "E:/OneDrive/Videos"
    assert not current.store.contains(Settings.screen_folder.key)
    assert announced == [Settings.screen_folder.key]
    del current.screen_folder
    assert announced == [Settings.screen_folder.key]


def test_going_back_to_the_default_is_announced_only_if_the_value_changes(
    tmp_path: Path,
) -> None:
    current = open_file(tmp_path / "Ekranik.ini")
    current.microphone = True
    announced: list[str] = []
    current.changed.connect(announced.append)
    del current.microphone
    assert announced == []
    assert not current.store.contains(Settings.microphone.key)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("frame_rate", 45),
        ("microphone", "maybe"),
        ("language", "de"),
        ("language", None),
        ("screen_folder", "Videos"),
        ("screen_folder", "C:"),
        ("screen_folder", "\\Videos"),
        ("screen_folder", "//server"),
        # Device paths: Qt would strip \\?\ and leave a relative path.
        ("screen_folder", "\\\\?\\rec"),
        ("screen_folder", "\\\\?\\C:\\rec"),
        ("screen_folder", "\\\\.\\pipe\\rec"),
        # Hidden characters: the path shown would not be the path used.
        ("screen_folder", "D:/rec\x00x"),
        ("screen_folder", "D:/rec\nx"),
        ("screen_folder", "D:/\u202ecer"),
        ("audio_folder", ""),
    ],
)
def test_an_invalid_value_is_refused(
    tmp_path: Path, attribute: str, value: object
) -> None:
    current = open_file(tmp_path / "Ekranik.ini")
    with pytest.raises(ValueError):
        setattr(current, attribute, value)
    assert current.store.allKeys() == [settings.VERSION_KEY]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("D:\\Recordings\\Screen\\", "D:/Recordings/Screen"),
        ("\\\\nas\\share\\rec", "//nas/share/rec"),
        # Persian writes some words with a zero-width non-joiner: not hidden.
        ("D:/می\u200cخواهم", "D:/می\u200cخواهم"),
    ],
)
def test_folders_are_kept_with_forward_slashes(
    tmp_path: Path, value: str, expected: str
) -> None:
    current = open_file(tmp_path / "Ekranik.ini")
    current.screen_folder = value
    assert current.screen_folder == expected


def test_the_app_keeps_its_settings_in_an_ini_file(
    qapp: QApplication, tmp_path_factory: pytest.TempPathFactory
) -> None:
    current = settings.install(qapp)
    assert settings.install(qapp) is current
    assert current.store.format() == QSettings.Format.IniFormat
    assert Path(current.store.fileName()).name == "Ekranik.ini"
    assert Path(current.store.fileName()).is_relative_to(tmp_path_factory.getbasetemp())
    # QSettings() without a format stays out of the registry too.
    assert QSettings().format() == QSettings.Format.IniFormat


def test_the_system_wide_file_is_ignored(
    qapp: QApplication, tmp_path_factory: pytest.TempPathFactory
) -> None:
    # Any user of the PC can write C:\ProgramData; Qt reads it as a fallback.
    names = (QCoreApplication.organizationName(), QCoreApplication.applicationName())
    system = Path(
        QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.SystemScope, *names
        ).fileName()
    )
    # Redirected by conftest.py: the real C:\ProgramData is never written.
    assert system.is_relative_to(tmp_path_factory.getbasetemp())
    system.parent.mkdir(parents=True, exist_ok=True)
    write_ini(system, "[recording]\nframe_rate=30\n")
    try:
        with_fallbacks = QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, *names
        )
        assert with_fallbacks.value(Settings.frame_rate.key) == "30"
        current = Settings(settings.open_store())
        assert current.frame_rate is FrameRate.SCREEN
        assert not current.store.contains(Settings.frame_rate.key)
    finally:
        system.unlink()


def test_every_setting_knows_its_name() -> None:
    assert [setting.name for setting in Settings.all()] == [
        "language",
        "screen_folder",
        "audio_folder",
        "frame_rate",
        "microphone",
    ]
    for setting in Settings.all():
        assert getattr(Settings, setting.name) is setting


def test_restore_puts_back_what_the_file_held(tmp_path: Path) -> None:
    path = write_ini(
        tmp_path / "Ekranik.ini", "[recording]\nframe_rate=sixty\nmicrophone=false\n"
    )
    current = open_file(path)
    saved = {setting: setting.raw(current) for setting in Settings.all()}
    assert saved[Settings.frame_rate] == "sixty"
    assert saved[Settings.screen_folder] is None
    current.frame_rate = FrameRate.FPS_30
    current.microphone = True
    current.screen_folder = "D:/Recordings"
    announced: list[str] = []
    current.changed.connect(announced.append)
    for setting, raw in saved.items():
        setting.restore(current, raw)
    # An unreadable value comes back as it was, for the Ekranik that wrote it.
    assert current.store.value(Settings.frame_rate.key) == "sixty"
    assert current.microphone is False
    assert not current.store.contains(Settings.screen_folder.key)
    assert sorted(announced) == sorted(
        s.key
        for s in (Settings.frame_rate, Settings.microphone, Settings.screen_folder)
    )
    # Putting back what is already there announces nothing.
    announced.clear()
    Settings.microphone.restore(current, "false")
    assert announced == []
