"""Languages: the choice, Windows' languages, the English fallback, live switching (EKR-6)."""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ekranik import i18n, settings
from ekranik.settings import Language, Settings
from ekranik.ui.main_window import MainWindow
from ekranik.ui.settings_dialog import SettingsDialog

ROOT = Path(__file__).resolve().parent.parent


def tags(*preferred: str) -> Callable[[], list[str]]:
    return lambda: list(preferred)


def refuse() -> list[str]:
    raise AssertionError("asked Windows although the language is chosen")


@pytest.mark.parametrize(
    ("choice", "preferred", "expected"),
    [
        # A choice wins, and Windows isn't asked (about 2 ms at startup).
        (Language.RUSSIAN, None, Language.RUSSIAN),
        (Language.ARMENIAN, None, Language.ARMENIAN),
        (Language.ENGLISH, None, Language.ENGLISH),
        # As Qt reports Windows' languages (2026-11-20): with scripts and regions.
        (
            Language.SYSTEM,
            ("hy-Armn-AM", "hy-AM", "hy", "ru-Cyrl-RU", "ru"),
            Language.ARMENIAN,
        ),
        (Language.SYSTEM, ("ru_RU",), Language.RUSSIAN),
        # The first language Ekranik has, in the user's order.
        (Language.SYSTEM, ("de-DE", "de", "ru-RU", "hy-AM"), Language.RUSSIAN),
        (Language.SYSTEM, ("en-GB", "ru-RU"), Language.ENGLISH),
        (Language.SYSTEM, ("de-DE", "fr-FR"), Language.ENGLISH),
        (Language.SYSTEM, (), Language.ENGLISH),
        (Language.SYSTEM, ("", "-", "C", "x-ru"), Language.ENGLISH),
    ],
)
def test_pick(
    choice: Language, preferred: tuple[str, ...] | None, expected: Language
) -> None:
    asked = refuse if preferred is None else tags(*preferred)
    assert i18n.pick(choice, asked) is expected


@pytest.fixture
def current(qapp: QApplication) -> Settings:
    return settings.install(qapp)


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    """The main window; the test holds it, since pytest-qt keeps only weak references."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def file_names(qapp: QApplication) -> list[str]:
    return [Path(file).name for file in i18n.install(qapp).files()]


def test_english_loads_no_file(qapp: QApplication, current: Settings) -> None:
    current.language = Language.ENGLISH
    assert i18n.install(qapp).language is Language.ENGLISH
    assert i18n.install(qapp).files() == []


@pytest.mark.parametrize(
    ("language", "settings_text", "space_key", "files"),
    [
        (Language.RUSSIAN, "Параметры", "Пробел", ["qtbase_ru.qm", "ekranik_ru.qm"]),
        # Qt has no Armenian of its own: its texts stay English (EKR-24).
        (Language.ARMENIAN, "Կարգավորումներ", "Space", ["ekranik_hy.qm"]),
    ],
)
def test_a_chosen_language_shows_its_texts_at_once(
    qapp: QApplication,
    qtbot: QtBot,
    current: Settings,
    window: MainWindow,
    language: Language,
    settings_text: str,
    space_key: str,
    files: list[str],
) -> None:
    current.language = language
    assert i18n.install(qapp).language is language
    assert file_names(qapp) == files
    # Ekranik's own file comes from its own folder, never from the current one.
    assert Path(i18n.install(qapp).files()[-1]).parent == i18n.FOLDER
    # An open window changes its texts; one opened later starts in the language.
    qtbot.waitUntil(lambda: window.settings_button.text() == settings_text)
    dialog = SettingsDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == settings_text
    assert QCoreApplication.translate("QShortcut", "Space") == space_key
    # A text without a translation stays English.
    assert (
        QCoreApplication.translate("SettingsDialog", "A text Ekranik doesn't have")
        == "A text Ekranik doesn't have"
    )

    current.language = Language.ENGLISH
    qtbot.waitUntil(lambda: window.settings_button.text() == "Settings")
    assert dialog.windowTitle() == "Settings"
    assert file_names(qapp) == []


def test_until_chosen_the_language_follows_windows(
    qapp: QApplication,
    qtbot: QtBot,
    current: Settings,
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(i18n, "windows_languages", tags("de-DE", "hy-AM", "ru-RU"))
    del current.language
    assert i18n.install(qapp).language is Language.ARMENIAN
    qtbot.waitUntil(lambda: window.settings_button.text() == "Կարգավորումներ")
    # Choosing "follow Windows" is the same, but stays chosen.
    current.language = Language.SYSTEM
    assert i18n.install(qapp).language is Language.ARMENIAN
    monkeypatch.setattr(i18n, "windows_languages", tags("fr-FR"))
    i18n.install(qapp).apply()
    assert i18n.install(qapp).language is Language.ENGLISH
    qtbot.waitUntil(lambda: window.settings_button.text() == "Settings")


def test_switching_unloads_the_previous_language(
    qapp: QApplication, current: Settings
) -> None:
    for language in (Language.RUSSIAN, Language.ARMENIAN, Language.RUSSIAN):
        current.language = language
    assert file_names(qapp) == ["qtbase_ru.qm", "ekranik_ru.qm"]


def test_the_translations_are_current_and_complete() -> None:
    # Rule 14: every text of the code is in each .ts file, translated, and built
    # into the .qm file the app loads. The fix: uv run tools/translations.py
    done = subprocess.run(  # noqa: S603 -- this repo's own tool, by full path
        [sys.executable, ROOT / "tools" / "translations.py", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
