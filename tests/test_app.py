"""The app starts, shows its main window and quits cleanly."""

from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QSettings, QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

import ekranik
from ekranik import i18n, settings
from ekranik.ui import theme
from ekranik.ui.main_window import MainWindow


def test_app_is_configured(qapp: QApplication) -> None:
    assert qapp.organizationName() == ekranik.APP_NAME
    assert qapp.applicationName() == ekranik.APP_NAME
    assert qapp.style().name() == ekranik.STYLE
    assert qapp.findChild(theme.Theme) is not None
    assert qapp.findChild(i18n.Translations) is not None
    # An app-wide stylesheet doubles the cost of every widget (rule 3, theme.py).
    assert qapp.styleSheet() == ""


def test_tests_keep_away_from_the_users_settings(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    settings = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, ekranik.APP_NAME
    )
    assert Path(settings.fileName()).is_relative_to(tmp_path_factory.getbasetemp())
    assert QStandardPaths.isTestModeEnabled()
    # Recordings made by tests land in temporary folders, not in Videos or Music.
    current = ekranik.settings.install(QApplication.instance())
    for folder in (current.screen_folder, current.audio_folder):
        assert Path(folder).is_relative_to(tmp_path_factory.getbasetemp())


def test_main_window_opens_and_closes(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    with qtbot.waitExposed(window):
        window.show()
    assert window.windowTitle() == ekranik.APP_NAME
    assert window.size() == theme.MAIN_WINDOW_SIZE
    window.close()
    assert not window.isVisible()


def test_main_sets_up_the_app_shows_the_window_and_exits_with_0(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    # main() would create a second QApplication; hand it pytest-qt's instead,
    # stripped of the setup that main() itself must apply.
    monkeypatch.setattr(ekranik, "QApplication", lambda _argv: qapp)
    qapp.setOrganizationName("")
    qapp.setApplicationName("pytest")
    qapp.setStyle("Fusion")
    for installed in (
        *qapp.findChildren(theme.Theme),
        *qapp.findChildren(i18n.Translations),
        *qapp.findChildren(settings.Settings),
    ):
        shiboken6.delete(installed)
    shown: list[MainWindow] = []
    setup_while_running: list[object] = []

    def close_main_window() -> None:
        setup_while_running.extend(
            (
                qapp.organizationName(),
                qapp.applicationName(),
                qapp.style().name(),
                len(qapp.findChildren(theme.Theme)),
                len(qapp.findChildren(settings.Settings)),
                len(qapp.findChildren(i18n.Translations)),
                QSettings.defaultFormat(),
            )
        )
        shown.extend(
            w
            for w in qapp.topLevelWidgets()
            if isinstance(w, MainWindow) and w.isVisible()
        )
        for window in shown:
            window.close()

    QTimer.singleShot(0, close_main_window)
    # If closing did not quit the app, end the event loop with an error code
    # instead of hanging the test run.
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(lambda: qapp.exit(1))
    guard.start(5000)
    try:
        # Restored by configure_app() below, so no later test can reach the registry.
        QSettings.setDefaultFormat(QSettings.Format.NativeFormat)
        assert ekranik.main() == 0
    finally:
        guard.stop()
        ekranik.configure_app(qapp)  # for the tests that follow, even after a failure
    assert setup_while_running == [
        ekranik.APP_NAME,
        ekranik.APP_NAME,
        ekranik.STYLE,
        1,
        1,
        1,
        QSettings.Format.IniFormat,
    ]
    assert len(shown) == 1
    assert shown[0].windowTitle() == ekranik.APP_NAME
