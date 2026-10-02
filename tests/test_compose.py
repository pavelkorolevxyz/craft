#!/usr/bin/env python3
"""Checks safe composition of interface and slide fragments."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib import ROOT, scaffold, run

COMPOSE = ROOT / "scripts/compose.py"
CHECK_PROJECT = ROOT / "scripts/check_project.py"


def command(project: Path, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(COMPOSE), str(project), *args], cwd=ROOT, text=True, capture_output=True)
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, "the command should have failed"
    return result


def test_interface(root: Path) -> None:
    project = root / "interface"
    scaffold(project, "interface", "blank", "Composition check")
    index = project / "index.html"

    before = index.read_text(encoding="utf-8")
    available = command(project, "--list-fragments")
    assert "split-workspace:" in available.stdout and "flow:" not in available.stdout
    assert index.read_text(encoding="utf-8") == before
    preview = command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=<Heading>",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=<p>Contents</p>",
        "--dry-run",
    )
    assert "&lt;Heading&gt;" in preview.stdout and index.read_text(encoding="utf-8") == before

    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=<Heading>",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=<p>Contents</p>",
    )
    html = index.read_text(encoding="utf-8")
    assert 'id="alpha"' in html and "&lt;Heading&gt;" in html and "<p>Contents</p>" in html
    assert "{{" not in html

    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=alpha",
        "--set", "SECTION_TITLE=Repeat",
        "--set", "SECTION_SUMMARY=",
        "--html", "SECTION_CONTENT=",
        success=False,
    )
    command(
        project,
        "--fragment", "section",
        "--set", "SECTION_ID=beta",
        "--set", "SECTION_TITLE=Wrong mode",
        "--set", "SECTION_SUMMARY=",
        "--set", "SECTION_CONTENT=<p>Not allowed</p>",
        success=False,
    )

    (project / "section-nav.js").unlink()
    before_dry_run = {path.name: path.read_bytes() for path in project.iterdir() if path.is_file()}
    command(
        project,
        "--fragment", "section-nav",
        "--set", "NAV_LABEL=Sections",
        "--html", 'NAV_LINKS=<a href="#alpha">First</a>',
        "--dry-run",
    )
    after_dry_run = {path.name: path.read_bytes() for path in project.iterdir() if path.is_file()}
    assert after_dry_run == before_dry_run, "--dry-run changed project files"

    command(
        project,
        "--fragment", "section-nav",
        "--set", "NAV_LABEL=Sections",
        "--html", 'NAV_LINKS=<a href="#alpha">First</a>',
    )
    html = index.read_text(encoding="utf-8")
    assert (project / "section-nav.js").is_file()
    assert html.count('<script src="section-nav.js"></script>') == 1

    command(
        project,
        "--fragment", "tabs",
        "--set", "TABS_LABEL=Modes",
        "--html", 'TAB_BUTTONS=<button type="button" role="tab" id="tab-a" aria-controls="panel-a">First</button>',
        "--html", 'TAB_PANELS=<div role="tabpanel" id="panel-a" aria-labelledby="tab-a">Contents</div>',
    )
    html = index.read_text(encoding="utf-8")
    assert (project / "tabs.js").is_file()
    assert html.count('<script src="tabs.js"></script>') == 1
    run(sys.executable, CHECK_PROJECT, project)


def test_slides(root: Path) -> None:
    project = root / "slides"
    scaffold(project, "slides", "deck", "Composition check")
    available = command(project, "--list-fragments")
    assert len(available.stdout.splitlines()) == 15
    assert "comparison:" in available.stdout and "quote:" not in available.stdout
    unknown = command(project, "--fragment", "quote", "--list-placeholders", success=False)
    assert "Available:" in unknown.stderr and "comparison" in unknown.stderr
    command(project, "--list-fragments", "--list-placeholders", success=False)
    listing = command(project, "--fragment", "list", "--list-placeholders")
    assert "Job:" in listing.stdout and "Avoid when:" in listing.stdout
    assert "SLIDE_TITLE: text" in listing.stdout and "LIST_ITEMS: html" in listing.stdout
    assert "Fixed:" in listing.stdout and "all points are of one kind" in listing.stdout
    assert "references/slides/selection.md" in listing.stdout
    comparison = command(project, "--fragment", "comparison", "--list-placeholders")
    assert "shared criterion" in comparison.stdout and "two independent topics" in comparison.stdout
    flow = command(project, "--fragment", "flow", "--list-placeholders")
    assert "a central position does not earn an accent" in flow.stdout
    assert "the incoming link with the next node" in flow.stdout
    items = ("--fragment", "list", "--set", "SLIDE_TITLE=Structure", "--html", "LIST_ITEMS=<li>First</li><li>Second</li>")
    missing = command(project, *items, success=False)
    assert "--key" in missing.stderr, "slide without a stable key was accepted"
    invalid = command(project, *items, "--key", "Structure", success=False)
    assert "lowercase Latin" in invalid.stderr
    command(project, *items, "--key", "structure")
    duplicate = command(project, *items, "--key", "structure", success=False)
    assert "already taken" in duplicate.stderr
    index = project / "index.html"
    html = index.read_text(encoding="utf-8")
    assert html.count('<section class="slide') == 2 and 'data-slide-layout="list"' in html
    assert 'data-slide-layout="list" data-key="structure"' in html, "key not written to the source slide"

    # The first item may appear with the heading. The rest are revealed.
    mixed = html.replace("<li>Second</li>", '<li class="frag">Second</li>')
    index.write_text(mixed, encoding="utf-8")
    run(sys.executable, CHECK_PROJECT, project)

    # A dependency from a nested format folder goes to the same subfolder, not the project root.
    values = ["--set", "SLIDE_TITLE=Code", "--set", "CODE_LANGUAGE=python", "--set", "HIGHLIGHT_LINES=1",
              "--set", "CODE=print(1)", "--set", "FINDING=Takeaway"]
    command(project, "--fragment", "code", *values, "--key", "code")
    assert not (project / "highlight.min.js").exists(), "highlighting was copied to the project root"
    assert index.read_text(encoding="utf-8").count("highlight.min.js") == 1


def test_cover(root: Path) -> None:
    project = root / "cover"
    run(sys.executable, ROOT / "scripts/scaffold.py", project, "--surface", "slides", "--title", "Talk", "--author", "Pavel Korolev")
    html = (project / "index.html").read_text(encoding="utf-8")
    assert 'data-slide-layout="cover" data-key="cover"' in html and "s-title-card" not in html
    assert '<p class="byline">Pavel Korolev</p>' in html and '<h1 class="type-hero">Talk</h1>' in html
    run(sys.executable, CHECK_PROJECT, project)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="craft-compose-") as directory:
        root = Path(directory)
        test_interface(root)
        test_slides(root)
        test_cover(root)
    print("Done: safe fragment composition checked")


if __name__ == "__main__":
    main()
