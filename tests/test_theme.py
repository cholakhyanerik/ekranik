"""The theme: colors per Windows app mode, roles, live switching, rule 15."""

import io
import re
import tokenize
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontInfo, QPalette
from PySide6.QtWidgets import QApplication, QLabel
from pytestqt.qtbot import QtBot

from ekranik.ui import theme

SRC = Path(__file__).parents[1] / "src" / "ekranik"
THEME = SRC / "ui" / "theme.py"

QT_COLORS = (
    "white|black|red|darkRed|green|darkGreen|blue|darkBlue|cyan|darkCyan|magenta"
    "|darkMagenta|yellow|darkYellow|gray|darkGray|lightGray|transparent|color0|color1"
)
IN_STRINGS = re.compile(
    r"#[0-9a-f]{3,8}\b"  # hex colors
    r"|\b(rgba?|hsla?|hsva?)\s*\("  # stylesheet color functions
    # stylesheet color properties: their values belong in the theme
    r"|(?<![\w-])((alternate-|selection-)?background(-color)?|(selection-)?color"
    r"|border(-\w+)?-color|gridline-color)\s*:",
    re.IGNORECASE,
)
IN_CODE = re.compile(
    r"\bQColor\s*\(\s*[\d'\"]"  # QColor from numbers or a color name
    r"|\bQColor\s*\.\s*from\w*\s*\(\s*[\d'\"]"  # fromRgb(0, ...), fromString("red")
    r"|\bQColorConstants\b"
    r"|\bGlobalColor\b"
    rf"|\bQt\s*\.\s*({QT_COLORS})\b",
)
STRING_TOKENS = {tokenize.STRING, tokenize.FSTRING_MIDDLE, tokenize.TSTRING_MIDDLE}


def color_literals_in(source: str) -> list[str]:
    """Color literals in Python source: in its strings and in its Qt calls."""
    tokens = [
        token
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type != tokenize.COMMENT
    ]
    strings = "\n".join(token.string for token in tokens if token.type in STRING_TOKENS)
    code = " ".join(token.string for token in tokens)
    return [m.group() for m in IN_STRINGS.finditer(strings)] + [
        m.group() for m in IN_CODE.finditer(code)
    ]


def color_literals(path: Path) -> list[str]:
    return color_literals_in(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "code",
    [
        'QColor("#ff0000")',
        "QColor(255, 0, 0)",
        'label.setStyleSheet("color: red")',
        'w.setStyleSheet("QWidget { background-color: palette(base) }")',
        "QColor.fromString('white')",
        "QColor.fromRgb(1, 2, 3)",
        "QColorConstants.Svg.red",
        "QPen(Qt.black)",
        "Qt.GlobalColor.red",
        '"rgba(0, 0, 0, 40)"',
    ],
)
def test_the_color_check_finds(code: str) -> None:
    assert color_literals_in(code)


@pytest.mark.parametrize(
    "code",
    [
        "QColor(colors.critical)",
        'QLabel("Record the red channel")',
        "self.tr('Color')",
        "if (color := pick()) is not None: pass",
        "def paint(color: str) -> None: pass",
    ],
)
def test_the_color_check_lets_pass(code: str) -> None:
    assert color_literals_in(code) == []


def test_no_color_literals_outside_the_theme() -> None:
    # The check must see the theme's own colors, or it would see nothing anywhere.
    assert len(color_literals(THEME)) == 2 * len(theme.Colors._fields)
    found = {
        str(path.relative_to(SRC)): literals
        for path in SRC.rglob("*.py")
        if path != THEME and (literals := color_literals(path))
    }
    assert found == {}


@pytest.mark.parametrize(
    ("scheme", "contrast", "expected"),
    [
        (Qt.ColorScheme.Light, Qt.ContrastPreference.NoPreference, theme.LIGHT),
        (Qt.ColorScheme.Dark, Qt.ContrastPreference.NoPreference, theme.DARK),
        (Qt.ColorScheme.Unknown, Qt.ContrastPreference.NoPreference, theme.LIGHT),
        (Qt.ColorScheme.Dark, Qt.ContrastPreference.HighContrast, None),
        (Qt.ColorScheme.Light, Qt.ContrastPreference.HighContrast, None),
    ],
)
def test_colors_for_each_mode(
    scheme: Qt.ColorScheme,
    contrast: Qt.ContrastPreference,
    expected: theme.Colors | None,
) -> None:
    assert theme.colors_for(scheme, contrast) == expected


@pytest.mark.parametrize("body_px", [12, 14, 21, 28])
def test_the_type_ramp_follows_the_body_text(body_px: int) -> None:
    sizes = [theme.font_px(size, body_px) for size in theme.FontSize]
    assert sizes == sorted(sizes)
    assert theme.font_px(theme.FontSize.BODY, body_px) == body_px
    assert theme.font_px(theme.FontSize.TITLE, body_px) == 2 * body_px


def test_text_px_of_the_system_font(qapp: QApplication) -> None:
    # The theme's body size: positive on every platform, offscreen included.
    assert theme.text_px(qapp.font()) > 0
    pixels = QFont()
    pixels.setPixelSize(17)
    assert theme.text_px(pixels) == 17


@pytest.mark.parametrize("points", [9.0, 10.5, 12.0, 15.75, 18.0])
def test_text_px_matches_what_qt_measures(qapp: QApplication, points: float) -> None:
    # text_px() computes at 96 pixels per inch instead of measuring; the system
    # font at 100 % to 200 % "Text size" must come out as Qt draws it.
    if qapp.platformName() == "offscreen":
        pytest.skip("the offscreen platform cannot measure fonts")
    font = QFont(qapp.font())
    font.setPointSizeF(points)
    assert theme.text_px(font) == QFontInfo(font).pixelSize()


def test_install_makes_one_theme(qapp: QApplication) -> None:
    assert theme.install(qapp) is theme.install(qapp)
    assert len(qapp.findChildren(theme.Theme)) == 1


def hex_argb(color: str | QColor) -> str:
    return QColor(color).name(QColor.NameFormat.HexArgb)


def text_color(label: QLabel, group: QPalette.ColorGroup) -> str:
    return hex_argb(label.palette().color(group, QPalette.ColorRole.WindowText))


def make_label(qtbot: QtBot) -> QLabel:
    label = QLabel("Text")
    qtbot.addWidget(label)
    label.show()
    return label


def test_title_role_scales_with_the_body_text(qtbot: QtBot, qapp: QApplication) -> None:
    current = theme.install(qapp)
    # Given after showing: the role must restyle a label that is already on screen.
    title = make_label(qtbot)
    theme.set_role(title, theme.Role.TITLE)
    assert title.font().pixelSize() == theme.font_px(
        theme.FontSize.TITLE, current.body_px
    )
    assert title.font().weight() == QFont.Weight.DemiBold
    assert title.font().family() == qapp.font().family()


def test_text_roles_take_their_color_from_the_theme(
    qtbot: QtBot, qapp: QApplication
) -> None:
    colors = theme.install(qapp).colors
    if colors is None:
        pytest.skip("in high contrast the theme leaves colors to Windows")
    plain = make_label(qtbot)
    plain.setEnabled(False)
    disabled = QPalette.ColorGroup.Disabled
    for role, color in (
        (theme.Role.SECONDARY, colors.text_secondary),
        (theme.Role.CRITICAL, colors.critical),
        (theme.Role.SUCCESS, colors.success),
    ):
        label = make_label(qtbot)
        theme.set_role(label, role)
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            assert text_color(label, group) == hex_argb(color)
        assert label.font().pixelSize() == plain.font().pixelSize()
        # A disabled label keeps the native disabled color, like any other label.
        label.setEnabled(False)
        assert text_color(label, disabled) == text_color(plain, disabled)


def test_without_theme_colors_a_role_inherits_everything(qtbot: QtBot) -> None:
    # High contrast: the system's colors and fonts must win.
    plain = make_label(qtbot)
    label = make_label(qtbot)
    theme.style_label(label, theme.Role.CRITICAL, theme.LIGHT, 12)
    theme.style_label(label, theme.Role.CRITICAL, None, 12)
    assert label.palette().resolveMask() == 0
    assert label.font().resolveMask() == 0
    active = QPalette.ColorGroup.Active
    assert text_color(label, active) == text_color(plain, active)


def test_theme_follows_high_contrast_live(
    qtbot: QtBot, qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = theme.install(qapp)
    if current.colors is None:
        pytest.skip("the test machine is in high contrast already")
    label = make_label(qtbot)
    theme.set_role(label, theme.Role.CRITICAL)
    accessibility = qapp.styleHints().accessibility()
    # Windows turning a contrast theme on, as Qt reports it to the app.
    monkeypatch.setattr(theme, "colors_for", lambda _scheme, _contrast: None)
    with qtbot.waitSignal(current.changed):
        accessibility.contrastPreferenceChanged.emit(Qt.ContrastPreference.HighContrast)
    assert current.colors is None
    assert label.palette().resolveMask() == 0
    monkeypatch.undo()
    with qtbot.waitSignal(current.changed):
        accessibility.contrastPreferenceChanged.emit(Qt.ContrastPreference.NoPreference)
    assert current.colors is not None
    assert label.palette().resolveMask() != 0


def test_theme_follows_the_text_size_live(qtbot: QtBot, qapp: QApplication) -> None:
    current = theme.install(qapp)
    title = make_label(qtbot)
    theme.set_role(title, theme.Role.TITLE)
    start = qapp.font()
    bigger = QFont(start)
    bigger.setPixelSize(2 * current.body_px)
    try:
        with qtbot.waitSignal(current.changed):
            qapp.setFont(bigger)
        assert current.body_px == bigger.pixelSize()
        assert title.font().pixelSize() == theme.font_px(
            theme.FontSize.TITLE, current.body_px
        )
    finally:
        with qtbot.waitSignal(current.changed):
            qapp.setFont(start)


def test_theme_follows_the_windows_app_mode(qtbot: QtBot, qapp: QApplication) -> None:
    # Checked here, not in a skipif: the platform is known once the app exists.
    if qapp.platformName() == "offscreen":
        pytest.skip("the offscreen platform has no light or dark mode")
    current = theme.install(qapp)
    if current.colors is None:
        pytest.skip("in high contrast the theme leaves colors to Windows")
    hint = make_label(qtbot)
    theme.set_role(hint, theme.Role.SECONDARY)
    hints = qapp.styleHints()
    start = hints.colorScheme()
    other = (
        Qt.ColorScheme.Light if start == Qt.ColorScheme.Dark else Qt.ColorScheme.Dark
    )
    try:
        # What Windows does when the app mode changes, without touching the
        # user's Windows setting: Qt's own request for a mode.
        for scheme in (other, start):
            with qtbot.waitSignal(current.changed):
                hints.setColorScheme(scheme)
            expected = theme.colors_for(scheme)
            assert expected is not None
            assert current.colors == expected
            assert text_color(hint, QPalette.ColorGroup.Active) == hex_argb(
                expected.text_secondary
            )
    finally:
        hints.unsetColorScheme()


def test_heading_role_is_semibold_body_text(qtbot: QtBot, qapp: QApplication) -> None:
    plain = make_label(qtbot)
    heading = make_label(qtbot)
    theme.set_role(heading, theme.Role.HEADING)
    assert heading.font().weight() == QFont.Weight.DemiBold
    # The size is inherited, so it follows the Windows text size by itself.
    assert heading.font().pixelSize() == plain.font().pixelSize()
    assert heading.font().pointSizeF() == plain.font().pointSizeF()
    assert heading.palette().resolveMask() == 0
