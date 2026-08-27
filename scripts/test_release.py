#!/usr/bin/env python3
"""Проверяет релизные архивы и команды из распакованного пакета Craft."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from lib import ROOT, chromium_args

FORBIDDEN_PARTS = {"tests", "docs", "examples", "output", "artifacts"}
RUNTIME_SCRIPTS = {"lib.py", "scaffold.py", "compose.py", "check_project.py"}
INTERFACE_DOCS = {"index.html", "sheet.html", "getting-started.html", "foundations.html", "atoms.html", "molecules.html", "organisms.html", "templates.html", "pages.html"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def execute(root: Path, *arguments: str | Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(argument) for argument in arguments],
        cwd=root,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"команда не прошла: {' '.join(map(str, arguments))}\n{result.stdout}\n{result.stderr}"
    return result


def check_entries(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts, f"небезопасный путь в {archive.name}: {name}"
            relative = path.parts[1:]
            assert not (FORBIDDEN_PARTS & set(relative)), f"запрещённый путь в {archive.name}: {name}"
            assert "specimen" not in path.name and not path.name.startswith("test_"), f"тестовый файл в {archive.name}: {name}"
        return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    dist = args.dist.expanduser().resolve()
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["packages"]
    assert set(expected) == {"craft-interface", "craft-slides", "craft-complete"}

    for package, metadata in expected.items():
        archive = dist / metadata["file"]
        names = check_entries(archive)
        assert archive.stat().st_size == metadata["bytes"]
        assert digest(archive) == metadata["sha256"]
        assert len(names) == metadata["entries"]
        interface_docs = {f"catalog/interfaces/{name}" for name in INTERFACE_DOCS}
        expected_catalogs = {
            "craft-interface": interface_docs,
            "craft-slides": {"catalog/slides/index.html", "catalog/slides/case-study.html"},
            "craft-complete": interface_docs | {"catalog/slides/index.html", "catalog/slides/case-study.html"},
        }[package]
        relative_names = {"/".join(PurePosixPath(name).parts[1:]) for name in names}
        assert expected_catalogs <= relative_names, f"{package}: не включён публичный каталог"

    with tempfile.TemporaryDirectory(prefix="craft-release-") as directory:
        temporary = Path(directory)
        for package, surface in (("craft-interface", "interfaces"), ("craft-slides", "slides")):
            archive = dist / expected[package]["file"]
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(temporary)
            package_root = temporary / package
            execute(ROOT, sys.executable, ROOT / "scripts/check_project.py", package_root / f"catalog/{surface}", "--static-only", "--resource-root", package_root)

        complete = dist / expected["craft-complete"]["file"]
        with zipfile.ZipFile(complete) as package:
            package.extractall(temporary)
        root = temporary / "craft-complete"
        scripts = root / "scripts"
        assert {path.name for path in scripts.glob("*.py")} == RUNTIME_SCRIPTS
        execute(root, sys.executable, scripts / "check_project.py", root / "catalog/interfaces", "--resource-root", root)
        execute(root, sys.executable, scripts / "check_project.py", root / "catalog/slides", "--resource-root", root)
        for page in ("index.html", "atoms.html", "organisms.html", "pages.html"):
            source = root / "catalog/interfaces" / page
            dumped = execute(root, *chromium_args(390 if page == "atoms.html" else 1440, 900), "--dump-dom", source.as_uri()).stdout
            assert "<main" in dumped and "Craft" in dumped, f"{page}: документация не открывается из архива"
            if page != "index.html":
                assert "data-preview-code=\"\"" in dumped and "&lt;" in dumped, f"{page}: код примера не создан из архива"

        interface = temporary / "interface-project"
        execute(root, sys.executable, scripts / "scaffold.py", interface, "--surface", "interface", "--title", "Проверка релиза")
        execute(
            root,
            sys.executable,
            scripts / "compose.py",
            interface,
            "--fragment", "section",
            "--set", "SECTION_ID=release-section",
            "--set", "SECTION_TITLE=Раздел",
            "--set", "SECTION_SUMMARY=",
            "--html", "SECTION_CONTENT=<p>Проверка</p>",
        )
        execute(root, sys.executable, scripts / "check_project.py", interface)

        slides = temporary / "slides-project"
        execute(root, sys.executable, scripts / "scaffold.py", slides, "--surface", "slides", "--title", "Проверка релиза")
        execute(
            root,
            sys.executable,
            scripts / "compose.py",
            slides,
            "--fragment", "statement",
            "--set", "STATEMENT=Главный тезис",
            "--set", "QUALIFIER=Уточнение",
        )
        execute(root, sys.executable, scripts / "check_project.py", slides)

    print("Готово: архивы безопасны, а распакованный Craft автономно создаёт, компонует и проверяет проекты")


if __name__ == "__main__":
    main()
