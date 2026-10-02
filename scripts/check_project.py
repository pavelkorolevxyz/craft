#!/usr/bin/env python3
"""Checks a standalone interface or slide deck built with Craft."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lib import ROOT, node, run

PLACEHOLDER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_IMPORT = re.compile(r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)", re.I)
CSS_URL = re.compile(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", re.I)
VIEWPORTS = ((1440, 900), (390, 844), (320, 720))
WEB_DELIVERY = re.compile(r"<html\b[^>]*\bdata-craft-delivery=\"web\"")
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net", "unpkg.com"}


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
        if tag in {"script", "img", "source", "video", "audio", "track", "iframe", "embed"} and values.get("src"):
            self.assets.append(values["src"] or "")
        if tag == "object" and values.get("data"):
            self.assets.append(values["data"] or "")
        if tag == "video" and values.get("poster"):
            self.assets.append(values["poster"] or "")
        if tag in {"img", "source"} and values.get("srcset"):
            self.assets.extend(
                candidate.strip().split()[0]
                for candidate in (values["srcset"] or "").split(",")
                if candidate.strip()
            )
        if values.get("style"):
            self.assets.extend(css_references(values["style"] or ""))


def project_index(path: Path) -> Path:
    target = path.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    assert index.is_file(), f"index.html not found: {index}"
    return index


def css_references(text: str) -> list[str]:
    source = CSS_COMMENT.sub("", text)
    return [*CSS_IMPORT.findall(source), *CSS_URL.findall(source)]


def validate_reference(root: Path, base: Path, value: str, origin: Path, web: bool = False) -> None:
    reference = value.strip()
    if not reference or reference.startswith("#"):
        return
    parsed = urlsplit(reference)
    if parsed.scheme in {"data", "blob"}:
        return
    if parsed.scheme or reference.startswith("//"):
        allowed = web and parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
        detail = "external asset not on the allowlist" if web else "external asset in a local project"
        assert allowed, f"{detail} in {origin.relative_to(root)}: {reference}"
        return
    relative = Path(unquote(parsed.path))
    assert not relative.is_absolute(), f"absolute asset path in {origin.relative_to(root)}: {reference}"
    target = (base / relative).resolve()
    assert target == root or root in target.parents, f"asset points outside the project folder in {origin.relative_to(root)}: {reference}"
    assert target.is_file(), f"broken local asset in {origin.relative_to(root)}: {reference}"


def check_qr_color(text: str) -> None:
    """QR modules take the color of the .qr border. Use an inline svg with currentColor, not <img> and not a hardcoded color."""
    for block in re.findall(r'<div class="qr">(.*?)</div>', text, re.DOTALL):
        assert "<img" not in block, "the QR inside .qr must be an inline <svg> with currentColor, not <img>, or the module color will not match the border"
        if "<use" in block:
            continue
        paints = re.findall(r'(?:fill|stroke)\s*[=:]\s*["\']?\s*([^"\';\s]+)', block)
        paints = [value for value in paints if value != "none"]
        assert paints and all(value == "currentColor" for value in paints), (
            "the QR inside .qr must paint its modules with currentColor so they match the border"
        )


SLIDE_SECTION = re.compile(r'<section\b[^>]*class="[^"]*\bslide\b[^"]*"[^>]*>(.*?)</section>', re.DOTALL)
CODE_BLOCK = re.compile(r"<(pre|code|script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
COUNT_VALUE = re.compile(r"<[^>]*\bdata-count\b[^>]*>([^<]*)<")
MOTION_QUERY = re.compile(r"prefers-reduced-motion")
MECHANICS = {"deck.js", "media.js"}


def check_slide_sources(root: Path, index: Path, files: list[Path]) -> None:
    """Deck rules that show in the source before any browser runs."""
    for path in files:
        if path.suffix in {".css", ".js"} and path.name not in MECHANICS and "vendor" not in path.parts:
            text = CSS_COMMENT.sub("", path.read_text(encoding="utf-8"))
            assert not MOTION_QUERY.search(text), (
                f"prefers-reduced-motion in {path.relative_to(root)}: the deck turns motion off with one policy. "
                "Write the rule for :root[data-motion-state=\"on\"] or keep the animation, base.css removes it"
            )
    document = index.read_text(encoding="utf-8")
    # Each clip takes a hardware decoder on page load, and a phone has only a
    # few. media.js loads clips within the warm-up radius.
    eager = [tag for tag in re.findall(r"<video\b[^>]*>", document) if not re.search(r'\bpreload=["\']none["\']', tag)]
    assert not eager, (
        f"video without preload=\"none\" ({len(eager)}): on load all clips would grab the phone decoders at once. "
        "media.js loads the open page and its neighbors"
    )
    lang = re.search(r'<html\b[^>]*\blang=["\']([^"\']*)', document, re.I)
    english = not lang or not lang.group(1) or lang.group(1).lower().startswith("en")
    for body in SLIDE_SECTION.findall(document):
        visible = CODE_BLOCK.sub("", body)
        assert not re.search(r"<br\s*/?>", visible, re.I), (
            "manual <br> inside a slide: let the browser wrap lines, or text-wrap produces ragged lines. "
            "Use code lines or separate list items instead of breaks"
        )
        for value in COUNT_VALUE.findall(body):
            # One token covers digits joined by a comma, a no-break space, a narrow
            # no-break space or a plain space, so "12,400" and "12 400" match whole.
            digits = re.search(r"\d(?:[\d \u00a0\u202f]|,(?=\d))*\d", value)
            if not digits:
                continue
            token = digits.group(0)
            # English groups digits with a comma; Russian and other languages with
            # a no-break space, since their comma is the decimal mark.
            sample = "12,400" if english else "12\u00a0400 with a no-break space"
            assert " " not in token, (
                f'plain space in counter number "{value.strip()}": write {sample}, or the number may wrap'
            )
            plain = re.sub(r"[,\u00a0\u202f]", "", token)
            if len(plain) >= 5:
                assert token != plain, f'counter number "{value.strip()}" has no group separator: write {sample}'


def check_static(index: Path, resource_root: Path | None = None) -> str:
    root = index.parent
    resources = resource_root.expanduser().resolve() if resource_root else root
    assert resources == root or resources in root.parents, "the resource folder must contain the project under check"
    project_files = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".html", ".css", ".js"}]
    web = bool(WEB_DELIVERY.search(index.read_text(encoding="utf-8")))
    html_parsers: dict[Path, ProjectParser] = {}
    for path in project_files:
        text = path.read_text(encoding="utf-8")
        match = PLACEHOLDER.search(text)
        assert not match, f"unfilled placeholder {match.group(0)} in {path.relative_to(root)}"
        if path.suffix == ".html":
            parser = ProjectParser()
            parser.feed(text)
            html_parsers[path] = parser
            for value in parser.assets:
                validate_reference(resources, path.parent, value, path, web)
        elif path.suffix == ".css":
            for value in css_references(text):
                validate_reference(resources, path.parent, value, path, web)

    parser = html_parsers[index]
    assert parser.h1_count == 1, f"expected one h1, found: {parser.h1_count}"
    assert parser.interface != parser.slides, "cannot tell the Craft format for sure"
    if parser.slides:
        check_qr_color(index.read_text(encoding="utf-8"))
        check_slide_sources(root, index, project_files)
    return "interface" if parser.interface else "slides"


def page_check(indexes: list[Path], surface: str, pdf: bool = False) -> list[dict]:
    """Runs page_check.mjs on several pages in one Chromium session."""
    command: list[str | Path] = [node(), ROOT / "scripts/page_check.mjs", *indexes, "--surface", surface]
    command += ["--viewports", ",".join(f"{width}x{height}" for width, height in VIEWPORTS)]
    if pdf:
        command.append("--pdf")
    result = subprocess.run([str(part) for part in command], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(f"the browser check did not run: {(result.stderr or result.stdout).strip()[-600:]}")
    results = json.loads(result.stdout)
    assert len(results) == len(indexes), "Chromium returned an incomplete check result"
    for result in results:
        assert len(result["viewports"]) == len(VIEWPORTS) and all("scroll" in item for item in result["viewports"]), "Chromium returned an incomplete check result"
    return results


def probe_all(index: Path, surface: str) -> list[dict]:
    """Checks every test viewport of one page in one Chromium run."""
    return page_check([index], surface)[0]["viewports"]


VISUAL_CHECKS = {
    "doubleBorders": "double borders on shared edges",
    "pageTabs": "tabs under the header without .tabs--page or not full width",
    "overlaps": "text overlaps other text",
    "outside": "text overflows its block",
    "clipped": "text clipped by container",
    "tiny": "text smaller than 12 px",
    "contrast": "text contrast below WCAG AA",
    "smallTargets": "tap target smaller than 24 px",
}


def check_viewports(results: list[dict], surface: str) -> None:
    for (width, _), result in zip(VIEWPORTS, results):
        assert result["viewport"] == width, f"Chromium opened the {width}px test viewport at {result['viewport']}px wide"
        assert result["scroll"] <= width, f"horizontal overflow at {width}px: {result['scroll']}px > {width}px"
        assert result["spill"] == 0, f"control panel runs past the edge at {width}px by {result['spill']}px"
        assert result["unnamed"] == 0, f"controls without an accessible name: {result['unnamed']}"
        assert result["jumps"] == 0, f"skipped heading levels: {result['jumps']}"
        if surface == "slides" or result["shell"]:
            assert result["themeChanged"], "theme switching does not work"
        if surface == "interface":
            for key, message in VISUAL_CHECKS.items():
                assert result[f"{key}Count"] == 0, f"{message} at {width}px ({result[f'{key}Count']}): {'; '.join(result[key])}"
        if surface == "slides":
            assert result["slides"] > 0 and result["undeclared"] == 0 and result["active"] == 1, "slide deck contract broken"


def check_browser(index: Path, surface: str, full: bool = False) -> None:
    """Page in one Chromium session: three widths, both themes, and with full the PDF."""
    result = page_check([index], surface, pdf=full)[0]
    check_viewports(result["viewports"], surface)
    if full:
        assert result["pdfBytes"] and result["pdfBytes"] > 5_000, "PDF printing failed"


# What each level walks in a deck. render is the default: every state in its
# final frame at three widths and on a phone. full adds the light theme,
# the control panel, motion, deep links, video and both PDFs.
DECK_PASSES = {
    "render": "viewports,frames,phone",
    "full": "viewports,frames,light,phone,panel,motion,navigation,video,print",
}


def check_deck(index: Path, level: str = "full", shots: Path | None = None) -> dict:
    """Walks deck states in one Chromium session; the level picks the passes."""
    command: list[str | Path] = [node(), ROOT / "scripts/deck_probe.mjs", index, "--passes", DECK_PASSES[level]]
    command += ["--viewports", ",".join(f"{width}x{height}" for width, height in VIEWPORTS)]
    if shots:
        command += ["--shots", shots]
    report = json.loads(run(*command).stdout)
    for item in report["warnings"]:
        print(f"! {format_issue(item)}")
    if report["errors"]:
        lines = "\n".join(f"  {format_issue(item)}" for item in report["errors"])
        raise AssertionError(f"the deck failed the state check ({len(report['errors'])}):\n{lines}")
    check_viewports(report["viewports"], "slides")
    return report


def format_issue(item: dict) -> str:
    place = []
    if item.get("page"):
        place.append(f"p. {item['page']}")
    if item.get("key"):
        step = f"/{item['step']}" if item.get("step") else ""
        place.append(f"#{item['key']}{step}")
    prefix = f"[{', '.join(place)}] " if place else ""
    return f"{prefix}{item['message']}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project folder or path to index.html")
    level = parser.add_mutually_exclusive_group()
    level.add_argument("--static-only", action="store_true", help="Contracts only: sources and resources, no browser")
    level.add_argument("--full", action="store_true", help="Everything: also PDF; for a deck also motion, video, panel, light theme and deep links")
    parser.add_argument("--resource-root", type=Path, help="Root of the standalone package when the catalog sits deeper than the assets")
    parser.add_argument("--shots", type=Path, help="Deck: save a screenshot of each state to this folder")
    parser.add_argument("--report", type=Path, help="Deck: save the JSON report of the state pass")
    args = parser.parse_args()

    try:
        run_checks(args)
    except AssertionError as failure:
        raise SystemExit(f"Error: {failure}") from None


def run_checks(args: argparse.Namespace) -> None:
    index = project_index(args.project)
    surface = check_static(index, args.resource_root)
    print(f"✓ static contracts: {surface}")
    if args.static_only:
        print(f"Done: contracts checked, browser skipped: {index}")
        return
    level = "full" if args.full else "render"
    if surface == "slides":
        report = check_deck(index, level, args.shots)
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("✓ Chromium: 1440, 390 and 320 px, theme and accessibility")
        line = f"✓ deck states: {len(report['pages'])} pages, {report['sources']} slides"
        if report["pdf"]:
            line += f", PDF {report['pdf']['steps']} and {report['pdf']['final']} pages"
        print(line)
    else:
        check_browser(index, surface, full=args.full)
        print("✓ Chromium: 1440, 390 and 320 px, theme, accessibility" + (" and PDF" if args.full else ""))
    if args.full:
        print(f"Done: Craft project is valid: {index}")
    else:
        print(f"Done: Craft project renders correctly: {index}. Before handing it over, run with --full")


if __name__ == "__main__":
    main()
