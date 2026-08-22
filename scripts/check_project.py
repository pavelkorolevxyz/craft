#!/usr/bin/env python3
"""Проверяет автономный интерфейс или слайдовую колоду, созданные с Craft."""

from __future__ import annotations

import argparse
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lib import chromium_args, run

PLACEHOLDER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
REMOTE_SCHEMES = {"http", "https"}
VIEWPORTS = ((1440, 900), (390, 844), (320, 720))


class ProjectParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []
        self.h1_count = 0
        self.interface = False
        self.slides = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if values.get("data-craft-layout") == "interface":
            self.interface = True
        if tag == "section" and "slide" in (values.get("class") or "").split():
            self.slides = True
        if tag == "link" and values.get("href"):
            self.assets.append(values["href"] or "")
        if tag in {"script", "img", "source", "video"} and values.get("src"):
            self.assets.append(values["src"] or "")


def project_index(path: Path) -> Path:
    target = path.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    assert index.is_file(), f"не найден index.html: {index}"
    return index


def check_static(index: Path) -> str:
    root = index.parent
    project_files = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".html", ".css", ".js"}]
    for path in project_files:
        text = path.read_text(encoding="utf-8")
        match = PLACEHOLDER.search(text)
        assert not match, f"необработанная подстановка {match.group(0)} в {path.relative_to(root)}"

    parser = ProjectParser()
    parser.feed(index.read_text(encoding="utf-8"))
    assert parser.h1_count == 1, f"ожидался один h1, найдено: {parser.h1_count}"
    assert parser.interface != parser.slides, "не удалось однозначно определить поверхность Craft"

    for value in parser.assets:
        parsed = urlsplit(value)
        assert parsed.scheme not in REMOTE_SCHEMES and not value.startswith("//"), f"внешний ресурс: {value}"
        if parsed.scheme in {"data", "blob"} or value.startswith("#"):
            continue
        assert not Path(unquote(parsed.path)).is_absolute(), f"абсолютный путь к ресурсу: {value}"
        target = (root / unquote(parsed.path)).resolve()
        assert target.is_file(), f"сломанный локальный ресурс: {value}"
    return "interface" if parser.interface else "slides"


def probe(index: Path, surface: str, width: int, height: int) -> tuple[int, ...]:
    probe_path = index.with_name("__craft_check__.html")
    html = index.read_text(encoding="utf-8")
    action = (
        "document.dispatchEvent(new Event('DOMContentLoaded'));const toggle=document.querySelector('[data-theme-toggle]');"
        "const before=document.documentElement.dataset.theme;toggle?.click();const changed=before!==document.documentElement.dataset.theme;"
        if surface == "interface"
        else "const before=document.documentElement.dataset.theme;document.dispatchEvent(new KeyboardEvent('keydown',{key:'T'}));const changed=before!==document.documentElement.dataset.theme;"
    )
    script = (
        action
        + "const controls=[...document.querySelectorAll('button,input,select,textarea,a[href]')];"
        + "const unnamed=controls.filter(el=>{const id=el.id;const label=el.closest('label')||(id&&document.querySelector(`label[for=\"${CSS.escape(id)}\"]`));return !(el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent.trim()||label)}).length;"
        + "const ranks=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(el=>Number(el.tagName[1]));const jumps=ranks.slice(1).filter((rank,i)=>rank>ranks[i]+1).length;"
        + "const slides=[...document.querySelectorAll('.slide')];const undeclared=slides.filter(el=>!el.dataset.slideLayout).length;const active=document.querySelectorAll('.slide[data-active]').length;"
        + "document.title=`craft-check:${document.documentElement.scrollWidth}:${innerWidth}:${unnamed}:${jumps}:${changed?1:0}:${slides.length}:${undeclared}:${active}`;"
    )
    probe_path.write_text(html.replace("</body>", f"<script>{script}</script></body>"), encoding="utf-8")
    try:
        dumped = run(*chromium_args(width, height), "--dump-dom", probe_path.as_uri()).stdout
    finally:
        probe_path.unlink(missing_ok=True)
    match = re.search(r"<title>craft-check:(\d+):(\d+):(\d+):(\d+):([01]):(\d+):(\d+):(\d+)</title>", dumped)
    assert match, f"браузерная проверка не выполнилась при ширине {width}px"
    return tuple(map(int, match.groups()))


def check_browser(index: Path, surface: str) -> None:
    for width, height in VIEWPORTS:
        scroll, viewport, unnamed, jumps, theme_changed, slides, undeclared, active = probe(index, surface, width, height)
        assert scroll <= viewport, f"горизонтальное переполнение при ширине {width}px: {scroll}px > {viewport}px"
        assert unnamed == 0, f"элементы управления без доступного имени: {unnamed}"
        assert jumps == 0, f"найдены пропуски уровней заголовков: {jumps}"
        assert theme_changed == 1, "переключение темы не работает"
        if surface == "slides":
            assert slides > 0 and undeclared == 0 and active == 1, "нарушен контракт слайдовой колоды"

    with tempfile.TemporaryDirectory(prefix="craft-project-pdf-") as directory:
        pdf = Path(directory) / "project.pdf"
        run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", index.as_uri())
        assert pdf.is_file() and pdf.stat().st_size > 5_000, "печать PDF не выполнена"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Папка проекта или путь к index.html")
    parser.add_argument("--static-only", action="store_true", help="Не запускать Chromium и печать PDF")
    args = parser.parse_args()

    index = project_index(args.project)
    surface = check_static(index)
    print(f"✓ статические контракты: {surface}")
    if not args.static_only:
        check_browser(index, surface)
        print("✓ Chromium: 1440, 390 и 320 px, тема, доступность и PDF")
    print(f"Готово: проект Craft корректен — {index}")


if __name__ == "__main__":
    main()
