# Changelog

Notable changes to Ekranik, newest first. Versions: patch for every finished
task, minor when a milestone in [Tasks.md](Tasks.md) is complete, 1.0.0 for the
first Microsoft Store release.

## 0.1.6 — 2026-11-20

### Added

- A settings window. Open it with the new **Settings** button in the main
  window or with `Ctrl+,`. Its Recording page holds:
  - the folders for screen recordings and for audio recordings: **Browse…**
    picks another one, **Restore default** goes back to `Videos\Ekranik` or
    `Music\Ekranik`, which then follows Windows again if you move those folders;
  - the frame rate of screen recordings: the screen's refresh rate, 60 or
    30 fps;
  - whether new screen recordings include the microphone.
- Changes apply at once. **OK** or Enter keeps them; **Cancel**, Esc or closing
  the window takes back everything you changed since you opened it, and a
  folder you never chose keeps following Windows.
- Settings sit in cards, as in Windows 11, in light, dark and contrast themes,
  and the window grows with the Windows text size. Every control works with the
  keyboard (Tab, Ctrl+Tab between pages, Enter, Esc), and focus stays in its
  card after **Restore default**. Scrolling the page with the mouse wheel never
  changes a setting on the way. Screen readers announce each control with the
  setting it belongs to, and say at once when a folder can't be used. A long
  folder path is shortened in the middle, with the full path in its tooltip.

### Changed

- Starting Ekranik takes no longer: the settings window's code loads the first
  time you open it (about 30 ms then), which keeps 7–10 ms off every start.

### Security

- Folders are chosen in Windows' own folder picker, which Ekranik calls
  directly. Qt's file dialog, which shows the same picker, would save the last
  folder you browsed in a registry key that every Qt app on your PC shares
  (`HKCU\Software\QtProject`), and nothing turns that off; Ekranik writes
  nothing to the registry (Windows itself remembers only the picker's window
  size). The picker also keeps the folder out of Windows' recent items.
- A folder whose name contains hidden text-direction or control characters is
  refused with a message, so the folder you see is the one Ekranik uses.

## 0.1.5 — 2026-11-19

### Added

- Ekranik keeps its settings in a small file, `%APPDATA%\Ekranik\Ekranik.ini`,
  and they survive updates: the file carries a version number, and when a later
  Ekranik renames a setting, it moves your value to the new name instead of
  dropping it. Settings it doesn't know, such as those of a newer Ekranik, are
  kept. A value it can't read, such as a mistyped hand edit, counts as the
  default until you choose a new one.
- The first settings and their defaults: screen recordings are saved to
  `Videos\Ekranik` and audio recordings to `Music\Ekranik`, and screen
  recordings use the screen's refresh rate and include the microphone. Until
  you choose a folder, the default follows Windows when you move your Videos
  or Music folder; a folder you choose stays the one you chose. A settings
  window to change them comes in a later version, and recording after that.

### Changed

- Opening and reading the settings adds under 1 ms to the start, plus about
  3 ms to load the code.
- Ruff, the development tool for formatting and linting, is updated from 0.17.5
  to 0.17.6.

### Security

- Ekranik reads and writes only your own settings file: nothing goes to the
  Windows registry, and a settings file in `C:\ProgramData`, which any user of
  the PC can create, is ignored, so nobody else can redirect your recordings.
- A recording folder must be a full path on a drive or a network share. Windows
  device paths and hidden control or text-direction characters are refused, so
  the folder you see is always the folder that is used.
- The tests keep their recording folders and system-wide settings in temporary
  folders too, so they can never touch your Videos or Music folder.

## 0.1.4 — 2026-11-19

### Added

- Ekranik follows the Windows light or dark mode while it runs: switching it in
  Windows settings updates the app at once, without a restart. It also reacts
  to contrast themes, where it uses only the colors Windows chose, and to a
  larger system text size, where titles grow with the body text.
- One design system for every screen (`src/ekranik/ui/theme.py`): the Windows 11
  spacing, corner radii and type ramp, and colors for hints, errors and
  confirmations in light and dark mode, all readable at WCAG AA contrast or
  better. Titles scale with the Windows text size; disabled text keeps the
  standard Windows look.

### Changed

- The main window's size now comes from the theme (still 640 × 400). Start-up
  time is unchanged at about 0.3–0.4 s: the theme avoids a global stylesheet,
  which would have doubled the time to build every window.

## 0.1.3 — 2026-11-19

### Added

- Automated tests with pytest and pytest-qt, run with `uv run pytest`. They
  check that Ekranik starts with its name and the Windows 11 style, opens its
  main window and quits with exit code 0 when the window closes, so later
  changes can't silently break startup. Both tools are development-only: they
  are not part of the app, and they bring their own small helpers (colorama,
  iniconfig, packaging, pluggy, pygments, typing-extensions).

### Security

- The tests never read or overwrite your own Ekranik settings: they keep
  settings and app data in temporary test folders.

## 0.1.2 — 2026-11-19

### Added

- `uv run ekranik` now opens the Ekranik main window instead of printing a
  placeholder. The window is still empty: it is the base that the recording
  controls will be built on. It uses Qt's native Windows 11 style, opens at
  640 × 400 (scaled with the display), appears in about 0.4 s, and closing it
  quits the app.

## 0.1.1 — 2026-11-19

### Added

- `CLAUDE.md` with the project's working rules for Claude Code.
- `Tasks.md` with the backlog to version 1.0, in six milestones.
- Claude Code agents, skills and hooks in `.claude/`. The hooks check the Python
  version and the dependencies when a session starts, block risky git and pip
  commands and commits that contain secrets, and run ruff after every Python edit.
- Ruff as the development tool for formatting and linting, with security and
  performance rules.
- This changelog.

### Fixed

- The package description in `pyproject.toml` was still uv's placeholder.

## 0.1.0 — 2026-11-19

### Added

- Project scaffold with uv and PySide6.
- README, MIT license and a GitHub Sponsors button.
