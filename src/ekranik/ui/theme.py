"""Ekranik's design tokens: colors, spacing, corner radii, font sizes, window sizes.

The one source of them (CLAUDE.md, rule 15): widgets take their look from here
and hold no color or size literals. Qt's native ``windows11`` style draws the
standard controls and already follows light and dark mode. Ekranik's own text
roles (titles, hints, status text) get their font and color through
``set_role()``, and the theme re-applies them when Windows changes the app
mode, high contrast or the text size, without a restart.

There is no app-wide stylesheet on purpose: it routes every widget through
Qt's stylesheet style and doubled the time to build and first paint 210
standard controls (34 → 67 ms, measured 2026-11-19), even widgets no rule
matched (CLAUDE.md, rule 3).

The values follow the Windows 11 (Fluent) design: the 4-pixel spacing grid, the
control and overlay corner radii, the type ramp and the text and status colors.
Sizes are device-independent pixels, so they scale with the display.
"""

from enum import IntEnum, StrEnum
from typing import NamedTuple

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget


class Colors(NamedTuple):
    """The colors of one mode, as hex strings for ``QColor``."""

    text_secondary: str
    """Hints, captions and status text."""
    critical: str
    """Errors and the recording indicator."""
    success: str
    """Confirmations, such as a saved recording."""


LIGHT = Colors(text_secondary="#5c5c5c", critical="#c42b1c", success="#0f7b0f")
DARK = Colors(text_secondary="#cccccc", critical="#ff99a4", success="#6ccb5f")


class Spacing(IntEnum):
    """Margins and gaps: the Windows 11 4-pixel grid."""

    XS = 4
    S = 8
    M = 12
    L = 16
    XL = 24
    XXL = 32


class Radius(IntEnum):
    """Corner radii."""

    CONTROL = 4
    """Buttons, fields and cards inside a window."""
    OVERLAY = 8
    """Top-level surfaces such as the recording overlay and flyouts."""


class FontSize(IntEnum):
    """The Windows 11 type ramp, in Fluent's pixels, where body text is 14.

    Use ``font_px()``: Windows sets the real body size (Qt's default is 12
    pixels, and "Text size" in Windows settings makes it bigger).
    """

    CAPTION = 12
    BODY = 14
    BODY_LARGE = 18
    SUBTITLE = 20
    TITLE = 28


def font_px(size: FontSize, body_px: int) -> int:
    """A ramp size scaled to the system's body text, so the ramp keeps its order."""
    return round(body_px * size / FontSize.BODY)


LOGICAL_DPI = 96
"""Qt on Windows sizes fonts at 96 device-independent pixels per inch, at any scale."""


def text_px(font: QFont) -> int:
    """A font's size in device-independent pixels, as Qt draws it on Windows.

    Computed, not measured: ``QFontInfo`` loads the font engine, which cost
    12-14 ms at startup (2026-11-19), and gives -1 on the offscreen platform.
    A test checks the result against ``QFontInfo`` on the real platform.
    """
    if font.pixelSize() > 0:
        return font.pixelSize()
    return round(font.pointSizeF() * LOGICAL_DPI / 72)


MAIN_WINDOW_SIZE = QSize(640, 400)
"""The main window's size on first open."""

ROLE = "role"
"""The widget property that holds a widget's role."""


class Role(StrEnum):
    """What a label is for; the theme gives each role its font or color."""

    TITLE = "title"
    SUBTITLE = "subtitle"
    SECONDARY = "secondary"
    CRITICAL = "critical"
    SUCCESS = "success"


_ROLE_SIZES = {Role.TITLE: FontSize.TITLE, Role.SUBTITLE: FontSize.SUBTITLE}


def _role_color(role: Role, colors: Colors) -> str | None:
    match role:
        case Role.SECONDARY:
            return colors.text_secondary
        case Role.CRITICAL:
            return colors.critical
        case Role.SUCCESS:
            return colors.success
        case _:
            return None


def style_label(
    widget: QWidget, role: Role, colors: Colors | None, body_px: int
) -> None:
    """Give a widget the font and text color of a role; whatever the role leaves
    open is inherited, as if nothing had been set.

    The color goes into the enabled palette groups only, so a disabled label
    keeps the native disabled color. ``colors`` is ``None`` in high contrast,
    where the system's colors must win.
    """
    font = QFont()
    font.setResolveMask(0)  # inherit family, size and weight unless set below
    if (size := _ROLE_SIZES.get(role)) is not None:
        font.setPixelSize(font_px(size, body_px))
        font.setWeight(QFont.Weight.DemiBold)
    widget.setFont(font)

    palette = QPalette()
    palette.setResolveMask(0)  # inherit every color unless set below
    if colors is not None and (color := _role_color(role, colors)) is not None:
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            palette.setColor(group, QPalette.ColorRole.WindowText, QColor(color))
    widget.setPalette(palette)


def colors_for(
    scheme: Qt.ColorScheme,
    contrast: Qt.ContrastPreference = Qt.ContrastPreference.NoPreference,
) -> Colors | None:
    """The colors for a Windows app mode; an unknown mode counts as light.

    ``None`` in high contrast: then the system's contrast colors must win.
    """
    if contrast == Qt.ContrastPreference.HighContrast:
        return None
    return DARK if scheme == Qt.ColorScheme.Dark else LIGHT


class Theme(QObject):
    """Follows the Windows app mode, high contrast and text size, live."""

    changed = Signal()
    """Emitted after the colors or the body text size changed, for widgets that
    paint themselves.

    The native palette follows one event-loop pass later, so call ``update()``
    and paint then; don't read the palette inside the slot.
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._colors: Colors | None = None
        self._body_px = 0
        hints = app.styleHints()
        hints.colorSchemeChanged.connect(self.refresh)
        hints.accessibility().contrastPreferenceChanged.connect(self.refresh)
        app.fontChanged.connect(self.refresh)
        self.refresh()

    @property
    def colors(self) -> Colors | None:
        """The current colors; ``None`` in high contrast, where the system's apply."""
        return self._colors

    @property
    def body_px(self) -> int:
        """The system's body text size in pixels, for ``font_px()``."""
        return self._body_px

    def apply(self, widget: QWidget, role: Role) -> None:
        """Style a widget for its role with the current colors and text size."""
        style_label(widget, role, self._colors, self._body_px)

    def refresh(self) -> None:
        """Re-style every widget with a role, if the colors or text size changed."""
        hints = self._app.styleHints()
        colors = colors_for(
            hints.colorScheme(), hints.accessibility().contrastPreference()
        )
        body_px = text_px(self._app.font())
        if (colors, body_px) == (self._colors, self._body_px):
            return
        self._colors, self._body_px = colors, body_px
        for widget in self._app.allWidgets():
            if role := widget.property(ROLE):
                self.apply(widget, Role(role))
        self.changed.emit()


def install(app: QApplication) -> Theme:
    """Make the app follow the theme; calling it again returns the same ``Theme``."""
    theme = app.findChild(Theme)
    return theme if theme is not None else Theme(app)


def set_role(widget: QWidget, role: Role) -> None:
    """Give a label a role: its font and color then follow the theme."""
    widget.setProperty(ROLE, role.value)
    install(QApplication.instance()).apply(widget, role)
