"""Ekranik's interface languages: English, Russian and Armenian (CLAUDE.md, rule 14).

English is the source language: its texts are the ones in the code, so it needs
no file. A translation is ``translations/ekranik_<language>.qm`` in this
package, built by ``tools/translations.py`` (the /i18n skill) from the ``.ts``
files in the repo's ``translations`` folder; a text it doesn't translate stays
English. Qt's own texts, such as the names of keys in shortcuts, come from Qt's
``qtbase_<language>.qm``, which PySide6 has in Russian but not in Armenian.

The language is the user's choice (``Settings.language``). Until they choose
one, it follows Windows: the first language in the user's list of preferred
languages (Settings → Time & language → Language & region) that Ekranik has;
else English. The list starts with the display language, but a user who reads
Russian after an unsupported display language gets Russian, as in Store apps.
Qt appends the language of the regional format last when the list lacks it
(Qt 6.12, checked 2026-11-20): it counts only after every listed language, and
before English.
A new choice applies at once: every window gets ``QEvent.LanguageChange`` and
sets its texts again.

Cost at startup (2026-11-20): English loads no file, a translation loads in
under 1 ms. Following Windows asks Qt for the user's language list, about 2 ms;
calling Windows directly through ctypes costs 12 ms to import ctypes and gives
only the display language. The files load in the GUI thread (a rule 3
exception): the first window needs its texts before it is built.
"""

from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QLocale,
    QObject,
    QTranslator,
)

from ekranik import settings
from ekranik.settings import Language, Settings

FOLDER = Path(__file__).parent / "translations"
"""Ekranik's compiled translations, ``ekranik_<language>.qm``."""

SOURCE = Language.ENGLISH
"""The language of the texts in the code."""


def windows_languages() -> list[str]:
    """The user's preferred languages in Windows as language tags, in order."""
    return QLocale.system().uiLanguages()


def pick(choice: Language, preferred: Callable[[], Iterable[str]]) -> Language:
    """The language to show: the user's choice, else the first preferred language
    Ekranik has, else English.

    ``preferred`` gives language tags such as ``hy-Armn-AM`` or ``ru_RU``; it is
    called only when the choice is to follow Windows.
    """
    if choice is not Language.SYSTEM:
        return choice
    for tag in preferred():
        code = tag.replace("_", "-").partition("-")[0].casefold()
        if code and code in Language:
            return Language(code)
    return SOURCE


class Translations(QObject):
    """Shows the app in the language in effect, and follows its setting live."""

    def __init__(self, app: QCoreApplication, current: Settings) -> None:
        super().__init__(app)
        self._app = app
        self._settings = current
        self._language = SOURCE
        self._loaded: list[QTranslator] = []
        current.changed.connect(self._setting_changed)
        self.apply()

    @property
    def language(self) -> Language:
        """The language shown: never ``Language.SYSTEM``."""
        return self._language

    def files(self) -> list[str]:
        """The translation files in use, Qt's first; none for English."""
        return [translator.filePath() for translator in self._loaded]

    def apply(self) -> None:
        """Load the translations of the language in effect, if it is a new one."""
        language = pick(self._settings.language, windows_languages)
        if language is self._language:
            return
        for translator in self._loaded:
            self._app.removeTranslator(translator)
            translator.deleteLater()
        self._loaded.clear()
        self._language = language
        if language is SOURCE:
            return
        # Installed last, Ekranik's own file is searched first: it may correct
        # Qt's texts (EKR-24).
        for name, folder in (
            (
                f"qtbase_{language}",
                QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
            ),
            (f"ekranik_{language}", str(FOLDER)),
        ):
            translator = QTranslator(self)
            if translator.load(name, folder):
                self._app.installTranslator(translator)
                self._loaded.append(translator)
            else:
                translator.deleteLater()

    def _setting_changed(self, key: str) -> None:
        if key == Settings.language.key:
            self.apply()


def install(app: QCoreApplication) -> Translations:
    """Show the app in its language; calling it again returns the same ``Translations``."""
    found = app.findChild(Translations)
    return found if found is not None else Translations(app, settings.install(app))
