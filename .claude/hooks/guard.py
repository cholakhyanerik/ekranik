"""Claude Code hooks for Ekranik: guards for CLAUDE.md rules that ruff and the
tests cannot see.

Wired in .claude/settings.json; the mode is the first argument:

    session-start  SessionStart: system Python vs the project (rule 1), outdated
                   dependencies and tooling (rule 2), next tasks (rule 5) and
                   unfinished git work (rule 8)
    pre-shell      PreToolUse Bash|PowerShell: force-push and other history
                   loss, `git clean`, pip instead of uv, secrets or certificates
                   in a commit (rules 8, 9, 10)
    pre-agent      PreToolUse Agent: `model`/`effort` overrides and built-in
                   agents pinned to another model (rule 13)
    after-edit     PostToolUse Edit|Write: ruff on .py files (rules 3, 9),
                   UTF-8 without BOM, agent/skill/settings rules (rule 13)
    after-shell    PostToolUse Bash|PowerShell: the same file checks on every
                   changed file
    stop           Stop: asks to finish the task while work is uncommitted or
                   unpushed (rules 7, 8, 10)
    check-all      the file checks over the whole tree (by hand, selftest.py)

Exit code 2 sends stderr to Claude: before a tool call the call is blocked,
after it Claude is told what to fix. Standard library only, run as
`python -I`; the tests are in selftest.py.
"""

import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tomllib
import urllib.request

OFFLINE = "EKRANIK_GUARD_OFFLINE"  # set by selftest.py: skip network checks

TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".qss",
    ".toml",
    ".ts",
    ".txt",
    ".ui",
    ".xml",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {".gitattributes", ".gitignore", ".python-version", "LICENSE"}
BOM = b"\xef\xbb\xbf"
MAX_SCAN_BYTES = 2_000_000

# Built-in agents pinned to their own model (rule 13).
PINNED_AGENTS = {"claude-code-guide": "Haiku", "statusline-setup": "Sonnet"}
# Settings that would replace the model or effort chosen in the session.
FORBIDDEN_SETTINGS = {"model", "effortLevel"}
FORBIDDEN_ENV = {
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_SUBAGENT_EFFORT",
    "CLAUDE_CODE_SUBAGENT_MODEL",
}
AGENT_FILE = re.compile(r"^\.claude/agents/[^/]+\.md$")
SKILL_FILE = re.compile(r"^\.claude/skills/[^/]+/SKILL\.md$")
SETTINGS_FILE = re.compile(r"^\.claude/settings(\.local)?\.json$")

# Files that never go into git (rule 9); templates such as .env.example do.
SECRET_FILE = re.compile(
    r"(^|/)(\.env(\.[^/]+)?|id_(rsa|dsa|ecdsa|ed25519)"
    r"|[^/]+\.(pfx|p12|pem|key|jks|keystore))$",
    re.IGNORECASE,
)
TEMPLATE_SUFFIXES = (".example", ".sample", ".template")
# Secret shapes. Reports name the kind and the line, never the value.
SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    (
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"),
    ),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    (
        "hard-coded credential",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token"
            r"|auth[_-]?token)\b\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"
        ),
    ),
]

# Shell parsing: statements end at these runs of characters or at a newline.
SEPARATOR_CHARS = ";&|\n"
PREFIX_WORDS = {"command", "env", "exec", "nohup", "sudo", "time"}
GIT_VALUE_OPTIONS = {
    "-C",
    "-c",
    "--config-env",
    "--git-dir",
    "--namespace",
    "--work-tree",
}
PIP_VALUE_OPTIONS = {
    "-c",
    "--constraint",
    "-e",
    "--editable",
    "--extra-index-url",
    "-f",
    "--find-links",
    "-i",
    "--index-url",
    "-p",
    "--python",
    "-r",
    "--requirement",
    "-t",
    "--target",
}
OUTDATED = re.compile(r"([A-Za-z0-9_.-]+) v(\S+) .*?\(latest: v([^)\s]+)\)")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    handler = MODES.get(mode)
    if handler is None:
        print(
            f"guard.py: unknown mode {mode!r}; use one of: {', '.join(MODES)}",
            file=sys.stderr,
        )
        return 1
    payload = {} if mode == "check-all" else read_payload()
    return handler(payload, root_of(payload))


def read_payload() -> dict:
    raw = sys.stdin.buffer.read()
    try:
        data = json.loads(raw.decode("utf-8", errors="replace")) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def root_of(payload: dict) -> pathlib.Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    return pathlib.Path(raw).resolve()


def relative(root: pathlib.Path, path: pathlib.Path) -> str | None:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def run(
    args: list[str], root: pathlib.Path, timeout: float
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def git(root: pathlib.Path, *args: str) -> str | None:
    try:
        done = run(["git", *args], root, timeout=20)
    except OSError, subprocess.TimeoutExpired:
        return None
    return done.stdout if done.returncode == 0 else None


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def complain(head: str, problems: list[str]) -> int:
    if not problems:
        return 0
    print(head, file=sys.stderr)
    for problem in problems:
        print(f"- {problem}", file=sys.stderr)
    return 2


# --- session-start -----------------------------------------------------------


def session_start(payload: dict, root: pathlib.Path) -> int:
    lines = ["Ekranik session check (.claude/hooks/guard.py):", python_line(root)]
    if os.environ.get(OFFLINE):
        lines.append("- Dependencies (rule 2): not checked (offline).")
    else:
        lines += [dependencies_line(root), tooling_line(root)]
    lines += [tasks_line(root), git_line(root)]
    lines.append("Begin work with /start-task and close it with /finish-task.")
    print("\n".join(lines))
    return 0


def pyproject(root: pathlib.Path) -> dict:
    try:
        return tomllib.loads(read_text(root / "pyproject.toml"))
    except tomllib.TOMLDecodeError:
        return {}


def python_line(root: pathlib.Path) -> str:
    system = "{}.{}".format(*sys.version_info[:2])
    full = "{}.{}.{}".format(*sys.version_info[:3])
    pinned = ".".join(read_text(root / ".python-version").strip().split(".")[:2])
    spec = pyproject(root).get("project", {}).get("requires-python", "")
    lower = re.search(r">=\s*(\d+\.\d+)", spec)
    problems = []
    if not pinned:
        problems.append(".python-version is missing")
    elif pinned != system:
        problems.append(
            f"system Python {full} differs from the project's {pinned}: the project "
            "follows the system — update .python-version, requires-python and README now"
        )
    if lower and pinned and lower[1] != pinned:
        problems.append(
            f"requires-python {spec} does not match .python-version {pinned}"
        )
    if problems:
        return "- Python (rule 1): " + "; ".join(problems) + "."
    return f"- Python (rule 1): system {full} matches the project ({pinned})."


def dependencies_line(root: pathlib.Path) -> str:
    try:
        done = run(
            ["uv", "tree", "--outdated", "--depth", "1", "--frozen"], root, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"- Dependencies (rule 2): not checked ({exc.__class__.__name__})."
    if done.returncode != 0:
        last = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        return f"- Dependencies (rule 2): not checked (uv tree: {last[0]})."
    found = [
        f"{name} {old} → {new}" for name, old, new in OUTDATED.findall(done.stdout)
    ]
    if found:
        return (
            "- Dependencies (rule 2): updates available — "
            + ", ".join(found)
            + ". Update and adapt before the task (/start-task)."
        )
    return "- Dependencies (rule 2): all direct dependencies are current."


def pypi_latest(name: str) -> str | None:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.load(response)["info"]["version"]
    except OSError, ValueError, KeyError:
        return None


def version_key(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def tooling_line(root: pathlib.Path) -> str:
    try:
        words = run(["uv", "--version"], root, timeout=10).stdout.split()
    except OSError, subprocess.TimeoutExpired:
        words = []
    current = words[1] if len(words) > 1 else ""
    latest_uv, latest_build = pypi_latest("uv"), pypi_latest("uv-build")
    if not current or latest_uv is None or latest_build is None:
        return "- Tooling (rule 2): uv not checked (uv or PyPI unreachable)."
    notes = []
    if version_key(latest_uv) > version_key(current):
        notes.append(
            f"uv {current} → {latest_uv}: `python -m pip install --upgrade uv`"
        )
    requires = " ".join(pyproject(root).get("build-system", {}).get("requires", []))
    bound = re.search(r"uv_build\s*>=\s*([\d.]+)\s*,\s*<\s*([\d.]+)", requires)
    if bound and version_key(latest_build) >= version_key(bound[2]):
        notes.append(
            f"uv_build {latest_build} is outside >={bound[1]},<{bound[2]} — "
            "move the bound in [build-system]"
        )
    if notes:
        return "- Tooling (rule 2): " + "; ".join(notes) + "."
    return f"- Tooling (rule 2): uv {current} and the uv_build bound are current."


def board_rows(text: str) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            if rows:
                break  # the board table ended
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            if cells and cells[0].lower() == "id":
                header = [cell.lower() for cell in cells]
        elif not set("".join(cells)) <= set("-: "):
            rows.append(dict(zip(header, cells, strict=False)))
    return rows


def tasks_line(root: pathlib.Path) -> str:
    text = read_text(root / "Tasks.md")
    if not text:
        return (
            "- Tasks (rule 5): Tasks.md is missing — create it with the tasks for 1.0."
        )
    rows = [row for row in board_rows(text) if row.get("status", "").lower() == "to do"]
    if not rows:
        return "- Tasks (rule 5): the Tasks.md board has no To Do rows — plan the next tasks."
    head = "; ".join(f"{row.get('id', '?')} {row.get('title', '')}" for row in rows[:3])
    return f"- Tasks (rule 5): next — {head}."


def changed_files(root: pathlib.Path) -> list[str] | None:
    out = git(root, "status", "--porcelain", "-z", "--untracked-files=all")
    if out is None:
        return None
    names, entries, i = [], out.split("\0"), 0
    while i < len(entries):
        entry, i = entries[i], i + 1
        if len(entry) > 3:
            names.append(entry[3:])
            if entry[0] in "RC":
                i += 1  # a rename or copy is followed by the original path
    return names


def unpushed_count(root: pathlib.Path) -> int:
    out = (git(root, "rev-list", "--count", "@{upstream}..HEAD") or "").strip()
    return int(out) if out.isdigit() else 0


def git_line(root: pathlib.Path) -> str:
    changed = changed_files(root)
    if changed is None:
        return "- Git: not a git repository."
    unpushed = unpushed_count(root)
    parts = []
    if changed:
        parts.append(f"{len(changed)} uncommitted file(s)")
    if unpushed:
        parts.append(f"{unpushed} unpushed commit(s)")
    if not parts:
        return "- Git: clean, nothing unpushed."
    return (
        "- Git (rule 8): "
        + ", ".join(parts)
        + " — if it is unfinished work of a task, finish it first."
    )


# --- pre-shell ---------------------------------------------------------------


def segments(command: str) -> list[list[str]]:
    """Split a shell command into statements of words; quotes stay intact."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=SEPARATOR_CHARS)
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes: fall back to a rough split
        tokens = re.findall(r"[;&|\n]+|[^\s;&|]+", command)
    statements, current = [], []
    for token in tokens:
        if token and set(token) <= set(SEPARATOR_CHARS):
            if current:
                statements.append(current)
            current = []
        else:
            current.append(token)
    if current:
        statements.append(current)
    return statements


def program(word: str) -> str:
    name = pathlib.PureWindowsPath(word).name.lower()
    return name.removesuffix(".exe")


def pre_shell(payload: dict, root: pathlib.Path) -> int:
    command = (payload.get("tool_input") or {}).get("command") or ""
    problems = []
    for words in segments(command):
        problems += statement_problems(words, root)
    return complain("Blocked by .claude/hooks/guard.py (CLAUDE.md):", problems)


def statement_problems(words: list[str], root: pathlib.Path) -> list[str]:
    while words and (re.fullmatch(r"\w+=.*", words[0]) or words[0] in PREFIX_WORDS):
        words = words[1:]
    if not words:
        return []
    exe, args = program(words[0]), words[1:]
    if exe == "git":
        return git_problems(args, root)
    if exe in {"pip", "pip3"}:
        return pip_problems(args, via_uv=False)
    if exe in {"python", "python3", "py"}:
        pip_args = module_args(args, "pip")
        return [] if pip_args is None else pip_problems(pip_args, via_uv=False)
    if exe == "uv" and args[:1] == ["pip"]:
        return pip_problems(args[1:], via_uv=True)
    return []


def module_args(args: list[str], module: str) -> list[str] | None:
    for i, word in enumerate(args):
        if word == "-m":
            return args[i + 2 :] if args[i + 1 : i + 2] == [module] else None
        if not word.startswith("-"):
            return None  # a script, not `-m`
    return None


def pip_problems(args: list[str], via_uv: bool) -> list[str]:
    command, targets, i = None, [], 0
    while i < len(args):
        word = args[i]
        if word in PIP_VALUE_OPTIONS:
            if command:
                targets.append(word)  # a requirements file is never "just uv"
            i += 2
            continue
        if not word.startswith("-"):
            if command is None:
                command = word
            else:
                targets.append(word)
        i += 1
    if command not in {"install", "uninstall"}:
        return []
    names = {re.split(r"[<>=!~\[;@ ]", word, maxsplit=1)[0].lower() for word in targets}
    if command == "install" and not via_uv and names == {"uv"}:
        return []  # uv itself was installed with pip into the system Python
    return [
        (
            "uv is required: use `uv add`, `uv remove` or `uv sync` instead of pip; "
            "only uv itself is updated with `python -m pip install --upgrade uv`."
        )
    ]


def git_problems(args: list[str], root: pathlib.Path) -> list[str]:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_VALUE_OPTIONS else 1
    if i >= len(args):
        return []
    sub, rest = args[i], args[i + 1 :]
    if sub == "push":
        return push_problems(rest)
    if sub == "reset" and "--hard" in rest:
        return [
            (
                "`git reset --hard` throws away uncommitted work — undo the specific "
                "changes instead (rule 9)."
            )
        ]
    if sub == "clean" and not any(
        word == "--dry-run" or re.fullmatch(r"-[A-Za-z]*n[A-Za-z]*", word)
        for word in rest
    ):
        return [
            (
                "`git clean` also deletes .venv and .claude/settings.local.json — "
                "delete temporary files by path (rule 10)."
            )
        ]
    if sub == "commit":
        return commit_problems(root)
    return []


def push_problems(rest: list[str]) -> list[str]:
    for word in rest:
        if (
            word.startswith("--force")
            or word in {"--mirror", "--delete", "--prune"}
            or re.fullmatch(r"-[A-Za-z]*[fd][A-Za-z]*", word)
        ):
            return [
                f"`git push {word}` rewrites or deletes history on GitHub — push normally."
            ]
        if word.startswith(("+", ":")):
            return [
                f"refspec `{word}` force-pushes or deletes a branch — push normally."
            ]
    return []


def commit_candidates(root: pathlib.Path) -> list[str]:
    """Everything a `git add -A && git commit` could include."""
    names: set[str] = set()
    for args in (
        ("diff", "--cached", "--name-only", "-z"),
        ("diff", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        names.update(name for name in (git(root, *args) or "").split("\0") if name)
    return sorted(names)


def commit_problems(root: pathlib.Path) -> list[str]:
    problems = []
    for name in commit_candidates(root):
        if SECRET_FILE.search(name) and not name.lower().endswith(TEMPLATE_SUFFIXES):
            problems.append(
                f"{name}: secret or certificate file — keep it out of git (rule 9)"
            )
            continue
        path = root / name
        try:
            if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_bytes().decode("utf-8")
        except OSError, UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            kinds = [kind for kind, pattern in SECRET_PATTERNS if pattern.search(line)]
            if kinds:
                problems.append(
                    f"{name}:{number}: looks like a {kinds[0]} — remove it "
                    "(and revoke it if it is real) (rule 9)"
                )
    return problems


# --- pre-agent ---------------------------------------------------------------


def pre_agent(payload: dict, root: pathlib.Path) -> int:
    if payload.get("tool_name") not in {"Agent", "Task"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    problems = [
        f"`{key}: {tool_input[key]}` overrides the session's {key} — leave it out"
        for key in ("model", "effort")
        if tool_input.get(key)
    ]
    kind = tool_input.get("subagent_type") or ""
    if kind in PINNED_AGENTS:
        instead = (
            " — use the project's `docs` agent" if kind == "claude-code-guide" else ""
        )
        problems.append(
            f"built-in `{kind}` always runs on {PINNED_AGENTS[kind]}{instead}"
        )
    return complain(
        "Rule 13: subagents run on the model and effort chosen in this session.",
        problems,
    )


# --- file checks (after-edit, after-shell, check-all) ------------------------


def is_text(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (
        name in TEXT_NAMES
        or pathlib.PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES
    )


def file_problems(rel: str, data: bytes) -> list[str]:
    if not is_text(rel):
        return []
    if data.startswith(BOM):
        return ["starts with a UTF-8 BOM — save it as UTF-8 without BOM"]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return [
            "is UTF-16 (PowerShell 5.1 `>` writes that) — save it as UTF-8 without BOM"
        ]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"is not valid UTF-8 (byte {exc.start}) — save it as UTF-8 without BOM"]
    if AGENT_FILE.match(rel):
        return agent_problems(text)
    if SKILL_FILE.match(rel):
        return skill_problems(text)
    if SETTINGS_FILE.match(rel):
        return settings_problems(text)
    return []


def frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"([A-Za-z][\w-]*)\s*:\s*(.*)$", line)
        if match:
            fields[match[1]] = match[2].strip().strip("\"'")
    return None


def agent_problems(text: str) -> list[str]:
    fields = frontmatter(text)
    if fields is None:
        return ["an agent needs YAML frontmatter between --- lines"]
    problems = []
    if fields.get("model") != "inherit":
        problems.append(
            "an agent needs `model: inherit` — the session's model (rule 13)"
        )
    if "effort" in fields:
        problems.append(
            "an agent must not set `effort` — it then runs at the session's (rule 13)"
        )
    return problems


def skill_problems(text: str) -> list[str]:
    fields = frontmatter(text) or {}
    problems = []
    if "effort" in fields:
        problems.append(
            "a skill must not set `effort` — it changes the session's (rule 13)"
        )
    model = fields.get("model")
    if model is not None and not (
        model == "inherit" and fields.get("context") == "fork"
    ):
        problems.append(
            "a skill must not set `model` (only `model: inherit` with `context: fork`) (rule 13)"
        )
    return problems


def settings_problems(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}: {exc.msg}"]
    if not isinstance(data, dict):
        return ["settings must be a JSON object"]
    problems = [
        f"`{key}` would replace the session's model or effort (rule 13)"
        for key in sorted(FORBIDDEN_SETTINGS & data.keys())
    ]
    env = data.get("env")
    if isinstance(env, dict):
        problems += [
            f"env `{key}` would replace the session's model or effort (rule 13)"
            for key in sorted(FORBIDDEN_ENV & env.keys())
        ]
    hooks = data.get("hooks")
    for event, groups in (hooks if isinstance(hooks, dict) else {}).items():
        for group in groups if isinstance(groups, list) else []:
            handlers = group.get("hooks", []) if isinstance(group, dict) else []
            for handler in handlers if isinstance(handlers, list) else []:
                kind = handler.get("type") if isinstance(handler, dict) else None
                if kind != "command":
                    problems.append(
                        f'{event} hook of type `{kind}` — only `"command"` hooks: '
                        "prompt and agent hooks run on their own model (rule 13)"
                    )
    return problems


def ruff_problems(root: pathlib.Path, rel: str) -> list[str]:
    if not (root / "pyproject.toml").is_file():
        return []
    ruff = ["uv", "run", "--frozen", "--quiet", "ruff"]
    try:
        fixed = run([*ruff, "check", "--fix", "--quiet", rel], root, timeout=60)
        run([*ruff, "format", "--quiet", rel], root, timeout=60)
        if fixed.returncode == 0:
            return []
        # Re-check after formatting so the reported line numbers are current.
        done = run(
            [*ruff, "check", "--quiet", "--output-format", "concise", rel], root, 60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [
            f"ruff did not run ({exc.__class__.__name__}) — run `uv run ruff check {rel}`"
        ]
    if done.returncode == 0:
        return []
    lines = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return lines[:20] or ["ruff check failed without output"]


def after_edit(payload: dict, root: pathlib.Path) -> int:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    path = pathlib.Path(raw)
    path = path if path.is_absolute() else root / path
    rel = relative(root, path)
    if rel is None or rel.startswith(".venv/") or not path.is_file():
        return 0
    problems = file_problems(rel, path.read_bytes())
    if rel.endswith(".py") and not problems:
        problems = ruff_problems(root, rel)
    return complain(f"{rel} needs a fix (.claude/hooks/guard.py):", problems)


def tree_problems(root: pathlib.Path, names: list[str]) -> list[str]:
    problems = []
    for name in names:
        path = root / name
        try:
            if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        problems += [f"{name}: {problem}" for problem in file_problems(name, data)]
    return problems


def after_shell(payload: dict, root: pathlib.Path) -> int:
    problems = tree_problems(root, changed_files(root) or [])
    return complain("Changed files need a fix (.claude/hooks/guard.py):", problems)


def check_all(payload: dict, root: pathlib.Path) -> int:
    out = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if out is None:
        print("check-all: not a git repository", file=sys.stderr)
        return 1
    problems = tree_problems(root, sorted({name for name in out.split("\0") if name}))
    if not problems:
        print("check-all: no problems")
    return complain("check-all found problems:", problems)


# --- stop --------------------------------------------------------------------


def stop(payload: dict, root: pathlib.Path) -> int:
    if payload.get("stop_hook_active") or payload.get("background_tasks"):
        return 0
    changed = changed_files(root) or []
    unpushed = unpushed_count(root)
    if not changed and not unpushed:
        return 0
    parts = []
    if changed:
        more = "…" if len(changed) > 8 else ""
        parts.append(
            f"{len(changed)} uncommitted file(s): {', '.join(changed[:8])}{more}"
        )
    if unpushed:
        parts.append(f"{unpushed} unpushed commit(s)")
    reason = (
        "Unfinished work: "
        + "; ".join(parts)
        + ". If this is the task you just did, finish it now with /finish-task — Tasks.md, "
        "CHANGELOG, version, README, CLAUDE.md, commit, push, cleanup (rules 7, 8, 10). "
        "If these changes are not yours (for example the owner's own edits), leave them "
        "and say so."
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


MODES = {
    "session-start": session_start,
    "pre-shell": pre_shell,
    "pre-agent": pre_agent,
    "after-edit": after_edit,
    "after-shell": after_shell,
    "stop": stop,
    "check-all": check_all,
}

if __name__ == "__main__":
    sys.exit(main())
