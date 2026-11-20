# CLAUDE.md — Ekranik

Ekranik is a Windows-only desktop app that records the screen and audio. It is
written in Python 3.15 with PySide6 (Qt for Python) and managed with uv.
Version 1.0 is the first release on the Microsoft Store, free of charge.
Repo: github.com/cholakhyanerik/ekranik — public, MIT, default branch
`master`, donations through GitHub Sponsors (`.github/FUNDING.yml`).

The rules below come from the owner (2026-11-19) and bind every change; the
numbers are the owner's, keep them. This file stays in English and under ~200
lines: procedures live in skills, this file keeps the rule and its reason.

**State on 2026-11-20:** `uv run ekranik` opens the main window, in English,
Russian or Armenian, with a Settings button (`main()` → `configure_app()`: name,
style, theme, settings, language); no recording yet. Tasks.md: the road to 1.0.

## Commands

| What | Command |
| --- | --- |
| Run the app | `uv run ekranik` |
| Install or refresh the environment, dev tools included | `uv sync` |
| Format and lint | `uv run ruff format .` · `uv run ruff check .` |
| Tests | `uv run pytest` |
| Outdated direct dependencies | `uv tree --outdated --depth 1` |
| Upgrade all locked versions | `uv lock --upgrade`, then `uv sync` |
| Bump the version | `uv version --bump patch` (or `minor`) |
| Collect texts, build translations (`--check`: verify) | `uv run tools/translations.py` |
| Hook self-test | `python -I .claude/hooks/selftest.py` |

uv is required: never `pip install` into the project — `uv add` and
`uv remove` keep pyproject.toml and uv.lock in step. The one exception is uv
itself, installed with pip into the system Python:
`python -m pip install --upgrade uv`.

## Rules

**1. Python follows the system Python.** The project's Python (major.minor)
equals the system Python — the `python` on PATH, 3.15.2 today. When the system
Python changes, the project follows in that session: `.python-version`,
`requires-python`, README (badge and text), `uv sync`, checks; new ruff `UP`
findings are fixed in the code, not silenced. The SessionStart hook prints the
comparison. PySide6 wheels are `abi3`, so a newer Python rarely needs a newer
PySide6.

**2. Dependencies first.** Before every task: `uv tree --outdated --depth 1`
(the SessionStart hook runs it and also checks uv and the `uv_build` bound).
Updates → `uv lock --upgrade`, `uv sync`, checks. Breakage → adapt the code
instead of pinning back; read the new API in `.venv/Lib/site-packages/`
(PySide6 ships `.pyi` stubs), not from memory; note notable adaptations here.

**3. Optimized code.** Fast start. Nothing blocks the GUI thread — capture,
encoding and file I/O run in Qt Multimedia or worker threads; no per-frame
Python work in the capture path; no timers or polling while idle. Equal result
→ the cheaper way. Measure before claiming a speed-up. Ruff's `PERF` rules are on.

**4. Nothing that worked may break.** Recording modes, microphone on/off,
frame rate, overlay, hotkeys, settings and file names keep working. Settings
carry a schema version; renamed keys are migrated, not dropped. Every feature
and every fixed bug gets a test (pytest + pytest-qt, EKR-2), and the tests run
before every commit.

**5. Tasks.md is the backlog.** Every planned task lives there, Jira-style: ID,
type, priority, size, milestone, why, what to do, acceptance criteria, risks.
IDs (`EKR-n`) never change and are never reused. Tasks are as small as
possible — XS ≤ 1 hour, S ≤ half a day; anything bigger is split first. Every
session updates, improves and re-sorts the tasks and deletes the finished ones
(entry and board row), so Tasks.md is always current.

**6. Bugs are fixed now.** A bug or defect found during a task is fixed in that
task, with a test — not filed. Only new features and improvements go to Tasks.md.

**7. After every task: CHANGELOG, version, README, CLAUDE.md** — all four in
English. Version: patch per task, minor when a Tasks.md milestone is done,
1.0.0 for the Store release. Procedure: /finish-task.

**8. Commit and push without asking.** After each task: commit and
`git push origin master`, no question. Solo project, so work happens directly
on `master`. Message: `<version>: <summary>` plus the co-author line the
environment asks for. Never `--force`, never rewrite pushed history — the
PreToolUse hook blocks both.

**9. Security is a top priority.** The app sees the screen and hears the
microphone. No network access at runtime and no telemetry — a new outbound
connection needs a decision recorded here. Capture starts only on an explicit
user action and is always visible. Recordings go only to the folder the user
chose; nothing is overwritten. No secrets, tokens or signing certificates
(`.pfx`) in the repo; Store signing stays outside it. Every new dependency
needs a reason. GitHub Actions are pinned by commit SHA with minimal
`permissions:`. `reviewer-security` reviews changes to capture, files,
dependencies, packaging and CI; the PreToolUse hook scans every commit for
secrets.

**10. Clean up after the push.** Delete what the task created that does not
belong in the repo — `build/`, `dist/`, test recordings, logs, scratch files —
by explicit path. Never `git clean`: it also deletes `.venv` and
`.claude/settings.local.json` (the hook blocks it). `git status` ends clean.

**11. GitHub Actions minutes are shared.** The owner has many repos that use
Actions. This repo is public, so standard GitHub-hosted runners cost nothing
here; larger runners always cost money and are not used. Private repos share
the account's included minutes, and a Windows minute costs more than a Linux
one (GitHub billing docs, checked 2026-11-19 — re-check before relying on
numbers). So: CI runs only when something can be checked (`paths-ignore` for
docs and `.claude/`), with `concurrency` + `cancel-in-progress` and
`timeout-minutes` on every job; one push per finished task; no blind re-runs —
read `gh run view --log-failed` first. Watching (`gh run watch`) is free. No CI
until tests exist (EKR-28).

**12. Autonomy.** Rely on yourself. Don't ask anyone and don't wait for answers.
Don't hand tasks to the owner. Do everything yourself. If something is unclear,
take the most reasonable option, record the decision and why in the decision
log below, and carry on.
Limits, because rule 9 outranks speed: no spending money, no deleting repos,
releases or branches, no force-push, no change of repo visibility and no Store
submission unless the owner asked for it in the current session. Steps only the
owner can take (account sign-up, legal acceptance, payment) are prepared up to
the last step and marked **Needs owner** in Tasks.md.

**13. Subagents, hooks and skills use the session's model and effort.**
- Every agent in `.claude/agents/` has `model: inherit` and no `effort` field;
  then it runs on the model and the effort chosen in the session (Claude Code
  docs, sub-agents page, checked 2026-11-19).
- Agent calls never pass `model` or `effort`.
- Built-ins pinned to their own model are denied: `claude-code-guide` (Haiku)
  and `statusline-setup` (Sonnet); `docs` replaces the first. The project's
  `Explore` replaces the built-in one; `Plan` and `general-purpose` inherit.
- Skills set no `model` or `effort` (that would switch the session's for the
  turn). Hooks are `type: "command"` only — prompt and agent hooks run on their
  own model.
- Never set `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_EFFORT`,
  `CLAUDE_CODE_EFFORT_LEVEL`, `ANTHROPIC_MODEL` or a `model` key in settings.

The deny rules and the hooks enforce this.

**14. Three languages: English, Russian, Armenian.** Every visible string is
translatable (`self.tr()`, `QCoreApplication.translate`), English being the
source; translations live in `translations/ekranik_ru.ts` and `ekranik_hy.ts` —
`hy` is Armenian (AM is the country). A change with new text translates it into
both (/i18n; the tests fail otherwise). The built `.qm` files are committed, so
a run from source has its languages. Language: saved choice → the first of
Windows' preferred languages Ekranik has → English. Use established Windows terms; don't
invent words.

**15. Follow the design; improve UI/UX.** Colors, spacing, radii and fonts come
only from the theme module (EKR-3); widgets hold no hard-coded colors or sizes.
Native Windows 11 look (Qt's `windows11` style), keyboard access, high DPI,
light and dark mode. When a task touches a screen, improve its UI/UX where
possible and say what changed in the CHANGELOG.

**16. Web goes to Cloudflare.** Ekranik is a desktop app. If it ever needs a
website (landing page, docs, a privacy policy page), it is hosted on Cloudflare
(Pages or Workers, domain through Cloudflare Registrar) — the owner's standard
for web projects.

## Claude Code setup (`.claude/`)

- **Skills:** `/start-task` (rules 1, 2, 5, 12), `/finish-task` (4–8, 10), `/i18n` (14).
- **Agents:** `Explore` (read-only search), `docs` (Claude Code, PySide6, uv,
  MSIX/Store and GitHub facts with sources), `reviewer` (one lens per run),
  `reviewer-security` (rule 9), `refuter` (tries to disprove each finding).
- **Hooks:** `.claude/hooks/guard.py` (wired in `.claude/settings.json`; after
  changing it, run the self-test). Session start: the rule 1 and 2 checks, next
  tasks, unfinished git work. Shell: blocks force-push, `git reset --hard`,
  `git clean`, pip, commits with secrets or certificates. Agents: blocks
  `model`/`effort` and pinned built-ins. After edits: ruff, UTF-8 without BOM,
  rule 13. Stop: asks to finish uncommitted or unpushed work.
- **Permissions:** `.claude/settings.json` holds only the deny rules; see the
  decision log.

## Decision log

One dated line each; durable decisions move into the rules above.

- 2026-11-19 — The backlog is `Tasks.md`, the owner's name (not FEATURE_TASKS.md).
- 2026-11-19 — Ruff with the `S` (rule 9) and `PERF` (rule 3) rules, default width.
- 2026-11-19 — The author's email stays public in pyproject.toml and commits.
- 2026-11-19 — "Ekranik" is a brand and is not translated (rule 14 exception).
  It is defined once, `ekranik.APP_NAME`; windows read it through
  `QGuiApplication.applicationDisplayName()`, which avoids an import cycle.
- 2026-11-19 — Tests run under the real app name (they test `main()`'s setup),
  so `tests/conftest.py` sends INI settings (user and system scope) and the
  recording folders to temp folders and turns on `QStandardPaths` test mode.
- 2026-11-19 — No app-wide stylesheet (rule 3): it doubled building and first
  painting 210 controls (34 → 67 ms). Text roles get font and palette from
  `theme.set_role()`; Ekranik's own widgets paint with theme colors (`ui/widgets.py`).
  Font pixels are computed at 96 per inch: `QFontInfo` cost 12–14 ms at start.
- 2026-11-19 — Settings use the GUI thread (rule 3 exception: the INI file
  reads in under 1 ms). A chosen value is always stored, even the default, so a
  chosen folder stays chosen (rule 9); unchosen defaults follow Windows. A
  network folder is allowed when the user names one: Windows connects, not Ekranik.
- 2026-11-19 — `.claude/settings.json` has no `allow` list or `defaultMode`:
  auto mode refused to let Claude grant itself permissions; the owner may add them.
- 2026-11-20 — Folders are picked with Windows' `IFileOpenDialog` via ctypes
  (`ui/folder_picker.py`), never `QFileDialog`: it writes the last folder to
  `HKCU\Software\QtProject`, shared by all Qt apps, with no switch (Qt 6.12).
- 2026-11-20 — The settings window applies changes at once; Cancel, Esc or
  closing restores the file's raw values (`Setting.raw`/`restore`), so unchosen
  stays unchosen. Pages appear with their first setting. Its code loads on first
  open: 7–10 ms off every start (rule 3).
- 2026-11-20 — An unchosen language walks Windows' preferred-language list, as
  Store apps do: `QLocale.system().uiLanguages()`, ~2 ms (ctypes: 12 ms, and
  only the display language). Translations load in the GUI thread (rule 3
  exception: under 1 ms, needed before the first window). Key
  `interface/language`: Qt's INI treats `[General]` specially.
