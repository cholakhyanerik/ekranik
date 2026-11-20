"""Shared fixtures: the tests run in an app set up the way `ekranik.main()` sets it up."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QApplication

from ekranik import configure_app, settings


@pytest.fixture(scope="session", autouse=True)
def _configured_app(
    qapp: QApplication, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Apply Ekranik's name and style to pytest-qt's QApplication.

    The tests carry the real app name, so settings, app data and the recording
    folders are first redirected to test locations: no test reads or overwrites
    the user's own.
    """
    QStandardPaths.setTestModeEnabled(True)
    for scope, folder in (
        (QSettings.Scope.UserScope, "settings"),
        (QSettings.Scope.SystemScope, "system-settings"),
    ):
        QSettings.setPath(
            QSettings.Format.IniFormat, scope, str(tmp_path_factory.mktemp(folder))
        )
    configure_app(qapp)
    # Test mode leaves Videos and Music alone: the app's folders point elsewhere.
    current = settings.install(qapp)
    current.screen_folder = str(tmp_path_factory.mktemp("Videos"))
    current.audio_folder = str(tmp_path_factory.mktemp("Music"))
    # The tests compare English texts, whatever the language of Windows.
    current.language = settings.Language.ENGLISH


@pytest.fixture(autouse=True)
def _settings_unchanged(qapp: QApplication) -> Iterator[None]:
    """Every test starts from the same settings, whatever the one before changed."""
    saved = [
        (setting, setting.raw(settings.install(qapp)))
        for setting in settings.Settings.all()
    ]
    yield
    current = settings.install(qapp)  # a test may have installed new settings
    for setting, raw in saved:
        setting.restore(current, raw)
