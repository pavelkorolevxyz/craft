#!/usr/bin/env python3
"""Checks the minimal starters and the public Craft catalogs in Chromium."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_project as check_project_module
from lib import MANIFEST, ROOT, BrowserSession, run, scaffold, scaffold_matrix

CATALOG = ROOT / "catalog"
CHECK_PROJECT = ROOT / "scripts/check_project.py"
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
    assert index.is_file(), f"{key}: index.html is missing"
    assert (output / "tokens.css").is_file(), f"{key}: tokens.css is missing"
    assert (output / "favicon.svg").is_file(), f"{key}: favicon.svg is missing"
    if key.startswith("interface-"):
        assert (output / "theme.js").is_file(), f"{key}: theme.js is missing"
        assert (output / "section-nav.js").is_file(), f"{key}: section-nav.js is missing"
    expected_fonts = MANIFEST["requirements"]["fontFiles"]
    assert len(list((output / "fonts").glob("*.woff2"))) == expected_fonts

    html = index.read_text(encoding="utf-8")
    assert '<link rel="icon" href="favicon.svg" type="image/svg+xml">' in html, f"{key}: favicon is not linked"
    assert not re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", html), f"{key}: unfilled placeholder"
    parser = LocalAssetParser()
    parser.feed(html)
    for value in parser.paths:
        assert not value.startswith(("http://", "https://", "//")), f"{key}: external asset {value}"
        target = output / value.split("?", 1)[0].split("#", 1)[0]
        assert target.is_file(), f"{key}: broken asset {value}"


def test_catalog_favicons() -> None:
    pages = sorted(CATALOG.rglob("*.html"))
    assert pages, "public catalogs not found"
    for page in pages:
        surface = page.relative_to(CATALOG).parts[0]
        favicon = "favicon-slides.svg" if surface == "slides" else "favicon-interface.svg"
        expected = f'<link rel="icon" href="../../assets/shared/{favicon}" type="image/svg+xml">'
        html = page.read_text(encoding="utf-8")
        assert expected in html, f"{page.relative_to(ROOT)}: favicon is not linked"


def dump_probe(source: Path, script: str, width: int, height: int) -> str:
    html = source.read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=source.parent, prefix="__probe-", suffix=".html", delete=False
    ) as handle:
        handle.write(html.replace("</body>", f"<script>{script}</script></body>"))
        probe = Path(handle.name)
    title = re.search(r"<title>([^<]*)</title>", html)
    try:
        return BrowserSession.shared().dump(probe.as_uri(), width, height, title.group(1) if title else "")
    finally:
        probe.unlink(missing_ok=True)


def after_stable_layout(script: str) -> str:
    """Runs the probe after fonts load and the layout updates."""
    return (
        "addEventListener('load',()=>{document.fonts.ready.then(()=>setTimeout(()=>{"
        + script
        + "},0))},{once:true});"
    )


def print_pdf(source: Path, target: Path, width: int, height: int, minimum: int = 5_000) -> None:
    BrowserSession.shared().pdf(source.as_uri(), target, width, height)
    assert target.is_file() and target.stat().st_size > minimum, f"PDF printing failed: {source}"
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        text = run(pdftotext, target, "-").stdout
        assert "file://" not in text, f"browser address got into the PDF: {source}"


def test_scaffold_inputs(root: Path) -> None:
    title = 'A & B <em>X</em> "Q"'
    escaped = "A &amp; B &lt;em&gt;X&lt;/em&gt; &quot;Q&quot;"
    for surface in ("interface", "slides"):
        target = root / f"safe-{surface}"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/scaffold.py"), str(target), "--surface", surface, "--title", title, "--lang", "de-DE"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        document = target.joinpath("index.html").read_text(encoding="utf-8")
        assert escaped in document and '<html lang="de-DE"' in document, f"{surface}: title or lang inserted unsafely"
        assert "<em>X</em>" not in document, f"{surface}: title turned into HTML"

    invalid = root / "invalid-lang"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/scaffold.py"), str(invalid), "--lang", 'ru" data-test="x'],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0 and not invalid.exists(), "an invalid --lang created a project"


def assert_static_failure(project: Path, expected: str) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK_PROJECT), str(project), "--static-only"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr


def test_static_resources(root: Path) -> None:
    iframe = root / "external-iframe"
    scaffold(iframe, "interface", "blank")
    index = iframe / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace("</body>", '<iframe src="https://example.com/embed"></iframe></body>'), encoding="utf-8")
    assert_static_failure(iframe, "external asset")

    srcset = root / "external-srcset"
    scaffold(srcset, "interface", "blank")
    index = srcset / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace("</body>", '<img alt="" srcset="https://example.com/a.png 1x, local.png 2x"></body>'), encoding="utf-8")
    assert_static_failure(srcset, "external asset")

    imported = root / "external-import"
    scaffold(imported, "interface", "blank")
    theme = imported / "theme.css"
    theme.write_text(theme.read_text(encoding="utf-8") + '\n@import url("https://example.com/theme.css");\n', encoding="utf-8")
    assert_static_failure(imported, "external asset")

    escaped = root / "escaped-resource"
    scaffold(escaped, "interface", "blank")
    root.joinpath("outside.css").write_text("body {}\n", encoding="utf-8")
    index = escaped / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace("</head>", '<link rel="stylesheet" href="../outside.css"></head>'), encoding="utf-8")
    assert_static_failure(escaped, "asset points outside the project folder")


def test_delivery_and_bundle(root: Path) -> None:
    web = root / "delivery-web"
    run(sys.executable, ROOT / "scripts/scaffold.py", web, "--surface", "interface", "--title", "Web", "--delivery", "web")
    index = web / "index.html"
    text = index.read_text(encoding="utf-8")
    assert 'data-craft-delivery="web"' in text and "fonts.googleapis.com" in text, "web delivery is not set up"
    assert not (web / "fonts").exists(), "web delivery must not copy fonts"
    assert "@font-face" not in (web / "tokens.css").read_text(encoding="utf-8"), "local fonts are left in web delivery"
    run(sys.executable, CHECK_PROJECT, web, "--static-only")
    index.write_text(text.replace("</head>", '<script src="https://evil.example/x.js"></script></head>'), encoding="utf-8")
    assert_static_failure(web, "not on the allowlist")
    index.write_text(text, encoding="utf-8")

    bundled = root / "delivery-bundle"
    scaffold(bundled, "interface", "blank")
    run(sys.executable, ROOT / "scripts/bundle.py", bundled)
    single = root / "delivery-single"
    single.mkdir()
    shutil.copy2(bundled / "index.single.html", single / "index.html")
    run(sys.executable, CHECK_PROJECT, single, "--static-only")
    text = (single / "index.html").read_text(encoding="utf-8")
    assert "base64," in text and "<style>" in text and 'href="tokens.css"' not in text, "the bundle did not inline the assets"


def test_project_check_batches_browser(root: Path) -> None:
    project = root / "batched-browser-check"
    scaffold(project, "interface", "blank")
    index = project / "café #1?.html"
    (project / "index.html").rename(index)
    calls: list[tuple[str, ...]] = []

    def fake_run(arguments: list[str], **_: object) -> SimpleNamespace:
        command = tuple(map(str, arguments))
        calls.append(command)
        assert command[1].endswith("page_check.mjs") and str(index) in command, "the page is not checked by page_check.mjs"
        assert "--viewports" in command and all(f"{width}x{height}" in command[command.index("--viewports") + 1] for width, height in VIEWPORTS)
        result = {"scroll": 0, "viewport": 0, "unnamed": 0, "jumps": 0, "themeChanged": True, "slides": 0, "undeclared": 0, "active": 0, "spill": 0, "shell": True, **{f"{key}Count": 0 for key in check_project_module.VISUAL_CHECKS}, **{key: [] for key in check_project_module.VISUAL_CHECKS}}
        viewports = [{**result, "scroll": width, "viewport": width} for width, _ in VIEWPORTS]
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps([{"index": str(index), "viewports": viewports, "pdfBytes": 6_000 if "--pdf" in command else None}]))

    with patch.object(check_project_module.subprocess, "run", side_effect=fake_run):
        check_project_module.check_browser(index, "interface", full=True)
    assert len(calls) == 1, f"expected one browser session for viewports and PDF, got: {len(calls)}"
    assert "--pdf" in calls[0], "the full check did not print the PDF in the same session"


def test_project_check_rejects_double_boundaries(root: Path) -> None:
    project = root / "double-boundary"
    project.mkdir()
    index = project / "index.html"
    index.write_text(
        '''<!doctype html><html lang="en" data-theme="dark"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>*{box-sizing:border-box}body{margin:0}.theme{position:fixed}.head{height:64px;border-bottom:1px solid #444}.list{margin:0;border-top:1px solid #444}</style>
<button class="theme" data-theme-toggle aria-label="Switch theme" onclick="document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark'">Theme</button>
<header class="head"><h1>Pages</h1></header><main data-craft-layout="interface"><ol class="list"><li>Item</li></ol></main></html>''',
        encoding="utf-8",
    )
    doubled = check_project_module.probe_all(index, "interface")
    assert all(result["doubleBordersCount"] > 0 for result in doubled), "the validator missed two owners of a shared border"
    index.write_text(index.read_text(encoding="utf-8").replace(".list{margin:0;border-top:1px solid #444}", ".list{margin:0}"), encoding="utf-8")
    fixed = check_project_module.probe_all(index, "interface")
    assert all(result["doubleBordersCount"] == 0 for result in fixed), "the validator counts a single border as double"


def test_project_check_rejects_detached_page_tabs(root: Path) -> None:
    project = root / "page-tabs"
    project.mkdir()
    index = project / "index.html"
    page = '''<!doctype html><html lang="en" data-theme="dark"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>body{margin:0}.inset{margin:0 20px}</style>
<main data-craft-layout="interface"><header class="workspace-head"><h1>Calculations</h1></header>
<div class="TABS"><div class="tablist" role="tablist" aria-label="Sections"><button role="tab" type="button">Overview</button></div></div></main></html>'''
    cases = {"tabs": True, "tabs tabs--page inset": True, "tabs tabs--page": False}
    for classes, broken in cases.items():
        index.write_text(page.replace("TABS", classes), encoding="utf-8")
        counts = [result["pageTabsCount"] for result in check_project_module.probe_all(index, "interface")]
        assert all((count > 0) == broken for count in counts), f"the validator misjudged tabs under the header: {classes} → {counts}"


def test_catalog_visual_quality() -> None:
    pages = sorted((CATALOG / "interfaces").glob("*.html"))
    for page, checked in zip(pages, check_project_module.page_check(pages, "interface")):
        for (width, _), result in zip(VIEWPORTS, checked["viewports"]):
            assert result["scroll"] <= width, f"{page.name}: horizontal overflow at {width}px"
            for key, message in check_project_module.VISUAL_CHECKS.items():
                assert result[f"{key}Count"] == 0, f"{page.name}: {message} at {width}px: {'; '.join(result[key])}"

def test_dump_probe_isolated(root: Path) -> None:
    source = root / "probe-source.html"
    source.write_text("<!doctype html><title>probe</title><body></body>", encoding="utf-8")
    browser_urls: list[str] = []

    def fake_dump(url: str, *_: object) -> str:
        browser_urls.append(url)
        probes = list(root.glob("__probe-*.html"))
        assert len(probes) == 1 and probes[0].is_file(), "the probe is not isolated in a temp file"
        return "<title>probe-ready</title>"

    with patch.object(BrowserSession, "shared", return_value=SimpleNamespace(dump=fake_dump)):
        dump_probe(source, "document.title='probe-ready'", 320, 720)
        dump_probe(source, "document.title='probe-ready'", 320, 720)
    assert len(set(browser_urls)) == 2, "consecutive probes share one temp path"
    assert not list(root.glob("__probe-*.html")), "a temp probe was left after the check"


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
        assert match, f"interface-blank: browser check did not run at {width}px"
        scroll_width, viewport, mains = map(int, match.groups()[:3])
        before, after, layout, children, label = match.groups()[3:]
        assert scroll_width <= viewport, f"interface-blank: overflow at {width}px"
        assert mains == 1 and layout == "interface" and children == "0", "interface-blank: the starter is not minimal"
        assert before != after and "theme" in label, "interface-blank: the theme toggle does not work"
    print_pdf(source, work / "interface-blank.pdf", 1440, 900)


def test_interface_bare(output: Path, work: Path) -> None:
    html = (output / "index.html").read_text(encoding="utf-8")
    assert "data-craft-shell" not in html and "data-theme-toggle" not in html, "interface-bare: the shell-free starter contains a shell"
    assert 'data-craft-layout="interface"' in html and 'id="craft-content"' in html and 'src="theme.js"' in html, "interface-bare: no format root or theme choice"
    dumped = dump_probe(
        output / "index.html",
        "const paint=theme=>{CraftTheme.set(theme);return getComputedStyle(document.body).backgroundColor};"
        "document.title=`probe:${paint('light')!==paint('dark')?1:0}`",
        390,
        844,
    )
    assert "<title>probe:1</title>" in dumped, "interface-bare: the theme does not change styles without a shell"

    shell = work / "shell-without-toggle"
    shutil.copytree(work / "projects/interface-blank", shell)
    index = shell / "index.html"
    index.write_text(re.sub(r'<button[^>]*data-theme-toggle.*?</button>', "", index.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
    try:
        check_project_module.check_browser(index, "interface")
    except AssertionError as error:
        assert "theme switching" in str(error), f"the shell without a toggle failed for a reason other than the theme: {error}"
    else:
        raise AssertionError("the validator accepted a shell without a theme toggle")


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
            "const donut=document.querySelector('.donut-layout');const donutReady=innerWidth>600||getComputedStyle(donut).gridTemplateColumns.trim().split(/\\s+/).length===1;"
            "const mechanics=tabsWork&&dialogOpened&&!dialog.open&&document.querySelector('[data-catalog-mixed]').indeterminate&&rowSelection&&donutReady;"
            "document.title=`catalog:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}:${theme}:${aligned}:${document.querySelectorAll('.system-nav').length}:${document.querySelectorAll('[data-section-nav]').length}:${mechanics}`});",
            width,
            height,
        )
        match = re.search(r"<title>catalog:(\d+):(\d+):(\d+):(light|dark):(true|false):(\d+):(\d+):(true|false)</title>", dumped)
        assert match, f"interface-catalog: browser check did not run at {width}px"
        scroll_width, viewport, mains = map(int, match.groups()[:3])
        theme, aligned, sidebars, navs, mechanics = match.groups()[3:]
        assert scroll_width <= viewport, f"interface-catalog: overflow at {width}px"
        assert mains == 1 and aligned == "true" and int(navs) > 0, "interface-catalog: component contract broken"
        assert theme in {"light", "dark"} and int(sidebars) == 0, "interface-catalog: the test sheet is not standalone"
        assert mechanics == "true", "interface-catalog: tabs, dialog or indeterminate checkbox do not work"
    print_pdf(source, work / "interface-catalog.pdf", 1440, 900, 20_000)


def test_interface_docs() -> None:
    surface = MANIFEST["surfaces"]["interface"]
    index = CATALOG / "interfaces/index.html"
    for width in (1440, 320):
        dumped = dump_probe(
            index,
            after_stable_layout(
                "const toggle=document.querySelector('[data-theme-toggle]');const before=document.documentElement.dataset.theme;toggle.click();document.title=`docs-index:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('.component-index a').length}:${document.querySelectorAll('.component-group').length}:${before!==document.documentElement.dataset.theme}`"
            ),
            width,
            900,
        )
        match = re.search(r"<title>docs-index:(\d+):(\d+):(\d+):(\d+):(true|false)</title>", dumped)
        assert match, f"docs index did not open at {width}px"
        scroll_width, viewport, components, categories = map(int, match.groups()[:4])
        assert scroll_width <= viewport, f"docs index overflows at {width}px"
        assert components == 6 and categories == 1, "the home page must show only six levels"
        assert match.group(5) == "true", "the index theme toggle does not work"

    pages = {}
    for page in ("foundations", "atoms", "molecules", "organisms", "templates", "pages"):
        source = CATALOG / "interfaces" / f"{page}.html"
        pages[page] = re.findall(r'data-component-doc="([a-z-]+)"', source.read_text(encoding="utf-8"))
    for page, expected in pages.items():
        source = CATALOG / "interfaces" / f"{page}.html"
        widths = (1440, 320) if page in {"foundations", "atoms", "molecules", "organisms", "pages"} else (1440,)
        for width in widths:
            dumped = dump_probe(
                source,
                after_stable_layout(
                "const toggle=document.querySelector('[data-theme-toggle]');const before=document.documentElement.dataset.theme;toggle.click();"
                "const ids=[...document.querySelectorAll('[data-component-doc]')].map(node=>node.dataset.componentDoc).join(',');"
                "const code=[...document.querySelectorAll('[data-preview-code]')];const generated=code.length===0||code.every(node=>node.textContent.trim().length>0&&node.querySelector('.syntax-tag'));"
                "const tabs=document.querySelector('[data-tabs]');if(tabs){const first=tabs.querySelector('[role=tab]');first.focus();first.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))}"
                "const opener=document.querySelector('[data-dialog-open]');if(opener)opener.click();"
                "const codePanel=document.querySelector('.component-code');if(codePanel)codePanel.open=true;const codeBlock=codePanel?.querySelector('pre');const codeFits=!codeBlock||codeBlock.scrollWidth<=codeBlock.clientWidth;"
                "const currentLink=document.querySelector('.docs-nav .system-links [aria-current=true]');const links=currentLink.parentElement.getBoundingClientRect();const currentBox=currentLink.getBoundingClientRect();const currentVisible=currentBox.left>=links.left&&currentBox.right<=links.right;"
                "const records=document.querySelector('.data-table--records');const recordCells=records?[...records.querySelectorAll('td')]:[];const recordsReady=!records||innerWidth>520||(getComputedStyle(records.querySelector('tbody')).display==='grid'&&recordCells.every(cell=>cell.dataset.label&&getComputedStyle(cell,'::before').content!=='none'));"
                "const mechanics=(!tabs||tabs.querySelectorAll('[aria-selected=true]').length===1)&&(!opener||document.querySelector('dialog').open)&&codeFits&&recordsReady;"
                "document.title=`docs:${document.documentElement.scrollWidth}:${innerWidth}:${ids}:${generated}:${document.querySelectorAll('.docs-nav [aria-current=true]').length}:${before!==document.documentElement.dataset.theme}:${mechanics}:${currentVisible}`"
                ),
                width,
                900,
            )
            match = re.search(r"<title>docs:(\d+):(\d+):([^<]*):(true|false):(\d+):(true|false):(true|false):(true|false)</title>", dumped)
            assert match, f"{page}: docs browser check did not run at {width}px"
            scroll_width, viewport = map(int, match.groups()[:2])
            ids, generated, current, theme, mechanics, current_visible = match.groups()[2:]
            assert scroll_width <= viewport, f"{page}: docs overflow at {width}px"
            assert (ids.split(",") if ids else []) == expected, f"{page}: the browser sees an incomplete set of components"
            assert generated == "true" and int(current) == 1, f"{page}: docs code or navigation does not work"
            assert theme == "true" and mechanics == "true", f"{page}: example theme or mechanics do not work"
            assert current_visible == "true", f"{page}: the current nav section is not visible at {width}px"


def test_slide_source(name: str, source: Path, work: Path, minimum_pages: int) -> None:
    dumped = dump_probe(
        source,
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));"
        "const afterArrow=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const interactionStart=afterArrow;const link=document.createElement('a');link.href='#test-link';document.body.append(link);const button=document.createElement('button');document.body.append(button);"
        "const enterEvent=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});link.dispatchEvent(enterEvent);const spaceEvent=new KeyboardEvent('keydown',{key:' ',bubbles:true,cancelable:true});button.dispatchEvent(spaceEvent);"
        "const interactiveKeys=!enterEvent.defaultPrevented&&!spaceEvent.defaultPrevented&&document.querySelector('.slide[data-active]')?.dataset.index===interactionStart;link.remove();button.remove();"
        "const toolbar=document.querySelector('.help-panel');const controlSize=parseFloat(getComputedStyle(toolbar.querySelector('button')).width);const revealSize=parseFloat(getComputedStyle(document.querySelector('.help-reveal')).width);const accessibleControls=toolbar.getAttribute('role')==='toolbar'&&Boolean(toolbar.getAttribute('aria-label'))&&controlSize>=40&&revealSize>=40;"
        "const slideSemantics=[...document.querySelectorAll('.slide')].every(slide=>slide.getAttribute('role')==='group'&&slide.getAttribute('aria-roledescription')==='slide'&&slide.getAttribute('aria-label')?.startsWith('Slide '))&&document.querySelectorAll('.slide[aria-current=page]').length===1&&[...document.querySelectorAll('.slide-number')].every(number=>number.getAttribute('aria-hidden')==='true');"
        "const tablesLabeled=[...document.querySelectorAll('.slide table')].every(table=>{const ids=(table.getAttribute('aria-labelledby')||'').split(/\\s+/).filter(Boolean);return ids.length>0&&ids.every(id=>document.getElementById(id))});"
        "const pageInput=document.querySelector('.help-page-input');pageInput.value='0';pageInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));"
        "const afterClamp=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const deck=document.querySelector('.deck');const center=()=>{const a=document.querySelector('.slide[data-active]').getBoundingClientRect();const d=deck.getBoundingClientRect();return Math.round(Math.max(Math.abs(a.left+a.width/2-(d.left+deck.clientWidth/2)),Math.abs(a.top+a.height/2-(d.top+deck.clientHeight/2))))};"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));const stripError=center();document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const before=document.documentElement.dataset.theme;document.dispatchEvent(new KeyboardEvent('keydown',{key:'T'}));"
        "document.title=`slides:${document.querySelectorAll('.slide').length}:${document.querySelectorAll('.slide[data-active]').length}:${afterArrow}:${afterClamp}:${stripError}:${deck.dataset.stripDirection}:${before}:${document.documentElement.dataset.theme}:${document.querySelectorAll('.slide:not([data-slide-layout])').length}:${interactiveKeys}:${accessibleControls}:${slideSemantics}:${tablesLabeled}:${document.querySelectorAll('.slide[data-print-page] > .slide-canvas').length}`",
        1280,
        720,
    )
    match = re.search(r"<title>slides:(\d+):(\d+):(\d+):(\d+):(\d+):(\w+):(light|dark):(light|dark):(\d+):(true|false):(true|false):(true|false):(true|false):(\d+)</title>", dumped)
    assert match, f"{name}: deck mechanics check did not run"
    pages, active, after_arrow, after_clamp, strip_error = map(int, match.groups()[:5])
    direction, before, after, undeclared, interactive_keys, accessible_controls, slide_semantics, tables_labeled, print_pages = match.groups()[5:]
    assert pages >= minimum_pages and active == 1 and after_clamp == 1, f"{name}: invalid deck state"
    if name == "slides-catalog":
        assert pages == MANIFEST["surfaces"]["slides"]["catalogPages"], f"{name}: expected 58 pages, got {pages}"
    assert after_arrow == min(2, pages), f"{name}: arrow navigation does not work"
    assert direction == "vertical" and strip_error <= 1, f"{name}: the active strip slide is not centered"
    assert before != after and undeclared == "0", f"{name}: theme or layout declarations do not work"
    assert interactive_keys == "true", f"{name}: Enter or Space is taken away from links and buttons"
    assert accessible_controls == "true", f"{name}: the control panel lacks toolbar semantics or has targets under 40 px"
    assert slide_semantics == "true", f"{name}: slides lack accessible names or aria-current"
    assert tables_labeled == "true", f"{name}: a table is not tied to a heading or caption"
    assert int(print_pages) == pages, f"{name}: not every screen page got its own print area"

    if name == "slides-catalog":
        assert pages == MANIFEST["surfaces"]["slides"]["catalogPrintPages"], f"{name}: wrong print page count in the manifest"

    pdf = work / f"{name}.pdf"
    print_pdf(source, pdf, 1280, 720, 20_000 if minimum_pages > 1 else 10_000)
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        info = run(pdfinfo, pdf).stdout
        count = re.search(r"^Pages:\s+(\d+)", info, re.M)
        assert count and int(count.group(1)) == pages, f"{name}: the PDF must contain every screen page"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=Path, help="Keep the created projects in this folder")
    args = parser.parse_args()

    context = None if args.keep else tempfile.TemporaryDirectory(prefix="craft-test-")
    root = args.keep.resolve() if args.keep else Path(context.name)
    root.mkdir(parents=True, exist_ok=True)
    try:
        outputs = scaffold_matrix(root / "projects")
        assert set(outputs) == {"interface-blank", "interface-bare", "slides-deck"}, "the generator creates extra templates"
        for key, output in outputs.items():
            validate_output(key, output)
            print(f"✓ {key}")
        test_scaffold_inputs(root)
        test_catalog_favicons()
        test_static_resources(root)
        test_delivery_and_bundle(root)
        test_project_check_batches_browser(root)
        test_project_check_rejects_double_boundaries(root)
        test_project_check_rejects_detached_page_tabs(root)
        test_dump_probe_isolated(root)
        test_interface_starter(outputs["interface-blank"], root)
        test_interface_bare(outputs["interface-bare"], root)
        test_interface_catalog(root)
        test_interface_docs()
        test_catalog_visual_quality()
        test_slide_source("slides-deck", outputs["slides-deck"] / "index.html", root, 1)
        test_slide_source("slides-catalog", CATALOG / "slides" / "index.html", root, MANIFEST["surfaces"]["slides"]["catalogPages"])
        test_slide_source("slides-case-study", CATALOG / "slides" / "case-study.html", root, 8)
        for output in outputs.values():
            run(sys.executable, ROOT / "scripts/check_project.py", output)
        print("Done: starters, public catalogs and the project validator checked in Chromium and PDF")
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
