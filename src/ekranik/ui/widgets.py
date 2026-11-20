"""Ekranik's own widgets, painted with the theme's colors (no stylesheets, see theme.py)."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QAccessible,
    QAccessibleAnnouncementEvent,
    QColor,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ekranik.ui import theme


class ElidedLabel(QLabel):
    """One line of text that loses its middle to "…" when it doesn't fit.

    For paths: their start and end say the most. The whole text is the tooltip.
    The label takes the width it is given and never widens its window.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:
        super().setText(text)
        self.setToolTip(text)

    def shown_text(self) -> str:
        """The text as it is painted."""
        return self.fontMetrics().elidedText(
            self.text(), Qt.TextElideMode.ElideMiddle, self.contentsRect().width()
        )

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.style().drawItemText(
            painter,
            self.contentsRect(),
            int(self.alignment()),
            self.palette(),
            self.isEnabled(),
            self.shown_text(),
            self.foregroundRole(),
        )


class ComboBox(QComboBox):
    """A combo box that fits its items in every language and ignores the mouse
    wheel until it has the focus, so scrolling a page past it changes nothing."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()  # the page scrolls instead


class Card(QWidget):
    """A Windows 11 settings card: a title and a hint, with the controls on the right.

    The fill and the border come from the theme; in high contrast the border
    takes the palette's text color, so the card stays visible in every contrast
    theme. An error, such as a folder that can't be used, shows under the hint.
    """

    def __init__(
        self,
        *controls: QWidget,
        hint: QLabel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controls = controls
        self.title = QLabel()
        self.hint = QLabel() if hint is None else hint
        if hint is None:
            self.hint.setWordWrap(True)
        theme.set_role(self.hint, theme.Role.SECONDARY)
        self.error = QLabel()
        self.error.setWordWrap(True)
        theme.set_role(self.error, theme.Role.CRITICAL)
        self.error.hide()

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        for label in (self.title, self.hint, self.error):
            text.addWidget(label)
        buttons = QHBoxLayout()
        buttons.setSpacing(theme.Spacing.S)  # Fluent's gap between buttons
        for control in controls:
            buttons.addWidget(control)
        row = QHBoxLayout(self)
        row.setContentsMargins(*(theme.Spacing.L,) * 4)
        row.setSpacing(theme.Spacing.L)
        row.addLayout(text, 1)
        row.addLayout(buttons)

        self._theme = theme.install(QApplication.instance())
        self._theme.changed.connect(self.update)

    def set_title(self, title: str) -> None:
        self.title.setText(title)
        self._describe_controls()

    def set_hint(self, hint: str) -> None:
        self.hint.setText(hint)
        self.hint.setVisible(bool(hint))
        self._describe_controls()

    def set_error(self, error: str) -> None:
        """Show an error under the hint, and have screen readers say it at once;
        an empty one hides it."""
        changed = error != self.error.text()
        self.error.setText(error)
        self.error.setVisible(bool(error))
        self._describe_controls()
        if error and changed and QAccessible.isActive():
            QAccessible.updateAccessibility(
                QAccessibleAnnouncementEvent(self.error, error)
            )

    def _describe_controls(self) -> None:
        """Tell screen readers what each control belongs to.

        Controls are named after the card; a push button keeps the name on its
        face and gets the card's title in its description, so two "Browse…"
        buttons can be told apart. Every description has the hint, such as a
        folder's path, and the error, if any.
        """
        texts = [self.hint.text(), self.error.text()]
        for control in self._controls:
            if isinstance(control, QPushButton):
                about = [self.title.text(), *texts]
            else:
                control.setAccessibleName(self.title.text())
                about = texts
            control.setAccessibleDescription("\n".join(text for text in about if text))

    def colors(self) -> tuple[QColor, QColor]:
        """The fill and the border as they are painted now."""
        colors = self._theme.colors
        if colors is None:  # high contrast: the system's colors
            palette = self.palette()
            return (
                palette.color(QPalette.ColorRole.Window),
                palette.color(QPalette.ColorRole.WindowText),
            )
        return QColor(colors.card_fill), QColor(colors.card_stroke)

    def paintEvent(self, event: QPaintEvent) -> None:
        fill, stroke = self.colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(stroke, theme.STROKE))
        painter.setBrush(fill)
        # Inset by half the stroke, so the border lies inside the card and on
        # whole pixels at 100 % and 200 % (in between, Windows blends it too).
        inset = theme.STROKE / 2
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        painter.drawRoundedRect(rect, theme.Radius.CONTROL, theme.Radius.CONTROL)
