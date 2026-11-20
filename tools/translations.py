"""Update and build Ekranik's translations (CLAUDE.md, rule 14; the /i18n skill).

    uv run tools/translations.py           # .ts files from the code, then .qm files
    uv run tools/translations.py --check   # changes nothing; fails if anything is stale

The ``.ts`` files in ``translations/`` are the sources the translations are
written in; lupdate adds the code's new texts to them and drops the removed
ones. The ``.qm`` files in ``src/ekranik/translations/`` are what the app loads;
they are committed, so Ekranik run from source has its languages. Only finished
translations are built: an unfinished one, such as lupdate's guess for a changed
text, stays English until a translator confirms it.

``--check`` (run by the tests) fails when a ``.ts`` file misses a text of the
code, a ``.qm`` file is older than its ``.ts`` file, or a text has no finished
translation.
"""

import argparse
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ekranik.i18n import SOURCE
from ekranik.settings import Language

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "src" / "ekranik"
SOURCES = ROOT / "translations"
"""The ``.ts`` files, one per translated language."""
BUILT = CODE / "translations"
"""The ``.qm`` files the app loads (``ekranik.i18n.FOLDER``)."""

LANGUAGES = tuple(
    language for language in Language if language not in {Language.SYSTEM, SOURCE}
)


def ts_file(language: Language, folder: Path = SOURCES) -> Path:
    return folder / f"ekranik_{language}.ts"


def qm_file(language: Language, folder: Path = BUILT) -> Path:
    return folder / f"ekranik_{language}.qm"


def run(tool: str, *arguments: str | Path) -> None:
    """Run one of Qt's tools from this environment; its messages go to stderr."""
    executable = Path(sysconfig.get_path("scripts")) / f"{tool}.exe"
    done = subprocess.run(
        [executable, *map(str, arguments)], capture_output=True, text=True, check=False
    )
    if done.returncode:
        sys.exit(f"{tool} failed:\n{done.stdout}{done.stderr}")


def update(ts_files: list[Path]) -> None:
    """Bring the ``.ts`` files in step with the texts in the code.

    ``-extensions py`` must come before the folder, or lupdate finds no texts.
    No line numbers and no removed texts, so the files change only with the texts.
    """
    run(
        "pyside6-lupdate",
        "-silent",
        "-extensions",
        "py",
        CODE,
        "-locations",
        "none",
        "-no-obsolete",
        "-source-language",
        SOURCE.value,
        "-ts",
        *ts_files,
    )


def release(ts: Path, qm: Path) -> None:
    """Build a ``.qm`` file from the finished translations of a ``.ts`` file."""
    run("pyside6-lrelease", "-silent", "-nounfinished", ts, "-qm", qm)


def untranslated(ts: Path) -> list[str]:
    """The texts of a ``.ts`` file without a finished translation, as context: text."""
    # Ekranik's own file, written by lupdate: not untrusted input.
    tree = ET.parse(ts)  # noqa: S314
    return [
        f"{context.findtext('name')}: {message.findtext('source')}"
        for context in tree.iterfind("context")
        for message in context.iterfind("message")
        if (translation := message.find("translation")) is None
        or translation.get("type") is not None
        or not "".join(translation.itertext()).strip()
    ]


def check() -> list[str]:
    """What is stale or untranslated; empty when the translations are current."""
    problems = [
        f"{ts_file(language).name} is missing"
        for language in LANGUAGES
        if not ts_file(language).is_file()
    ]
    if problems:
        return problems
    with tempfile.TemporaryDirectory() as scratch:
        folder = Path(scratch)
        copies = [
            Path(shutil.copy(ts_file(language), ts_file(language, folder)))
            for language in LANGUAGES
        ]
        update(copies)
        for language, copy in zip(LANGUAGES, copies, strict=True):
            ts = ts_file(language)
            if copy.read_text(encoding="utf-8") != ts.read_text(encoding="utf-8"):
                problems.append(f"{ts.name} misses changes of the code's texts")
            release(ts, qm_file(language, folder))
            qm = qm_file(language)
            if not qm.is_file() or (
                qm_file(language, folder).read_bytes() != qm.read_bytes()
            ):
                problems.append(f"{qm.name} is not built from {ts.name}")
            problems.extend(
                f"{ts.name} has no finished translation of {text}"
                for text in untranslated(ts)
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="change nothing; report what is stale"
    )
    if parser.parse_args().check:
        problems = check()
        for problem in problems:
            print(problem, file=sys.stderr)
        if problems:
            print("Run: uv run tools/translations.py", file=sys.stderr)
        return 1 if problems else 0
    update([ts_file(language) for language in LANGUAGES])
    BUILT.mkdir(exist_ok=True)
    for language in LANGUAGES:
        release(ts_file(language), qm_file(language))
    for language in LANGUAGES:
        for text in untranslated(ts_file(language)):
            print(f"{ts_file(language).name}: untranslated: {text}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
