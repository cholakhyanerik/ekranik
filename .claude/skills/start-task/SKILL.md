---
name: start-task
description: Start an Ekranik task — check the system Python and the dependencies first (CLAUDE.md rules 1 and 2), pick the task from Tasks.md, read it and plan the checks. Use at the start of any piece of work, whether the user names a task ("EKR-12"), asks for "the next task" or brings new work.
argument-hint: "[task ID such as EKR-12, or a short description of new work]"
---

# Start a task

Task: $ARGUMENTS

## 1. Python and dependencies first (rules 1, 2)

The SessionStart hook already printed both checks; run them again if the
session has been open for a long time.

1. **Python.** The system Python (`python --version`, the one on PATH) and
   `.python-version` must match in major.minor. The system is newer → the
   project follows now: `.python-version`, `requires-python` in
   pyproject.toml, every "3.15" in README.md (badge and text), then
   `uv sync`, `uv run ruff check .` and the tests. New `UP` findings are fixed
   in the code, not silenced.
2. **Packages.** `uv tree --outdated --depth 1`. Updates →
   `uv lock --upgrade`, `uv sync`, all checks. Something broke → adapt the
   code instead of pinning the old version; check the new API in
   `.venv/Lib/site-packages/` (PySide6 ships `.pyi` stubs), not from memory.
   A notable adaptation gets a line in CLAUDE.md and in the CHANGELOG.
3. **Tooling.** A newer uv on PyPI → `python -m pip install --upgrade uv`
   (uv was installed with pip into the system Python). Keep the
   `uv_build>=X,<Y` bound in `[build-system]` on uv's current minor version.

The updates go into this task's commit and CHANGELOG entry.

## 2. The task (rules 5, 12)

1. An ID in the arguments → that task. No ID → the first **To Do** row of the
   Tasks.md board. Don't ask (rule 12).
2. New work that is not in Tasks.md → add it first, split into the smallest
   useful tasks, then take the first of them.
3. Read the whole entry, from `### EKR-n` to the next `### `. Stale facts in it
   (moved files, changed approach) → correct the entry.
4. Set its status on the board to **In Progress**.

## 3. Before the code

- Re-read the rules the task touches: 3 (performance), 4 (compatibility),
  9 (security), 14 (languages), 15 (design).
- Unclear how something works → the `Explore` agent (read-only; several can run
  in parallel). Library or tool facts → the `docs` agent.
- Plan the checks: which test proves it (see it fail first), what to look at
  in the running app, what must keep working (rule 4).
- A decision to make → take the most reasonable option and write it in the
  CLAUDE.md decision log with the reason (rule 12). No questions.

Then write the code, and close the task with /finish-task.
