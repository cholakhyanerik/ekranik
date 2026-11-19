# Ekranik — Tasks

The backlog to version 1.0, the first free release on the Microsoft Store.
How it is kept: [CLAUDE.md](CLAUDE.md), rules 5 and 6.

- **IDs are names, not positions.** `EKR-n` never changes and is never reused;
  re-sorting moves rows, not numbers.
- **Order.** Every task here is needed for 1.0, so the board runs milestone by
  milestone, and each task relies only on rows above it. The next task is the
  first **To Do** row. Priority says what matters most inside a milestone.
- **Small.** XS ≤ 1 hour, S ≤ half a day. Anything bigger is split before work
  starts.
- **Done = deleted.** A finished task loses its entry and its board row;
  [CHANGELOG.md](CHANGELOG.md) and git keep the history.
- **Bugs are not filed here.** A bug found during a task is fixed in that task.
  New features and improvements are added here at once.
- **Needs owner** marks a step only the owner can take (their Microsoft
  account, payment, legal acceptance). Everything before it is prepared.
- **Status:** To Do · In Progress · Needs owner.

**Starting point (2026-11-19).** The repo holds the uv scaffold only. The owner
reports that the core features already exist; if that code arrives, porting
it closes the recording, overlay and hotkey tasks sooner. Otherwise they are
built here.

## Board

| ID | Title | Type | Priority | Size | Milestone | Status |
|---|---|---|---|---|---|---|
| EKR-3 | Theme module with light and dark mode | Task | High | S | M1 Foundation | To Do |
| EKR-4 | Settings storage with schema version | Task | High | S | M1 Foundation | To Do |
| EKR-5 | Settings window | Story | High | S | M1 Foundation | To Do |
| EKR-6 | Translation infrastructure (en, ru, hy) | Task | High | S | M1 Foundation | To Do |
| EKR-7 | Language switcher | Story | Medium | S | M1 Foundation | To Do |
| EKR-8 | Single instance | Story | Medium | S | M1 Foundation | To Do |
| EKR-9 | Recording controller | Task | Highest | S | M2 Recording | To Do |
| EKR-10 | Output folder and file names | Story | High | S | M2 Recording | To Do |
| EKR-11 | Microphone picker | Story | High | S | M2 Recording | To Do |
| EKR-12 | Audio-only recording in full quality | Story | Highest | S | M2 Recording | To Do |
| EKR-13 | Screen picker | Story | High | XS | M2 Recording | To Do |
| EKR-14 | Screen recording at native resolution | Story | Highest | S | M2 Recording | To Do |
| EKR-15 | Frame rate setting and check | Story | High | S | M2 Recording | To Do |
| EKR-16 | Screen recording with microphone | Story | Highest | S | M2 Recording | To Do |
| EKR-17 | Recording errors | Story | High | S | M2 Recording | To Do |
| EKR-18 | Overlay window | Story | Highest | S | M3 Overlay and hotkeys | To Do |
| EKR-19 | Keep the overlay out of recordings | Task | High | XS | M3 Overlay and hotkeys | To Do |
| EKR-20 | Global hotkey engine | Task | Highest | S | M3 Overlay and hotkeys | To Do |
| EKR-21 | Hotkey actions and defaults | Story | High | XS | M3 Overlay and hotkeys | To Do |
| EKR-22 | Hotkey settings page | Story | High | S | M3 Overlay and hotkeys | To Do |
| EKR-23 | Russian translation | Task | High | S | M4 Languages | To Do |
| EKR-24 | Armenian translation | Task | High | S | M4 Languages | To Do |
| EKR-25 | Smoke test of every feature | Task | Highest | S | M5 Quality | To Do |
| EKR-26 | Performance check of long recordings | Task | High | S | M5 Quality | To Do |
| EKR-27 | Drop WebEngine and PDF from the dependencies | Task | Medium | S | M5 Quality | To Do |
| EKR-28 | Minimal CI | Task | Medium | XS | M5 Quality | To Do |
| EKR-29 | About dialog with licenses and Sponsors link | Story | High | S | M6 Store release | To Do |
| EKR-30 | Privacy policy | Task | High | XS | M6 Store release | To Do |
| EKR-31 | App icon and Store images | Task | Medium | S | M6 Store release | To Do |
| EKR-32 | Bundler spike | Spike | High | S | M6 Store release | To Do |
| EKR-33 | Build script for the standalone app | Task | High | S | M6 Store release | To Do |
| EKR-34 | MSIX package | Task | High | S | M6 Store release | To Do |
| EKR-35 | Partner Center account and app name | Task | High | XS | M6 Store release | Needs owner |
| EKR-36 | Store listing in three languages | Task | High | S | M6 Store release | To Do |
| EKR-37 | Submit version 1.0.0 | Task | High | XS | M6 Store release | Needs owner |

## M1 Foundation

### EKR-3 · Theme module with light and dark mode
Task · High · S · `ui`, `design`

**Why.** Rule 15: one source for colors, spacing and fonts.

**What to do.**
- `src/ekranik/ui/theme.py`: light and dark colors, a spacing scale, corner
  radii, font sizes; a small stylesheet built from them.
- Follow the Windows app mode through `QGuiApplication.styleHints()`
  (`colorScheme()` and `colorSchemeChanged`).
- Move the main window's default size (`DEFAULT_SIZE` in `main_window.py`, from
  EKR-1) into the theme.

**Acceptance criteria.**
- [ ] Switching Windows between light and dark updates the app without a restart.
- [ ] No color literals outside `theme.py`.

**Risks.** Heavy stylesheets fight the native `windows11` style; keep them small.

### EKR-4 · Settings storage with schema version
Task · High · S · `settings`

**Why.** Rule 4: settings must survive updates.

**What to do.**
- `src/ekranik/settings.py`: typed accessors over `QSettings` (INI format), all
  defaults in one place, a `schema_version` with one migration step per version.

**Acceptance criteria.**
- [ ] Settings survive a restart.
- [ ] A test migrates a version-0 file; unknown keys are kept.

**Risks.** Inside the MSIX package, writes to `%APPDATA%` go to the package's
private folder: fine for settings, but don't pass that path to other tools.
The tests redirect only INI user settings to a temporary folder
(`tests/conftest.py`): always open `QSettings` with `IniFormat` (or set it as
the default in `configure_app()`), never the registry format, or the tests
write the real settings.

### EKR-5 · Settings window
Story · High · S · `ui`, `settings`

**Why.** Folder, devices, frame rate, hotkeys and language need one home.

**What to do.**
- A settings dialog with pages General, Recording and Hotkeys, opened from the
  main window; values come from and go to `settings.py`.

**Acceptance criteria.**
- [ ] Changes apply at once and persist; Esc cancels, Enter confirms.
- [ ] Every control is reachable with the keyboard.

### EKR-6 · Translation infrastructure (en, ru, hy)
Task · High · S · `i18n`

**Why.** Rule 14: the app ships in English, Russian and Armenian.

**What to do.**
- `QTranslator` loads `ekranik_<lang>.qm`; language = saved choice → Windows
  display language (`QLocale.system().uiLanguages()`) → English.
- `translations/ekranik_ru.ts` and `ekranik_hy.ts` through
  `uv run pyside6-lupdate`; `.qm` files through `uv run pyside6-lrelease`.
  Decide whether `.qm` files are committed or built when packaging.
- Add an `/i18n` skill with the exact commands.

**Acceptance criteria.**
- [ ] A forced language shows Russian or Armenian text; a missing translation
  falls back to English.

**Risks.** lupdate only finds literal strings passed to `tr()` or `translate()`.

### EKR-7 · Language switcher
Story · Medium · S · `i18n`, `ui`

**Why.** People pick their language without changing Windows.

**What to do.**
- Settings → General → Language: English, Русский, Հայերեն, each written in its
  own language.
- Switch live: install the new translator; widgets handle
  `QEvent.LanguageChange` with a `retranslate()` method.

**Acceptance criteria.**
- [ ] Switching updates every visible string at once; the choice persists.

### EKR-8 · Single instance
Story · Medium · S · `app`

**Why.** Two copies would fight over hotkeys and devices.

**What to do.**
- A per-user `QLocalServer` name; a second launch signals the first through
  `QLocalSocket`, which brings its window forward, and then exits.

**Acceptance criteria.**
- [ ] A second launch shows the running window and starts no second process.

## M2 Recording

### EKR-9 · Recording controller
Task · Highest · S · `recording`

**Why.** The window, the overlay and the hotkeys must drive one recording the
same way.

**What to do.**
- `src/ekranik/recording/controller.py`: states idle → starting → recording →
  stopping → idle; one recording at a time; signals for state, elapsed time and
  errors. UI, overlay and hotkeys talk only to it.

**Acceptance criteria.**
- [ ] Tests cover every transition, including stop while starting and an error
  in each state.

### EKR-10 · Output folder and file names
Story · High · S · `recording`, `files`

**Why.** Recordings must land somewhere predictable and never overwrite anything.

**What to do.**
- Defaults through `QStandardPaths`: `Videos\Ekranik` for screen recordings,
  `Music\Ekranik` for audio; changeable in settings.
- Names from the start time, such as `Ekranik 2026-11-19 14-03-27.mp4`; a
  clash adds ` (2)`, ` (3)`.
- An "Open folder" button.

**Acceptance criteria.**
- [ ] Tests for name clashes and for a folder without write access.

### EKR-11 · Microphone picker
Story · High · S · `recording`, `audio`

**Why.** Many PCs have several inputs; the right one must be easy to pick.

**What to do.**
- List inputs with `QMediaDevices.audioInputs()`; default = the system
  default; follow `audioInputsChanged`; save the device ID.

**Acceptance criteria.**
- [ ] Plugging a USB microphone in or out updates the list without a restart.
- [ ] A saved device that is gone falls back to the default, with a notice.

### EKR-12 · Audio-only recording in full quality
Story · Highest · S · `recording`, `audio`

**Why.** A core feature: audio-only recording in full quality.

**What to do.**
- `QMediaCaptureSession` + `QAudioInput` + `QMediaRecorder`, lossless output
  (WAV or FLAC — pick what Qt's FFmpeg backend encodes on Windows and record
  the decision), at the device's native sample rate and channel count.
- Start and stop from the main window through the controller.

**Acceptance criteria.**
- [ ] A one-minute recording plays back; sample rate and channels match the
  device; no lossy codec.

**Risks.** Check `QMediaFormat().supportedFileFormats(QMediaFormat.ConversionMode.Encode)`
at runtime instead of assuming.

### EKR-13 · Screen picker
Story · High · XS · `recording`, `video`

**Why.** With several monitors, the user picks which one to record.

**What to do.**
- List `QGuiApplication.screens()` with name, resolution and refresh rate;
  default = the primary screen; save the choice.

**Acceptance criteria.**
- [ ] Works with one and with two monitors, including different scaling.

### EKR-14 · Screen recording at native resolution
Story · Highest · S · `recording`, `video`

**Why.** A core feature: screen recording in full quality.

**What to do.**
- `QScreenCapture` → `QMediaCaptureSession` → `QMediaRecorder`: MP4 with H.264
  (HEVC where available), `VeryHighQuality`, at the screen's physical pixels
  (logical size × device pixel ratio).

**Acceptance criteria.**
- [ ] On a scaled screen (for example 150 %) the file has the physical
  resolution, and text stays sharp.

**Risks.** Find out which capture API Qt uses on Windows and whether a
hardware encoder is used; record it in CLAUDE.md.

### EKR-15 · Frame rate setting and check
Story · High · S · `recording`, `video`

**Why.** "Full quality, including FPS" — the file must keep the frame rate.

**What to do.**
- Setting: "Screen refresh rate" (default), 60, 30; passed to the recorder
  with `setVideoFrameRate`.
- A test helper that measures the file's real frame rate (frames ÷ duration).

**Acceptance criteria.**
- [ ] While the screen content changes, the measured frame rate is within 2 %
  of the setting over one minute.

**Risks.** Windows delivers new frames only when the screen changes; check
that the file still has a constant frame rate.

### EKR-16 · Screen recording with microphone
Story · Highest · S · `recording`, `audio`, `video`

**Why.** A core feature: screen recording with or without the microphone.

**What to do.**
- Add `QAudioInput` to the screen session; a microphone on/off toggle in the
  main window (its default in settings).

**Acceptance criteria.**
- [ ] Toggle off: the file has no microphone audio. Toggle on: audio stays in
  sync — drift ≤ 100 ms after 10 minutes.

### EKR-17 · Recording errors
Story · High · S · `recording`

**Why.** A lost recording is the worst failure a recorder can have.

**What to do.**
- Handle a microphone or screen that disappears, a full disk, an encoder error,
  and a microphone blocked in the Windows privacy settings.
- A clear message with the fix (a button that opens
  `ms-settings:privacy-microphone`); recording stops cleanly; the partial file
  stays playable.

**Acceptance criteria.**
- [ ] Each error case is reproduced once and handled as described.

**Risks.** An MP4 cut off before its index is written does not play; check what
Qt leaves after a crash, and consider fragmented MP4 if Qt supports it.

## M3 Overlay and hotkeys

### EKR-18 · Overlay window
Story · Highest · S · `overlay`, `ui`

**Why.** A core feature: control and see the recording without the main window.

**What to do.**
- A small frameless always-on-top window (`Qt.Tool`, `FramelessWindowHint`,
  `WindowStaysOnTopHint`): mode, elapsed time, a Stop button; draggable; its
  position saved. Decide whether it also shows start buttons while idle.

**Acceptance criteria.**
- [ ] Stays above other windows during a recording; usable with the keyboard.

### EKR-19 · Keep the overlay out of recordings
Task · High · XS · `overlay`, `video`

**Why.** The overlay must not appear in the recorded video.

**What to do.**
- Call `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` through
  `ctypes` on the overlay's window handle.

**Acceptance criteria.**
- [ ] The overlay is visible on screen and absent from the recorded file.

**Risks.** Needs Windows 10 version 2004 or later; with some capture methods the
window shows as a black box instead — verify with Qt's capture backend.

### EKR-20 · Global hotkey engine
Task · Highest · S · `hotkeys`

**Why.** A core feature: hotkeys work while another app has focus.

**What to do.**
- Win32 `RegisterHotKey`/`UnregisterHotKey` through `ctypes`, plus a
  `QAbstractNativeEventFilter` for `WM_HOTKEY`; report registration failures
  (a combination another app already holds).

**Acceptance criteria.**
- [ ] Hotkeys fire with another app focused; all are released on exit.
- [ ] Tests for turning a key sequence into Win32 modifiers and key codes.

### EKR-21 · Hotkey actions and defaults
Story · High · XS · `hotkeys`

**Why.** Useful defaults so it works out of the box.

**What to do.**
- Actions: start/stop audio recording, start/stop screen recording, show/hide
  the overlay. Pick defaults that don't clash with Windows or common apps, and
  record them in CLAUDE.md.

**Acceptance criteria.**
- [ ] Every action works from any app with the default hotkeys.

### EKR-22 · Hotkey settings page
Story · High · S · `hotkeys`, `ui`

**Why.** A core feature: customizable hotkeys.

**What to do.**
- Settings → Hotkeys: a `QKeySequenceEdit` per action, a conflict check (inside
  the app and against Windows registration), "Reset to defaults"; saved.

**Acceptance criteria.**
- [ ] A taken combination shows a clear message and is not saved.
- [ ] Changes apply without a restart.

## M4 Languages

### EKR-23 · Russian translation
Task · High · S · `i18n`

**Why.** Rule 14.

**What to do.**
- Translate every string in `ekranik_ru.ts`; check each screen for cut-off
  text.

**Acceptance criteria.**
- [ ] `pyside6-lrelease` reports no unfinished translations; every screen is
  checked in Russian.

### EKR-24 · Armenian translation
Task · High · S · `i18n`

**Why.** Rule 14.

**What to do.**
- Translate every string in `ekranik_hy.ts`, using established Windows and
  software terms rather than invented words.
- Check that Armenian script renders in every widget; add a fallback font if
  needed.

**Acceptance criteria.**
- [ ] `pyside6-lrelease` reports no unfinished translations; every screen is
  checked in Armenian.

## M5 Quality

### EKR-25 · Smoke test of every feature
Task · Highest · S · `qa`

**Why.** The owner's plan: smoke-test everything before the Store release.

**What to do.**
- `docs/smoke-test.md`: a checklist of every mode, microphone on/off, frame
  rates, overlay, hotkeys, the three languages and the error cases.
- Run it on Windows 11; record the date, version and result in the file.

**Acceptance criteria.**
- [ ] Every line passes, or what failed has been fixed (rule 6).

### EKR-26 · Performance check of long recordings
Task · High · S · `qa`, `performance`

**Why.** Rule 3, and long recordings are where leaks show.

**What to do.**
- A 10-minute screen recording at 60 FPS on the largest available screen, and a
  10-minute audio recording: CPU, memory, dropped frames, file size.
- Put the numbers in CLAUDE.md with the date; fix hot spots.

**Acceptance criteria.**
- [ ] No memory growth over the 10 minutes; no dropped frames on the dev machine.

### EKR-27 · Drop WebEngine and PDF from the dependencies
Task · Medium · S · `performance`, `dependencies`

**Why.** The `pyside6` package also pulls `pyside6-webengine` (349 MB
installed) and `pyside6-pdf` (6 MB) — more than half of the 655 MB PySide6
install, unused by a recorder and paid for in every download.

**What to do.**
- Depend on `pyside6-essentials` and `pyside6-addons` (Qt Multimedia lives in
  Addons) instead of `pyside6`.

**Acceptance criteria.**
- [ ] The app and the tests run; the installed size drops by about 350 MB.

**Risks.** Check that every Qt module the app imports is still present.

### EKR-28 · Minimal CI
Task · Medium · XS · `ci`

**Why.** Rule 4 on every push, at no cost to the owner's shared minutes
(rule 11: standard runners are free for this public repo).

**What to do.**
- One workflow on `windows-latest`: `uv sync --locked`, `uv run ruff format
  --check .`, `uv run ruff check .`, `uv run pytest`.
- `paths-ignore` for `**.md`, `LICENSE` and `.claude/**`; `concurrency` with
  `cancel-in-progress`; `timeout-minutes: 15`; actions pinned by full commit
  SHA; `permissions: contents: read`.

**Acceptance criteria.**
- [ ] A code push runs it once; a docs-only push does not run it.

**Risks.** If the runner has no usable desktop, set `QT_QPA_PLATFORM=offscreen`;
the tests pass that way locally (2026-11-19).

## M6 Store release

### EKR-29 · About dialog with licenses and Sponsors link
Story · High · S · `ui`, `legal`

**Why.** Qt and PySide6 are LGPLv3: their notices must ship with the app. Also
the donation link.

**What to do.**
- Version, MIT license, third-party notices with the Qt and PySide6 license
  texts, links to the GitHub repo and GitHub Sponsors.

**Acceptance criteria.**
- [ ] Every link opens in the browser; the license texts are part of the build.

**Risks.** Check the Microsoft Store policies on donation links before release.

### EKR-30 · Privacy policy
Task · High · XS · `legal`

**Why.** The Store asks for a privacy policy when an app accesses personal data
such as the microphone.

**What to do.**
- `PRIVACY.md`: Ekranik works offline, collects and sends nothing; recordings
  stay where the user saves them. Link it from README, the About dialog and the
  Store listing.

**Acceptance criteria.**
- [ ] The GitHub URL of `PRIVACY.md` is ready for Partner Center.

### EKR-31 · App icon and Store images
Task · Medium · S · `design`

**Why.** The window, the taskbar and the Store listing need an identity.

**What to do.**
- An app icon (`.ico` with sizes 16–256 px), plus the Store logos and
  screenshots Partner Center asks for; `.gitattributes` marks images as binary.

**Acceptance criteria.**
- [ ] The icon shows in the title bar, the taskbar and Alt+Tab; the Store images
  have the sizes Partner Center lists.

### EKR-32 · Bundler spike
Spike · High · S · `packaging`

**Why.** The Store needs a standalone app, not a Python environment.

**What to do.**
- Compare `pyside6-deploy` (Nuitka) with PyInstaller in one-folder mode:
  size, startup time, antivirus false positives, Qt Multimedia plugins.
- Pick one and record the decision in CLAUDE.md.

**Acceptance criteria.**
- [ ] The chosen build starts on a Windows account without Python, and records
  audio and screen.

### EKR-33 · Build script for the standalone app
Task · High · S · `packaging`

**Why.** One repeatable command instead of manual steps.

**What to do.**
- `tools/build.py`, run with `uv run`: from a clean checkout to the standalone
  app folder, with the version taken from pyproject.toml.
- Bundle the runtime dependencies only (`--no-dev`): pytest and ruff stay out
  of the app.

**Acceptance criteria.**
- [ ] A clean clone builds with one command; the output stays out of git.

### EKR-34 · MSIX package
Task · High · S · `packaging`

**Why.** The package format the Store takes.

**What to do.**
- `packaging/AppxManifest.xml` with `runFullTrust`, the microphone device
  capability and the Store logos; a placeholder identity until EKR-35 provides
  the real one. Pack with `makeappx pack` from the Windows SDK.
- Test the install locally with a self-signed test certificate kept outside the
  repo (rule 9); the Store signs the uploaded package itself.

**Acceptance criteria.**
- [ ] The MSIX installs, starts, records with the microphone and uninstalls
  cleanly.

**Risks.** File-system virtualization of `%APPDATA%` (EKR-4); the microphone
privacy prompt for packaged apps.

### EKR-35 · Partner Center account and app name
Task · High · XS · `store` · **Needs owner**

**Why.** Only the owner can open a developer account with their Microsoft
account and reserve the name.

**What to do.**
- Prepared: the exact steps, and the values to copy back for EKR-34
  (Package/Identity/Name, Publisher, PublisherDisplayName).
- Owner: register an individual developer account in Partner Center and
  reserve the name "Ekranik".

**Acceptance criteria.**
- [ ] The real identity values are in `packaging/AppxManifest.xml`.

### EKR-36 · Store listing in three languages
Task · High · S · `store`, `i18n`

**Why.** The listing sells the app in the same three languages it speaks.

**What to do.**
- Description, short description, feature list and keywords in English,
  Russian and Armenian; screenshots; category; the age-rating questionnaire;
  price "Free". Keep the texts in `packaging/store/` so they are versioned.

**Acceptance criteria.**
- [ ] Everything Partner Center asks for is ready to paste; entering it needs
  the owner's account.

**Risks.** Check that Partner Center offers Armenian as a listing language.

### EKR-37 · Submit version 1.0.0
Task · High · XS · `store`, `release` · **Needs owner**

**Why.** The goal of 1.0: Ekranik on the Microsoft Store, for free.

**What to do.**
- Prepared: version 1.0.0, CHANGELOG entry, the MSIX, the listing.
- Owner: upload and submit in Partner Center.
- After approval: the Store link goes into README's "Microsoft Store" section.

**Acceptance criteria.**
- [ ] Ekranik is live on the Microsoft Store for free, and README links to it.
