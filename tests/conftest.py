"""Shared fixtures: the tests run in an app set up the way `ekranik.main()` sets it up."""

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
