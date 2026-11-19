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

## Development

| Task | Command |
| --- | --- |
| Run the app | `uv run ekranik` |
| Sync the environment with `uv.lock` | `uv sync` |
| Add a dependency | `uv add <package>` |
| Remove a dependency | `uv remove <package>` |
| Upgrade locked dependencies | `uv lock --upgrade` |

`uv add` and `uv remove` update both `pyproject.toml` and `uv.lock`. Commit the two files together so everyone runs the same versions.

### Project layout

```text
ekranik/
├── src/ekranik/      # application package (entry point: ekranik:main)
├── pyproject.toml    # project metadata and dependencies
├── uv.lock           # pinned dependency versions, managed by uv
└── .python-version   # Python version uv uses (3.15)
```

## Roadmap

- [x] Core features (see [Features](#features))
- [ ] Smoke-test every feature
- [ ] Publish on the Microsoft Store, for free

## Support Ekranik

Ekranik is free. If it's useful to you, you can support its development on [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik).

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor_on_GitHub-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## License

Ekranik is released under the [MIT License](LICENSE).
