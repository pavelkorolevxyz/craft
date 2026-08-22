#!/usr/bin/env python3
"""Проверяет минимальные стартеры и внутренние фикстуры Craft в Chromium."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from lib import MANIFEST, ROOT, chromium_args, run, scaffold_matrix

FIXTURES = ROOT / "tests" / "fixtures"
VIEWPORTS = ((1440, 900), (390, 844), (320, 720))


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            self.paths.append(values["href"] or "")
        if tag in {"script", "img", "source", "video"} and values.get("src"):
            self.paths.append(values["src"] or "")


def validate_output(key: str, output: Path) -> None:
    index = output / "index.html"
    assert index.is_file(), f"{key}: отсутствует index.html"
    assert (output / "tokens.css").is_file(), f"{key}: отсутствует tokens.css"
    if key.startswith("interface-"):
        assert (output / "theme.js").is_file(), f"{key}: отсутствует theme.js"
        assert (output / "section-nav.js").is_file(), f"{key}: отсутствует section-nav.js"
    expected_fonts = MANIFEST["requirements"]["fontFiles"]
    assert len(list((output / "fonts").glob("*.woff2"))) == expected_fonts

    html = index.read_text(encoding="utf-8")
    assert not re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", html), f"{key}: необработанная подстановка"
    parser = LocalAssetParser()
    parser.feed(html)
    for value in parser.paths:
        assert not value.startswith(("http://", "https://", "//")), f"{key}: внешний ресурс {value}"
        target = output / value.split("?", 1)[0].split("#", 1)[0]
        assert target.is_file(), f"{key}: сломанный ресурс {value}"


def dump_probe(source: Path, script: str, width: int, height: int) -> str:
    probe = source.with_name("__probe.html")
    html = source.read_text(encoding="utf-8")
    probe.write_text(html.replace("</body>", f"<script>{script}</script></body>"), encoding="utf-8")
    try:
        return run(*chromium_args(width, height), "--dump-dom", probe.as_uri()).stdout
    finally:
        probe.unlink(missing_ok=True)


def print_pdf(source: Path, target: Path, width: int, height: int, minimum: int = 10_000) -> None:
    run(*chromium_args(width, height), f"--print-to-pdf={target}", source.as_uri())
    assert target.is_file() and target.stat().st_size > minimum, f"печать PDF не выполнена: {source}"
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        text = run(pdftotext, target, "-").stdout
        assert "file://" not in text, f"в PDF попал адрес браузера: {source}"


def test_interface_starter(output: Path, work: Path) -> None:
    source = output / "index.html"
    for width, height in VIEWPORTS:
        dumped = dump_probe(
            source,
            "document.dispatchEvent(new Event('DOMContentLoaded'));"
            "const button=document.querySelector('[data-theme-toggle]');"
            "const before=document.documentElement.dataset.theme;button.click();"
            "document.title=`probe:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}:${before}:${document.documentElement.dataset.theme}:${document.querySelector('[data-craft-layout]')?.dataset.craftLayout}:${document.querySelector('#craft-content')?.childElementCount}:${button.getAttribute('aria-label')}`",
            width,
            height,
        )
        match = re.search(r"<title>probe:(\d+):(\d+):(\d+):(light|dark):(light|dark):([a-z-]+):(\d+):([^<]+)</title>", dumped)
        assert match, f"interface-blank: браузерная проверка не выполнена при {width}px"
        scroll_width, viewport, mains = map(int, match.groups()[:3])
        before, after, layout, children, label = match.groups()[3:]
        assert scroll_width <= viewport, f"interface-blank: переполнение при {width}px"
        assert mains == 1 and layout == "interface" and children == "0", "interface-blank: стартер не минимален"
        assert before != after and "тему" in label, "interface-blank: переключатель темы не работает"
    print_pdf(source, work / "interface-blank.pdf", 1440, 900)


def test_interface_fixture(work: Path) -> None:
    source = FIXTURES / "interfaces" / "index.html"
    for width, height in VIEWPORTS:
        dumped = dump_probe(
            source,
            "document.dispatchEvent(new Event('DOMContentLoaded'));"
            "const button=document.querySelector('[data-theme-toggle]');const before=document.documentElement.dataset.theme;button.click();"
            "const rows=Object.values([...document.querySelectorAll('.equal-panel')].reduce((all,panel)=>{const top=Math.round(panel.getBoundingClientRect().top);(all[top]??=[]).push(panel);return all},{}));"
            "const aligned=rows.every(row=>row.length<2||row.every(panel=>Math.abs(panel.getBoundingClientRect().height-row[0].getBoundingClientRect().height)<1));"
            "document.title=`fixture:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}:${before}:${document.documentElement.dataset.theme}:${aligned}:${document.querySelectorAll('[data-section-nav]').length}:${button.getAttribute('aria-label')}`",
            width,
            height,
        )
        match = re.search(r"<title>fixture:(\d+):(\d+):(\d+):(light|dark):(light|dark):(true|false):(\d+):([^<]+)</title>", dumped)
        assert match, f"interface-fixture: браузерная проверка не выполнена при {width}px"
        scroll_width, viewport, mains = map(int, match.groups()[:3])
        before, after, aligned, navs, label = match.groups()[3:]
        assert scroll_width <= viewport, f"interface-fixture: переполнение при {width}px"
        assert mains == 1 and aligned == "true" and int(navs) > 0, "interface-fixture: сломан контракт компонентов"
        assert before != after and "тему" in label, "interface-fixture: тема не работает"
    print_pdf(source, work / "interface-fixture.pdf", 1440, 900, 20_000)


def test_slide_source(name: str, source: Path, work: Path, minimum_pages: int) -> None:
    dumped = dump_probe(
        source,
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));"
        "const afterArrow=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const pageInput=document.querySelector('.help-page-input');pageInput.value='0';pageInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));"
        "const afterClamp=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const deck=document.querySelector('.deck');const center=()=>{const a=document.querySelector('.slide[data-active]').getBoundingClientRect();const d=deck.getBoundingClientRect();return Math.round(Math.max(Math.abs(a.left+a.width/2-(d.left+deck.clientWidth/2)),Math.abs(a.top+a.height/2-(d.top+deck.clientHeight/2))))};"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));const stripError=center();document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const before=document.documentElement.dataset.theme;document.dispatchEvent(new KeyboardEvent('keydown',{key:'T'}));"
        "document.title=`slides:${document.querySelectorAll('.slide').length}:${document.querySelectorAll('.slide[data-active]').length}:${afterArrow}:${afterClamp}:${stripError}:${deck.dataset.stripDirection}:${before}:${document.documentElement.dataset.theme}:${document.querySelectorAll('.slide:not([data-slide-layout])').length}`",
        1280,
        720,
    )
    match = re.search(r"<title>slides:(\d+):(\d+):(\d+):(\d+):(\d+):(\w+):(light|dark):(light|dark):(\d+)</title>", dumped)
    assert match, f"{name}: проверка механики колоды не выполнена"
    pages, active, after_arrow, after_clamp, strip_error = map(int, match.groups()[:5])
    direction, before, after, undeclared = match.groups()[5:]
    assert pages >= minimum_pages and active == 1 and after_clamp == 1, f"{name}: недопустимое состояние колоды"
    assert after_arrow == min(2, pages), f"{name}: навигация стрелкой не работает"
    assert direction == "vertical" and strip_error <= 1, f"{name}: активный слайд ленты не по центру"
    assert before != after and undeclared == "0", f"{name}: тема или объявления раскладок не работают"

    pdf = work / f"{name}.pdf"
    print_pdf(source, pdf, 1280, 720, 20_000 if minimum_pages > 1 else 10_000)
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        info = run(pdfinfo, pdf).stdout
        count = re.search(r"^Pages:\s+(\d+)", info, re.M)
        assert count and int(count.group(1)) == pages, f"{name}: количество страниц PDF отличается от колоды"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=Path, help="Сохранить созданные проекты в этой папке")
    args = parser.parse_args()

    context = None if args.keep else tempfile.TemporaryDirectory(prefix="craft-test-")
    root = args.keep.resolve() if args.keep else Path(context.name)
    root.mkdir(parents=True, exist_ok=True)
    try:
        outputs = scaffold_matrix(root / "projects")
        assert set(outputs) == {"interface-blank", "slides-deck"}, "генератор создаёт лишние шаблоны"
        for key, output in outputs.items():
            validate_output(key, output)
            print(f"✓ {key}")
        test_interface_starter(outputs["interface-blank"], root)
        test_interface_fixture(root)
        test_slide_source("slides-deck", outputs["slides-deck"] / "index.html", root, 1)
        test_slide_source("slides-fixture", FIXTURES / "slides" / "index.html", root, 11)
        for output in outputs.values():
            run(sys.executable, ROOT / "scripts/check_project.py", output)
        print("Готово: стартеры, внутренние фикстуры и валидатор проектов проверены в Chromium и PDF")
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
