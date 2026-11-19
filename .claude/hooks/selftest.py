"""Self-test for guard.py: every guard gets a case where it must fire and a
neighbour that must pass. Failures are collected and printed at the end
instead of stopping at the first one.

    python -I .claude/hooks/selftest.py

CI does not run the hooks: run this by hand after changing guard.py, and see
a new check fail once first (break it on purpose, run, restore).
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
GUARD = HERE / "guard.py"
ROOT = HERE.parent.parent
FAILURES: list[str] = []

# Fake secrets are assembled at run time, so this file never contains one.
FAKE_GITHUB_TOKEN = "gh" + "p_" + "A1b2C3d4" * 5
AGENT = "---\nname: x\ndescription: test\n{extra}---\n\nBody.\n"
SKILL = "---\nname: s\ndescription: test\n{extra}---\n\nBody.\n"
BOARD = (
    "# Tasks\n\n| ID | Title | Type | Priority | Size | Milestone | Status |\n"
    "|---|---|---|---|---|---|---|\n"
    "| EKR-7 | Sample task | Story | High | S | M1 | To Do |\n"
    "| EKR-8 | Owner step | Task | High | XS | M6 | Needs owner |\n\n"
    "## EKR-7 · Sample task\n"
)


def run(mode: str, payload: dict, root: pathlib.Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), EKRANIK_GUARD_OFFLINE="1")
    return subprocess.run(
        [sys.executable, "-I", str(GUARD), mode],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=root,
        timeout=120,
        check=False,
    )


def expect(
    name: str, done: subprocess.CompletedProcess, code: int, needle: str = ""
) -> None:
    output = done.stdout + done.stderr
    if done.returncode != code or needle not in output:
        FAILURES.append(
            f"{name}: exit {done.returncode} (want {code}), "
            f"wanted {needle!r} in output: {output.strip()[:400]!r}"
        )


def new_repo() -> tuple[tempfile.TemporaryDirectory, pathlib.Path]:
    holder = tempfile.TemporaryDirectory()
    root = pathlib.Path(holder.name).resolve()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return holder, root


def shell(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_pre_shell() -> None:
    holder, root = new_repo()
    with holder:
        cases = [
            ("git push origin master", 0),
            ("git push --force origin master", 2),
            ("git push -f", 2),
            ("git push --force-with-lease", 2),
            ("git push origin +master", 2),
            ("git push origin --delete feature", 2),
            ("git -C repo push --force", 2),
            ("git status && git push --force", 2),
            ("git status\ngit push -f", 2),
            ('git commit -m "Block git push --force; really"', 0),
            ("git reset --soft HEAD~1", 0),
            ("git reset --hard HEAD~1", 2),
            ("git clean -fdx", 2),
            ("git clean -n", 0),
            ("pip install requests", 2),
            ("cd src; pip3 install requests", 2),
            ("python -m pip install requests", 2),
            ("python -m pip install -r requirements.txt", 2),
            ("uv pip install requests", 2),
            ("python -m pip install --upgrade uv", 0),
            ("py -3.15 -m pip install -U uv", 0),
            ("pip list --outdated", 0),
            ("uv add requests", 0),
            ("python -I .claude/hooks/selftest.py", 0),
        ]
        for command, code in cases:
            expect(
                f"pre-shell {command!r}", run("pre-shell", shell(command), root), code
            )


def test_commit_scan() -> None:
    holder, root = new_repo()
    with holder:
        (root / "app.py").write_text("print('clean')\n", encoding="utf-8")
        expect(
            "commit: clean tree", run("pre-shell", shell("git commit -m x"), root), 0
        )

        (root / "config.py").write_text(
            f'TOKEN = "{FAKE_GITHUB_TOKEN}"\n', encoding="utf-8"
        )
        done = run("pre-shell", shell("git add -A && git commit -m x"), root)
        expect(
            "commit: GitHub token", done, 2, "config.py:1: looks like a GitHub token"
        )
        if FAKE_GITHUB_TOKEN in done.stdout + done.stderr:
            FAILURES.append("commit: the report must not repeat the secret itself")
        (root / "config.py").unlink()

        (root / "signing").mkdir()
        (root / "signing" / "test.pfx").write_bytes(b"\x30\x82")
        expect(
            "commit: certificate file",
            run("pre-shell", shell("git commit -am x"), root),
            2,
            "signing/test.pfx: secret or certificate file",
        )
        (root / "signing" / "test.pfx").unlink()
        (root / ".env.example").write_text("KEY=\n", encoding="utf-8")
        expect(
            "commit: .env template", run("pre-shell", shell("git commit -m x"), root), 0
        )


def test_pre_agent() -> None:
    root = ROOT
    cases = [
        ({"subagent_type": "Explore", "prompt": "find"}, 0, ""),
        ({"subagent_type": "general-purpose", "prompt": "x"}, 0, ""),
        ({"subagent_type": "claude-code-guide"}, 2, "use the project's `docs` agent"),
        ({"subagent_type": "statusline-setup"}, 2, "Sonnet"),
        ({"subagent_type": "Explore", "model": "haiku"}, 2, "`model: haiku`"),
        ({"subagent_type": "Explore", "effort": "low"}, 2, "`effort: low`"),
    ]
    for tool_input, code, needle in cases:
        payload = {"tool_name": "Agent", "tool_input": tool_input}
        expect(f"pre-agent {tool_input}", run("pre-agent", payload, root), code, needle)
    expect("pre-agent other tool", run("pre-agent", {"tool_name": "Bash"}, root), 0)


def test_after_edit() -> None:
    holder, root = new_repo()
    with holder:

        def edited(rel: str, data: bytes, code: int, needle: str = "") -> None:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            payload = {"tool_name": "Write", "tool_input": {"file_path": str(path)}}
            expect(f"after-edit {rel}", run("after-edit", payload, root), code, needle)

        edited("notes.md", "Plain UTF-8 — ok.\n".encode(), 0)
        edited("bom.md", b"\xef\xbb\xbfText\n", 2, "UTF-8 BOM")
        edited("utf16.md", "Text\n".encode("utf-16"), 2, "UTF-16")
        edited("latin1.md", "caf\xe9\n".encode("latin-1"), 2, "not valid UTF-8")
        edited("image.png", b"\x89PNG\r\n\x1a\n\xff\xfe", 0)
        edited("mod.py", b"x = 1\n", 0)  # no pyproject.toml here: ruff is skipped

        agent = ".claude/agents/a.md"
        edited(agent, AGENT.format(extra="model: inherit\n").encode(), 0)
        edited(agent, AGENT.format(extra="").encode(), 2, "model: inherit")
        edited(agent, AGENT.format(extra="model: opus\n").encode(), 2, "model: inherit")
        edited(
            agent,
            AGENT.format(extra="model: inherit\neffort: max\n").encode(),
            2,
            "effort",
        )

        skill = ".claude/skills/s/SKILL.md"
        edited(skill, SKILL.format(extra="").encode(), 0)
        edited(
            skill,
            SKILL.format(extra="model: opus\n").encode(),
            2,
            "must not set `model`",
        )
        edited(
            skill,
            SKILL.format(extra="effort: high\n").encode(),
            2,
            "must not set `effort`",
        )
        fork = "context: fork\nmodel: inherit\n"
        edited(skill, SKILL.format(extra=fork).encode(), 0)

        settings = ".claude/settings.json"
        command = {"type": "command", "command": "python"}
        good = {"hooks": {"Stop": [{"hooks": [command]}]}}
        edited(settings, json.dumps(good).encode(), 0)
        edited(settings, b"{ not json", 2, "invalid JSON")
        env = {"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"}}
        edited(settings, json.dumps(env).encode(), 2, "CLAUDE_CODE_SUBAGENT_MODEL")
        edited(settings, json.dumps({"model": "opus"}).encode(), 2, "`model`")
        prompt = {"hooks": {"Stop": [{"hooks": [{"type": "prompt", "prompt": "x"}]}]}}
        edited(settings, json.dumps(prompt).encode(), 2, "type `prompt`")

        outside = {"tool_name": "Write", "tool_input": {"file_path": str(GUARD.parent)}}
        expect("after-edit outside the project", run("after-edit", outside, root), 0)


def test_after_shell() -> None:
    holder, root = new_repo()
    with holder:
        (root / "ok.md").write_text("fine\n", encoding="utf-8")
        expect("after-shell clean", run("after-shell", shell("echo"), root), 0)
        (root / "bad.md").write_bytes("Text\n".encode("utf-16"))
        expect(
            "after-shell UTF-16", run("after-shell", shell("echo"), root), 2, "bad.md"
        )


def test_stop() -> None:
    holder, root = new_repo()
    with holder:
        expect("stop: clean repo", run("stop", {}, root), 0)
        (root / "new.py").write_text("x = 1\n", encoding="utf-8")
        done = run("stop", {}, root)
        expect("stop: dirty repo", done, 0, '"decision": "block"')
        expect("stop: names the file", done, 0, "new.py")
        quiet = run("stop", {"stop_hook_active": True}, root)
        if quiet.stdout.strip():
            FAILURES.append("stop: must stay quiet when stop_hook_active is set")
        busy = run("stop", {"background_tasks": [{"id": "x"}]}, root)
        if busy.stdout.strip():
            FAILURES.append("stop: must stay quiet while background tasks run")


def test_session_start() -> None:
    holder, root = new_repo()
    with holder:
        current = "{}.{}".format(*sys.version_info[:2])
        (root / ".python-version").write_text(current + "\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "x"\nrequires-python = ">={current}"\n',
            encoding="utf-8",
        )
        (root / "Tasks.md").write_text(BOARD, encoding="utf-8")
        done = run("session-start", {"source": "startup"}, root)
        expect("session-start: Python matches", done, 0, "matches the project")
        expect("session-start: next task", done, 0, "EKR-7 Sample task")
        if "EKR-8" in done.stdout:
            FAILURES.append("session-start: tasks that need the owner are not 'next'")
        (root / ".python-version").write_text("3.0\n", encoding="utf-8")
        expect("session-start: mismatch", run("session-start", {}, root), 0, "differs")
        (root / "Tasks.md").unlink()
        expect(
            "session-start: no Tasks.md", run("session-start", {}, root), 0, "missing"
        )


def test_project_tree() -> None:
    expect("check-all on the project", run("check-all", {}, ROOT), 0, "no problems")


def main() -> int:
    for test in (
        test_pre_shell,
        test_commit_scan,
        test_pre_agent,
        test_after_edit,
        test_after_shell,
        test_stop,
        test_session_start,
        test_project_tree,
    ):
        test()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for failure in FAILURES:
            print(f"- {failure}")
        return 1
    print("selftest: all guards behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
