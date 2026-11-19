# CLAUDE.md — Ekranik

Ekranik is a Windows-only desktop app that records the screen and audio. It is
written in Python 3.15 with PySide6 (Qt for Python) and managed with uv.
Version 1.0 is the first release on the Microsoft Store, free of charge.
Repo: github.com/cholakhyanerik/ekranik — public, MIT, default branch
`master`, donations through GitHub Sponsors (`.github/FUNDING.yml`).

The rules below come from the owner (2026-11-19) and bind every change; the
numbers are the owner's, keep them. This file stays in English and under ~200
lines: procedures live in skills, this file keeps the rule and its reason.

**State on 2026-11-19:** `uv run ekranik` opens an empty main window
(`ekranik.main()` → `configure_app()` → `ui/main_window.py`). The owner reports
that the core features already exist; Tasks.md plans the road to 1.0 either way.

## Commands

| What | Command |
| --- | --- |
| Run the app | `uv run ekranik` |
| Install or refresh the environment, dev tools included | `uv sync` |
| Format and lint | `uv run ruff format .` · `uv run ruff check .` |
| Tests (from EKR-2) | `uv run pytest` |
| Outdated direct dependencies | `uv tree --outdated --depth 1` |
| Upgrade all locked versions | `uv lock --upgrade`, then `uv sync` |
| Bump the version | `uv version --bump patch` (or `minor`) |
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
translatable (`self.tr()`, `QCoreApplication.translate`); the source language
is English; translations live in `translations/ekranik_ru.ts` and
`translations/ekranik_hy.ts` — `hy` is Armenian (AM is the country). A change
with new text updates all three. Language: saved choice → Windows display
language → English. Use established Windows terminology; don't invent words.

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

- **Skills:** `/start-task` (rules 1, 2, 5, 12) and `/finish-task` (rules 4–8, 10).
- **Agents:** `Explore` (read-only search), `docs` (Claude Code, PySide6, uv,
  MSIX/Store and GitHub facts with sources), `reviewer` (one lens per run),
  `reviewer-security` (rule 9), `refuter` (tries to disprove each finding).
- **Hooks:** `.claude/hooks/guard.py`, wired in `.claude/settings.json`.
  Session start: Python vs system, outdated dependencies and tooling, next
  tasks, unfinished git work. Before a shell command: blocks force-push,
  `git reset --hard`, `git clean`, pip instead of uv, and commits with secrets
  or certificates. Before an agent call: blocks `model`/`effort` and the pinned
  built-ins. After an edit: ruff fix + format on `.py` files, UTF-8 without
  BOM, the rule 13 checks. After a shell command: the same file checks on
  changed files. On stop: asks to finish a task left uncommitted or unpushed.
  After changing guard.py, run the self-test.
- **Permissions:** `.claude/settings.json` holds only the deny rules; see the
  decision log.

## Decision log

One dated line each; durable decisions move into the rules above.

- 2026-11-19 — Rule 1 is about the Python version: system 3.15.2 = project 3.15.
- 2026-11-19 — The backlog file is `Tasks.md`, the owner's name for it (the
  owner's other projects use FEATURE_TASKS.md).
- 2026-11-19 — Armenian uses the code `hy` (ISO 639-1); "AM" is the country.
- 2026-11-19 — Ruff is the dev tool for format and lint, with the `S`
  (security) and `PERF` rules: rules 3 and 9 in code. Line length stays at
  ruff's default.
- 2026-11-19 — No CI yet, as there is nothing to test; EKR-28 adds it.
- 2026-11-19 — The author's email stays public in pyproject.toml and commits
  (owner's choice).
- 2026-11-19 — The version goes up after every task, tooling-only ones
  included: rule 7 says "always".
- 2026-11-19 — "Ekranik" is a brand and is not translated (rule 14 exception).
  It is defined once, `ekranik.APP_NAME`; windows read it through
  `QGuiApplication.applicationDisplayName()`, which avoids an import cycle.
- 2026-11-19 — `.claude/settings.json` has no `allow` list and no
  `defaultMode`: Claude Code's auto-mode safety check refused to let Claude
  grant itself permissions. The owner adds them if wanted.
