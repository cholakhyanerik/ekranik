"""Ekranik's own widgets: the settings card and the eliding label."""

import pytest
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPalette, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pytestqt.qtbot import QtBot

from ekranik.ui import theme
from ekranik.ui.widgets import Card, ComboBox, ElidedLabel


def render(card: Card) -> QImage:
    """The card as it paints itself, at one device pixel per pixel."""
    card.resize(QSize(240, 72))
    image = QImage(card.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    card.render(image)
    return image


def pixel(image: QImage, x: int, y: int) -> str:
    return QColor(image.pixel(x, y)).name()


def test_a_card_paints_the_theme_colors(qtbot: QtBot, qapp: QApplication) -> None:
    colors = theme.install(qapp).colors
    if colors is None:
        pytest.skip("in high contrast the card paints the system's colors")
    card = Card()
    qtbot.addWidget(card)
    image = render(card)
    assert pixel(image, 120, 36) == colors.card_fill
    assert pixel(image, 120, 0) == colors.card_stroke  # the border, on whole pixels
    assert pixel(image, 120, 71) == colors.card_stroke
    assert card.styleSheet() == ""


def test_in_high_contrast_a_card_has_a_border_in_the_text_color(
    qtbot: QtBot, qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(theme.install(qapp), "_colors", None)
    card = Card()
    qtbot.addWidget(card)
    image = render(card)
    palette = card.palette()
    assert pixel(image, 120, 36) == palette.color(QPalette.ColorRole.Window).name()
    assert pixel(image, 120, 0) == palette.color(QPalette.ColorRole.WindowText).name()


class PaintCounter(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def eventFilter(self, _watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Paint:
            self.count += 1
        return False


def test_a_card_repaints_when_the_theme_changes(
    qtbot: QtBot, qapp: QApplication
) -> None:
    card = Card()
    qtbot.addWidget(card)
    with qtbot.waitExposed(card):
        card.show()
    counter = PaintCounter()
    card.installEventFilter(counter)
    qtbot.wait(50)  # let the first paint pass
    counter.count = 0
    theme.install(qapp).changed.emit()
    qtbot.waitUntil(lambda: counter.count > 0)


def test_a_card_names_its_controls_for_screen_readers(qtbot: QtBot) -> None:
    switch = QCheckBox()
    browse = QPushButton("Browse…")
    card = Card(switch, browse)
    qtbot.addWidget(card)
    card.set_title("Microphone")
    card.set_hint("New screen recordings include the microphone.")
    # A control without text of its own is named after the card ...
    assert switch.accessibleName() == "Microphone"
    # ... a button keeps its own name, and says which card it belongs to.
    assert browse.accessibleName() == ""
    assert switch.accessibleDescription() == card.hint.text()
    assert browse.accessibleDescription() == f"Microphone\n{card.hint.text()}"
    # An error is part of the description too.
    card.set_error("No microphone.")
    assert switch.accessibleDescription() == f"{card.hint.text()}\nNo microphone."
    card.set_hint("")
    assert not card.hint.isVisibleTo(card)


def test_a_card_shows_an_error_only_while_there_is_one(qtbot: QtBot) -> None:
    card = Card()
    qtbot.addWidget(card)
    assert not card.error.isVisibleTo(card)
    card.set_error("This folder can't be used.")
    assert card.error.isVisibleTo(card)
    assert card.error.property(theme.ROLE) == theme.Role.CRITICAL.value
    card.set_error("")
    assert not card.error.isVisibleTo(card)


def test_an_elided_label_shortens_the_middle_and_never_widens_its_window(
    qtbot: QtBot,
) -> None:
    label = ElidedLabel()
    qtbot.addWidget(label)
    path = "C:\\Users\\someone\\" + "very long folder name\\" * 10 + "Ekranik"
    label.setText(path)
    label.resize(200, label.sizeHint().height())
    shown = label.shown_text()
    assert shown != path
    assert shown.startswith("C:\\") and shown.endswith("Ekranik")
    assert "…" in shown
    assert label.toolTip() == path
    assert label.minimumSizeHint().width() == 0
    label.resize(label.fontMetrics().horizontalAdvance(path) + 10, 30)
    assert label.shown_text() == path


def test_a_combo_box_ignores_the_wheel_until_it_has_the_focus(
    qtbot: QtBot, qapp: QApplication
) -> None:
    page = QWidget()
    layout = QVBoxLayout(page)
    other = QPushButton("Another control")
    box = ComboBox()
    box.addItems(["a", "b", "c"])
    layout.addWidget(other)
    layout.addWidget(box)
    qtbot.addWidget(page)
    with qtbot.waitExposed(page):
        page.show()
    other.setFocus()  # the user is somewhere else, scrolling the page
    assert not box.hasFocus()
    center = QPointF(box.rect().center())

    def wheel_down() -> None:
        event = QWheelEvent(
            center,
            box.mapToGlobal(center),
            QPoint(),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        qapp.sendEvent(box, event)

    wheel_down()
    assert box.currentIndex() == 0
    assert box.focusPolicy() == Qt.FocusPolicy.StrongFocus
    box.setFocus()
    if not box.hasFocus():
        pytest.skip("the test window could not take the focus")
    wheel_down()
    assert box.currentIndex() == 1
