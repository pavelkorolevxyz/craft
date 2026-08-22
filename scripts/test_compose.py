#!/usr/bin/env python3
"""Проверяет безопасную композицию интерфейсных и слайдовых фрагментов."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from lib import ROOT, scaffold, run

COMPOSE = ROOT / "scripts/compose.py"
CHECK_PROJECT = ROOT / "scripts/check_project.py"


def command(project: Path, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(COMPOSE), str(project), *args], cwd=ROOT, text=True, capture_output=True)
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, "команда должна была завершиться ошибкой"
    return result


def test_interface(root: Path) -> None:
    project = root / "interface"
    scaffold(project, "interface", "blank", "Проверка композиции")
    index = project / "index.html"

    before = index.read_text(encoding="utf-8")
    preview = command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=<Заголовок>",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=<p>Содержимое</p>",
        "--dry-run",
    )
    assert "&lt;Заголовок&gt;" in preview.stdout and index.read_text(encoding="utf-8") == before

    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=<Заголовок>",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=<p>Содержимое</p>",
    )
    html = index.read_text(encoding="utf-8")
    assert 'id="alpha"' in html and "&lt;Заголовок&gt;" in html and "<p>Содержимое</p>" in html
    assert "{{" not in html

    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=Повтор",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=",
        success=False,
    )
    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=beta",
        "--set", "SECTION_TITLE=Неверный режим",
        "--set", "SECTION_SUMMARY=",
        "--set", "SECTION_CONTENT=<p>Нельзя</p>",
        success=False,
    )

    (project / "section-nav.js").unlink()
    command(
        project,
        "--fragment", "section-nav",
        "--set", "NAV_LABEL=Разделы",
        "--html", 'NAV_LINKS=<a href="#alpha">Первый</a>',
    )
    html = index.read_text(encoding="utf-8")
    assert (project / "section-nav.js").is_file()
    assert html.count('<script src="section-nav.js"></script>') == 1

    command(
        project,
        "--fragment", "tabs",
        "--set", "TABS_LABEL=Режимы",
        "--html", 'TAB_BUTTONS=<button type="button" role="tab" id="tab-a" aria-controls="panel-a">Первый</button>',
        "--html", 'TAB_PANELS=<div role="tabpanel" id="panel-a" aria-labelledby="tab-a">Содержимое</div>',
    )
    html = index.read_text(encoding="utf-8")
    assert (project / "tabs.js").is_file()
    assert html.count('<script src="tabs.js"></script>') == 1
    run(sys.executable, CHECK_PROJECT, project)


def test_slides(root: Path) -> None:
    project = root / "slides"
    scaffold(project, "slides", "deck", "Проверка композиции")
    listing = command(project, "--fragment", "list", "--list-placeholders")
    assert "SLIDE_TITLE: text" in listing.stdout and "LIST_ITEMS: html" in listing.stdout
    command(
        project,
        "--fragment", "list",
        "--set", "SLIDE_TITLE=Структура",
        "--html", "LIST_ITEMS=<li>Первый</li><li>Второй</li>",
    )
    html = project.joinpath("index.html").read_text(encoding="utf-8")
    assert html.count('<section class="slide') == 2 and 'data-slide-layout="list"' in html
    run(sys.executable, CHECK_PROJECT, project)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="craft-compose-") as directory:
        root = Path(directory)
        test_interface(root)
        test_slides(root)
    print("Готово: безопасная композиция фрагментов проверена")


if __name__ == "__main__":
    main()
