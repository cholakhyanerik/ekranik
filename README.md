# Ekranik

Screen and audio recorder for Windows.

[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)](#run-from-source)
[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Managed with uv](https://img.shields.io/badge/managed_with-uv-DE5FE9)](https://docs.astral.sh/uv/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-%E2%9D%A4-EA4AAA?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

Ekranik is a desktop app with a graphical interface for recording audio, or your screen with or without your microphone. It's written in Python with PySide6 (Qt for Python) and runs on Windows only. It's free, and it's coming soon to the Microsoft Store.

## Features

- **Audio-only recording** in full quality.
- **Screen recording** in full quality, at full frame rate (FPS).
- **With or without a microphone**: include your microphone in screen recordings, or leave it out.
- **Overlay with customizable hotkeys** for audio and screen recording.
- **Native Windows 11 look** that follows your light or dark mode live and respects contrast themes.

## Installation

### Microsoft Store

Coming soon. Once every feature has passed a smoke test, Ekranik will be published on the Microsoft Store as a free app. Until then, run it from source.

### Run from source

**Requirements:** Windows and [uv](https://docs.astral.sh/uv/), Astral's Python package and project manager. Using uv is required: the project is built, run and managed with it, so don't install dependencies with `pip`. You don't need to install Python yourself. If Python 3.15 is missing, uv downloads it.

1. Install uv, then open a new terminal so the `uv` command is available:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Or with WinGet: `winget install --id=astral-sh.uv -e`

2. Clone the repository and start the app:

   ```powershell
   git clone https://github.com/cholakhyanerik/ekranik.git
   cd ekranik
   uv run ekranik
   ```

`uv run` creates the virtual environment, installs the exact dependency versions pinned in `uv.lock`, and launches Ekranik. The first run takes longer because uv downloads Python and PySide6 (a few hundred MB).

For now the main window is empty: recording arrives with the milestones in the [Roadmap](#roadmap).

## Development

| Task | Command |
| --- | --- |
| Run the app | `uv run ekranik` |
| Sync the environment with `uv.lock`, dev tools included | `uv sync` |
| Format and lint | `uv run ruff format .` and `uv run ruff check .` |
| Run the tests | `uv run pytest` |
| Add a dependency | `uv add <package>` |
| Remove a dependency | `uv remove <package>` |
| Upgrade locked dependencies | `uv lock --upgrade` |

`uv add` and `uv remove` update both `pyproject.toml` and `uv.lock`. Commit the two files together so everyone runs the same versions.

The project is developed with [Claude Code](https://code.claude.com/docs): [CLAUDE.md](CLAUDE.md) holds the working rules, and `.claude/` holds the agents, skills and hooks that enforce them.

### Project layout

```text
ekranik/
├── src/ekranik/      # application package (entry point: ekranik:main)
│   └── ui/           # windows and widgets
├── tests/            # pytest and pytest-qt tests
├── .claude/          # Claude Code agents, skills and hooks
├── CLAUDE.md         # working rules for Claude Code
├── Tasks.md          # backlog to version 1.0
├── CHANGELOG.md      # changes in each version
├── pyproject.toml    # project metadata, dependencies and ruff settings
├── uv.lock           # pinned dependency versions, managed by uv
└── .python-version   # Python version uv uses (3.15)
```

## Roadmap

Version 1.0 is the first release on the Microsoft Store. The work is planned as small tasks in [Tasks.md](Tasks.md), in six milestones:

1. Foundation: main window, settings, theme, tests
2. Recording: audio only, and the screen in full quality and frame rate, with or without the microphone
3. Overlay and customizable hotkeys
4. Interface in English, Russian and Armenian
5. Quality: a smoke test of every feature and performance checks
6. Free release on the Microsoft Store

What changed in each version is in [CHANGELOG.md](CHANGELOG.md).

## Support Ekranik

Ekranik is free. If it's useful to you, you can support its development on [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik).

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor_on_GitHub-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## License

Ekranik is released under the [MIT License](LICENSE).
