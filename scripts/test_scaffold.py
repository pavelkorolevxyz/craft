#!/usr/bin/env python3
"""Проверяет минимальные стартеры и публичные каталоги Craft в Chromium."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from lib import MANIFEST, ROOT, chromium_args, run, scaffold_matrix

CATALOG = ROOT / "catalog"
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


def test_scaffold_inputs(root: Path) -> None:
    title = 'A & B <em>X</em> "Q"'
    escaped = "A &amp; B &lt;em&gt;X&lt;/em&gt; &quot;Q&quot;"
    for surface in ("interface", "slides"):
        target = root / f"safe-{surface}"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/scaffold.py"), str(target), "--surface", surface, "--title", title, "--lang", "en-US"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        document = target.joinpath("index.html").read_text(encoding="utf-8")
        assert escaped in document and '<html lang="en-US"' in document, f"{surface}: title или lang вставлены небезопасно"
        assert "<em>X</em>" not in document, f"{surface}: title превратился в HTML"

    invalid = root / "invalid-lang"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/scaffold.py"), str(invalid), "--lang", 'ru" data-test="x'],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0 and not invalid.exists(), "невалидный --lang создал проект"


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


def test_interface_catalog(work: Path) -> None:
    source = ROOT / MANIFEST["surfaces"]["interface"]["testPage"]
    for width, height in VIEWPORTS:
        dumped = dump_probe(
            source,
            "addEventListener('load',()=>{"
            "const theme=document.documentElement.dataset.theme;"
            "const rows=Object.values([...document.querySelectorAll('.equal-panel')].reduce((all,panel)=>{const top=Math.round(panel.getBoundingClientRect().top);(all[top]??=[]).push(panel);return all},{}));"
            "const aligned=rows.every(row=>row.length<2||row.every(panel=>Math.abs(panel.getBoundingClientRect().height-row[0].getBoundingClientRect().height)<1));"
            "const first=document.querySelector('[role=tab]');first.focus();first.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));"
            "const tabsWork=document.querySelector('#catalog-tab-done').getAttribute('aria-selected')==='true'&&!document.querySelector('#catalog-panel-done').hidden;"
            "const opener=document.querySelector('[data-dialog-open]');opener.click();const dialog=document.querySelector('dialog');const dialogOpened=dialog.open;dialog.querySelector('[data-dialog-close]').click();"
            "const selectedRow=document.querySelector('tr[data-interactive][aria-selected=true]');const idleRow=document.querySelector('tr[data-interactive][aria-selected=false]');const rowSelection=getComputedStyle(selectedRow).backgroundColor!==getComputedStyle(idleRow).backgroundColor;"
            "const mechanics=tabsWork&&dialogOpened&&!dialog.open&&document.querySelector('[data-catalog-mixed]').indeterminate&&rowSelection;"
            "document.title=`catalog:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}:${theme}:${aligned}:${document.querySelectorAll('.system-nav').length}:${document.querySelectorAll('[data-section-nav]').length}:${mechanics}`});",
            width,
            height,
        )
        match = re.search(r"<title>catalog:(\d+):(\d+):(\d+):(light|dark):(true|false):(\d+):(\d+):(true|false)</title>", dumped)
        assert match, f"interface-catalog: браузерная проверка не выполнена при {width}px"
        scroll_width, viewport, mains = map(int, match.groups()[:3])
        theme, aligned, sidebars, navs, mechanics = match.groups()[3:]
        assert scroll_width <= viewport, f"interface-catalog: переполнение при {width}px"
        assert mains == 1 and aligned == "true" and int(navs) > 0, "interface-catalog: сломан контракт компонентов"
        assert theme in {"light", "dark"} and int(sidebars) == 0, "interface-catalog: проверочный лист не автономен"
        assert mechanics == "true", "interface-catalog: вкладки, диалог или составной флажок не работают"
    print_pdf(source, work / "interface-catalog.pdf", 1440, 900, 20_000)


def test_interface_docs() -> None:
    surface = MANIFEST["surfaces"]["interface"]
    index = CATALOG / "interfaces/index.html"
    for width in (1440, 320):
        dumped = dump_probe(
            index,
            "addEventListener('load',()=>{const toggle=document.querySelector('[data-theme-toggle]');const before=document.documentElement.dataset.theme;toggle.click();document.title=`docs-index:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('.component-index a').length}:${document.querySelectorAll('.component-group').length}:${before!==document.documentElement.dataset.theme}`});",
            width,
            900,
        )
        match = re.search(r"<title>docs-index:(\d+):(\d+):(\d+):(\d+):(true|false)</title>", dumped)
        assert match, f"индекс документации не открылся при {width}px"
        scroll_width, viewport, components, categories = map(int, match.groups()[:4])
        assert scroll_width <= viewport, f"индекс документации переполнен при {width}px"
        assert components == len(surface["components"]) and categories == len(surface["componentCategories"]), "индекс документации расходится с реестром"
        assert match.group(5) == "true", "переключатель темы индекса не работает"

    pages = {category["id"]: [component["id"] for component in surface["components"] if component["category"] == category["id"]] for category in surface["componentCategories"]}
    pages["recipes"] = []
    for page, expected in pages.items():
        source = CATALOG / "interfaces" / f"{page}.html"
        widths = (1440, 320) if page in {"layout", "forms", "recipes"} else (1440,)
        for width in widths:
            dumped = dump_probe(
                source,
                "addEventListener('load',()=>{"
                "const toggle=document.querySelector('[data-theme-toggle]');const before=document.documentElement.dataset.theme;toggle.click();"
                "const ids=[...document.querySelectorAll('[data-component-doc]')].map(node=>node.dataset.componentDoc).join(',');"
                "const code=[...document.querySelectorAll('[data-preview-code]')];const generated=code.length>0&&code.every(node=>node.textContent.trim().length>0&&node.querySelector('.syntax-tag'));"
                "const tabs=document.querySelector('[data-tabs]');if(tabs){const first=tabs.querySelector('[role=tab]');first.focus();first.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))}"
                "const opener=document.querySelector('[data-dialog-open]');if(opener)opener.click();"
                "const codePanel=document.querySelector('.component-code');codePanel.open=true;const codeBlock=codePanel.querySelector('pre');const codeFits=codeBlock.scrollWidth<=codeBlock.clientWidth;"
                "const currentLink=document.querySelector('.docs-nav .system-links [aria-current=true]');const links=currentLink.parentElement.getBoundingClientRect();const currentBox=currentLink.getBoundingClientRect();const currentVisible=currentBox.left>=links.left&&currentBox.right<=links.right;"
                "const mechanics=(!tabs||tabs.querySelectorAll('[aria-selected=true]').length===1)&&(!opener||document.querySelector('dialog').open)&&codeFits;"
                "document.title=`docs:${document.documentElement.scrollWidth}:${innerWidth}:${ids}:${generated}:${document.querySelectorAll('.docs-nav [aria-current=true]').length}:${before!==document.documentElement.dataset.theme}:${mechanics}:${currentVisible}`});",
                width,
                900,
            )
            match = re.search(r"<title>docs:(\d+):(\d+):([^<]*):(true|false):(\d+):(true|false):(true|false):(true|false)</title>", dumped)
            assert match, f"{page}: браузерная проверка документации не выполнена при {width}px"
            scroll_width, viewport = map(int, match.groups()[:2])
            ids, generated, current, theme, mechanics, current_visible = match.groups()[2:]
            assert scroll_width <= viewport, f"{page}: переполнение документации при {width}px"
            assert (ids.split(",") if ids else []) == expected, f"{page}: браузер видит неполный набор компонентов"
            assert generated == "true" and int(current) == 1, f"{page}: код или навигация документации не работают"
            assert theme == "true" and mechanics == "true", f"{page}: тема или механика примера не работает"
            assert current_visible == "true", f"{page}: текущий раздел навигации не виден при {width}px"


def test_slide_source(name: str, source: Path, work: Path, minimum_pages: int) -> None:
    dumped = dump_probe(
        source,
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));"
        "const afterArrow=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const interactionStart=afterArrow;const link=document.createElement('a');link.href='#test-link';document.body.append(link);const button=document.createElement('button');document.body.append(button);"
        "const enterEvent=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});link.dispatchEvent(enterEvent);const spaceEvent=new KeyboardEvent('keydown',{key:' ',bubbles:true,cancelable:true});button.dispatchEvent(spaceEvent);"
        "const interactiveKeys=!enterEvent.defaultPrevented&&!spaceEvent.defaultPrevented&&document.querySelector('.slide[data-active]')?.dataset.index===interactionStart;link.remove();button.remove();"
        "const toolbar=document.querySelector('.help-panel');const controlSize=parseFloat(getComputedStyle(toolbar.querySelector('button')).width);const revealSize=parseFloat(getComputedStyle(document.querySelector('.help-reveal')).width);const accessibleControls=toolbar.getAttribute('role')==='toolbar'&&Boolean(toolbar.getAttribute('aria-label'))&&controlSize>=40&&revealSize>=40;"
        "const pageInput=document.querySelector('.help-page-input');pageInput.value='0';pageInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));"
        "const afterClamp=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const deck=document.querySelector('.deck');const center=()=>{const a=document.querySelector('.slide[data-active]').getBoundingClientRect();const d=deck.getBoundingClientRect();return Math.round(Math.max(Math.abs(a.left+a.width/2-(d.left+deck.clientWidth/2)),Math.abs(a.top+a.height/2-(d.top+deck.clientHeight/2))))};"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));const stripError=center();document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const before=document.documentElement.dataset.theme;document.dispatchEvent(new KeyboardEvent('keydown',{key:'T'}));"
        "document.title=`slides:${document.querySelectorAll('.slide').length}:${document.querySelectorAll('.slide[data-active]').length}:${afterArrow}:${afterClamp}:${stripError}:${deck.dataset.stripDirection}:${before}:${document.documentElement.dataset.theme}:${document.querySelectorAll('.slide:not([data-slide-layout])').length}:${interactiveKeys}:${accessibleControls}`",
        1280,
        720,
    )
    match = re.search(r"<title>slides:(\d+):(\d+):(\d+):(\d+):(\d+):(\w+):(light|dark):(light|dark):(\d+):(true|false):(true|false)</title>", dumped)
    assert match, f"{name}: проверка механики колоды не выполнена"
    pages, active, after_arrow, after_clamp, strip_error = map(int, match.groups()[:5])
    direction, before, after, undeclared, interactive_keys, accessible_controls = match.groups()[5:]
    assert pages >= minimum_pages and active == 1 and after_clamp == 1, f"{name}: недопустимое состояние колоды"
    if name == "slides-catalog":
        assert pages == MANIFEST["surfaces"]["slides"]["catalogPages"], f"{name}: ожидалось 58 страниц, получено {pages}"
    assert after_arrow == min(2, pages), f"{name}: навигация стрелкой не работает"
    assert direction == "vertical" and strip_error <= 1, f"{name}: активный слайд ленты не по центру"
    assert before != after and undeclared == "0", f"{name}: тема или объявления раскладок не работают"
    assert interactive_keys == "true", f"{name}: Enter или Space перехватываются у ссылок и кнопок"
    assert accessible_controls == "true", f"{name}: панель управления не имеет toolbar-семантики или цели меньше 40 px"

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
        test_scaffold_inputs(root)
        test_interface_starter(outputs["interface-blank"], root)
        test_interface_catalog(root)
        test_interface_docs()
        test_slide_source("slides-deck", outputs["slides-deck"] / "index.html", root, 1)
        test_slide_source("slides-catalog", CATALOG / "slides" / "index.html", root, MANIFEST["surfaces"]["slides"]["catalogPages"])
        for output in outputs.values():
            run(sys.executable, ROOT / "scripts/check_project.py", output)
        print("Готово: стартеры, публичные каталоги и валидатор проектов проверены в Chromium и PDF")
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
