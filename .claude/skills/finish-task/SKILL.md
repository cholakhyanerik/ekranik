---
name: finish-task
description: Finish an Ekranik task in order — checks, review, Tasks.md, version, CHANGELOG, README, CLAUDE.md, commit and push without asking, cleanup (CLAUDE.md rules 4–8 and 10). Use as soon as the code of a task is done.
---

# Finish a task

The steps run in this order; each relies on the one before.

## 1. The code works

1. **Checks**, one after another:
   `uv run ruff format --check .` · `uv run ruff check .` · `uv run pytest`
   (once tests exist, EKR-2) · `python -I .claude/hooks/selftest.py` (when
   `.claude/hooks/` changed). A failure → fix it. Cannot fix it → say so
   plainly, with the output.
2. **Nothing old broke (rule 4).** The tests cover it; whatever they don't
   cover gets a manual run of the affected mode, named in the report.
3. **Review** anything beyond a trivial change: `reviewer` agents in parallel,
   one per relevant lens; `reviewer-security` for capture, files, settings,
   subprocesses, network, dependencies, packaging, CI or `.claude/`. Every
   finding goes to `refuter`; fix what is confirmed.
4. **Bugs found on the way** are fixed here, each with a test (rule 6).

## 2. Bookkeeping, all in English (rules 5, 7)

5. **Tasks.md** — delete the finished task (entry and board row); add the new
   tasks and improvements found on the way, split small; correct stale facts
   in other entries; keep the board sorted by priority.
6. **Version** — `uv version --bump patch`; `--bump minor` when this task
   completes a milestone (its last task leaves the board); 1.0.0 is the
   Microsoft Store release. It updates pyproject.toml and uv.lock.
7. **CHANGELOG.md** — a new entry on top, `## <version> — <YYYY-MM-DD>`, with
   `Added`, `Changed`, `Fixed`, `Security` as needed, in words a user
   understands, with the reason.
8. **README.md** — everything a user sees: features, install, usage,
   requirements. The Roadmap keeps pointing to Tasks.md.
9. **CLAUDE.md** — what the next session would stumble on, briefly, with the
   reason; decisions taken without asking go to the decision log. Stay under
   ~200 lines: procedures belong in skills.

## 3. Commit, push, clean up (rules 8, 10)

10. **Before staging**, delete temporary files inside the repo (test
    recordings, logs, scratch files): `git add -A` would commit them.
11. **Commit and push without asking**: `git add -A`, `git commit` with
    `<version>: <summary of the new CHANGELOG entry>` and the co-author line
    the environment asks for, then `git push origin master`. Never `--force`,
    never rewrite pushed history. The PreToolUse hook scans the commit for
    secrets and certificates.
12. **CI** (once a workflow exists): find the run of this commit
    (`gh run list --commit <sha> --limit 1`), then
    `gh run watch <id> --exit-status` — watching costs no minutes. Red → read
    `gh run view <id> --log-failed`, fix, push once; no blind re-runs (rule 11).
13. **After the push**, delete what is left: ignored build output (`build/`,
    `dist/`) and scratch files outside the repo — by explicit path, never
    `git clean`. `git status` shows nothing.
14. **Report**: what was done; bugs fixed on the way; the new version; Tasks.md
    changes (removed, added); decisions taken; anything that failed, plainly.
