#!/usr/bin/env python3
"""Fast checks of Craft source contracts with minimal dependencies."""

from __future__ import annotations

import ast
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from audit_css import audit as audit_css
from lib import ASSETS, MANIFEST, ROOT, node, run

TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py"}
# output/ is a scratch area outside the repository; its content is not checked.
IGNORED_DIRS = {".git", ".claude", ".ralph", ".tmp", "output", "dist", "artifacts", "__pycache__"}
CATALOG_HTML = sorted((ROOT / "catalog").rglob("*.html"))
CANONICAL_INTERFACE_PAGES = [
    ROOT / "catalog/interfaces/foundations.html",
    ROOT / "catalog/interfaces/atoms.html",
    ROOT / "catalog/interfaces/molecules.html",
    ROOT / "catalog/interfaces/organisms.html",
]
CSS_FILES = [*ASSETS.rglob("*.css"), ROOT / "catalog/interfaces/catalog.css"]
HTML_FILES = [ROOT / path for surface in MANIFEST["surfaces"].values() for path in surface["entrypoints"]]
FRAGMENT_DEFINITIONS = [fragment for surface in MANIFEST["surfaces"].values() for fragment in surface.get("fragments", [])]
FRAGMENT_FILES = [ROOT / fragment["path"] for fragment in FRAGMENT_DEFINITIONS]
CHECKED_HTML = [*HTML_FILES, *CATALOG_HTML]
MARK_SELECTOR = re.compile(r"\.icon\b|-mark\b|-dot\b|-status\b|::before|::after|\bsvg\b")
LABEL_SELECTORS = {".tag"}
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CYRILLIC = re.compile(r"[\u0400-\u04ff]")
# An element with its own non-English lang, e.g. <p lang="ru">, may hold that language.
FOREIGN_LANG_BLOCK = re.compile(r'<(?!html\b)([a-z][a-z0-9]*)\b[^>]*\blang="(?!en\b)[^"]*"[^>]*>.*?</\1>', re.S | re.I)
LANGUAGE_SUFFIXES = TEXT_SUFFIXES | {".mjs", ".svg", ".yml", ".yaml", ".txt", ".sh"}
LANGUAGE_FILES = {"Makefile"}
RUSSIAN_GUIDE = ROOT / "references/russian.md"
RAW_COLOR = re.compile(r"(?<![\w-])(?:#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\([^)]*\))")


class LanguageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "html":
            self.lang = dict(attrs).get("lang")


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            self.assets.append(values["href"] or "")
        if tag in {"script", "img", "source", "video"} and values.get("src"):
            self.assets.append(values["src"] or "")


class HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.levels: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if re.fullmatch(r"h[1-6]", tag):
            self.levels.append(int(tag[1]))


def check_reading_routes() -> None:
    """An agent reads one route, not the whole skill, so each file and each route has a size limit."""
    config = MANIFEST["readingRoutes"]
    file_limit, route_limit = config["limits"]["fileChars"], config["limits"]["routeChars"]
    docs = [ROOT / "SKILL.md", *sorted((ROOT / "references").rglob("*.md"))]
    for path in docs:
        size = len(path.read_text(encoding="utf-8"))
        assert size <= file_limit, f"{path.relative_to(ROOT)}: {size} characters, over {file_limit}; split the reference by topic"
    covered: set[str] = set()
    for name, route in config["routes"].items():
        assert route[0] == "SKILL.md", f"route {name} must start with SKILL.md"
        reachable = {"SKILL.md"}
        for item in route:
            assert item in reachable, f"route {name}: no link to {item} from the files read before it"
            path = ROOT / item
            for target in re.findall(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
                reachable.add((path.parent / target).resolve().relative_to(ROOT).as_posix())
        size = sum(len((ROOT / item).read_text(encoding="utf-8")) for item in route)
        assert size <= route_limit, f"route {name}: {size} characters, over {route_limit}; make the routing narrower"
        covered.update(route)
    orphans = [path.relative_to(ROOT).as_posix() for path in docs if path.relative_to(ROOT).as_posix() not in covered]
    assert not orphans, f"references outside all reading routes: {', '.join(orphans)}"


def check_required() -> None:
    required = [
        ROOT / "SKILL.md",
        ROOT / "README.md",
        ROOT / "scripts/craft.json",
        ROOT / "references/identity.md",
        ROOT / "references/workflow.md",
        ROOT / "references/surfaces.md",
        ROOT / "references/extending.md",
        ROOT / "references/interfaces/design-language.md",
        ROOT / "references/interfaces/components.md",
        ROOT / "references/interfaces/atomic-design.md",
        ROOT / "references/interfaces/layout.md",
        ROOT / "references/slides/design-language.md",
        ROOT / "references/slides/authoring.md",
        ROOT / "references/slides/selection.md",
        ROOT / "references/slides/charts.md",
        ASSETS / "shared/tokens.css",
        ASSETS / "interfaces/theme.css",
        ASSETS / "interfaces/theme.js",
        ASSETS / "interfaces/section-nav.js",
        ASSETS / "interfaces/copy.js",
        ASSETS / "interfaces/dialog.js",
        ASSETS / "interfaces/tabs.js",
        ROOT / "catalog/interfaces/catalog.css",
        ROOT / "catalog/interfaces/catalog.js",
        ASSETS / "slides/base.css",
        ASSETS / "slides/theme.css",
        ASSETS / "slides/deck.js",
        *HTML_FILES,
        *CATALOG_HTML,
        *FRAGMENT_FILES,
    ]
    for path in required:
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"

    component_tags: list[tuple[Path, str]] = []
    for path in CANONICAL_INTERFACE_PAGES:
        html = path.read_text(encoding="utf-8")
        component_tags.extend((path, tag) for tag in re.findall(r'<section[^>]+data-component-doc="[^"]+"[^>]*>', html))
    expected_components = len(MANIFEST["surfaces"]["interface"]["components"])
    assert len(component_tags) == expected_components, f"expected {expected_components} components in the atomic registry, found {len(component_tags)}"
    for path, tag in component_tags:
        level = re.search(r'data-atomic-level="([^"]+)"', tag)
        assert level and level.group(1) in {"atom", "molecule", "organism"}, (
            f"a component in {path.relative_to(ROOT)} has no valid data-atomic-level"
        )

    forbidden = [ROOT / "docs/cases", ROOT / "examples", ASSETS / "interfaces/specimen.html", ASSETS / "slides/specimen.html"]
    for path in forbidden:
        assert not path.exists(), f"public examples and catalogs do not belong in the repository: {path.relative_to(ROOT)}"
    fonts = list((ASSETS / "shared/fonts").glob("*.woff2"))
    expected = MANIFEST["requirements"]["fontFiles"]
    assert len(fonts) == expected, f"expected {expected} local font files, found {len(fonts)}"

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    description = re.search(r'^description:\s*"([^"]+)"', skill, re.MULTILINE)
    assert description and len(description.group(1)) <= 57, "the skill description gets cut off in the index"
    assert "references/slides/selection.md" in skill, "the skill route must link to choosing a layout"
    assert "references/slides/charts.md" in skill, "charts must be a separate branch of the skill"
    check_reading_routes()
    assert len(skill.splitlines()) <= 60, "SKILL.md must stay a short router"
    assert "references/workflow.md" in skill and "## Requirements" not in skill, "process and requirements belong in the references"
    extending = (ROOT / "references/extending.md").read_text(encoding="utf-8")
    assert "## One-off composition" in extending and "## New supported format" in extending, "extending.md does not separate the two ways to extend Craft"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for package in ("craft-interface.zip", "craft-slides.zip", "craft-complete.zip"):
        assert package in readme, f"README does not describe {package}"
    assert "sha256sum -c SHA256SUMS" in readme, "README does not describe how to verify release archives"
    case_study = ROOT / "catalog/slides/case-study.html"
    assert case_study.is_file() and "catalog/slides/case-study.html" in readme, "README does not link the mini deck"
    case_html = case_study.read_text(encoding="utf-8")
    assert len(re.findall(r'<section class="slide\b', case_html)) == 8, "the mini deck must have eight source slides"
    interface, slides = MANIFEST["surfaces"]["interface"], MANIFEST["surfaces"]["slides"]
    # Each fact sits in its own metric next to its label, so a stray matching
    # number elsewhere on the page does not pass for a stale fact.
    facts = {
        "interface components": len(interface["components"]),
        "interface fragments": len(interface["fragments"]),
        "canonical slide fragments": len(slides["fragments"]),
        "catalog pages": slides["catalogPages"],
    }
    for label, value in facts.items():
        assert re.search(rf'>{value}</div><div class="k">{label}<|{value} {label}', case_html), f"mini deck fact is stale or missing: {value} {label}"
    assert MANIFEST["version"] in case_html, f"mini deck does not show version {MANIFEST['version']}"


def check_assets() -> None:
    for path in CHECKED_HTML:
        parser = AssetParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for value in parser.assets:
            parts = urlsplit(value)
            assert not parts.scheme and not parts.netloc, f"external runtime resource {value} in {path.relative_to(ROOT)}"
            target = (path.parent / unquote(parts.path)).resolve()
            assert target.is_file(), f"broken resource {value} in {path.relative_to(ROOT)}"


def check_tokens() -> None:
    tokens = ASSETS / "shared/tokens.css"
    for path in CSS_FILES:
        if path == tokens:
            continue
        match = RAW_COLOR.search(path.read_text(encoding="utf-8"))
        assert not match, f"raw color {match.group(0)} outside assets/shared/tokens.css in {path.relative_to(ROOT)}"

    css = "\n".join(path.read_text(encoding="utf-8") for path in CSS_FILES)
    definitions = set(re.findall(r"(--[\w-]+)\s*:", css))
    usages = set(re.findall(r"var\((--[\w-]+)", css))
    dynamic = set(MANIFEST["dynamicCssProperties"])
    unknown = usages - definitions - dynamic
    assert not unknown, f"undefined CSS properties: {', '.join(sorted(unknown))}"

    light_roles = {
        "--craft-light-bg", "--craft-light-surface", "--craft-light-sunken",
        "--craft-light-line", "--craft-light-line-strong", "--craft-light-text",
        "--craft-light-text-body", "--craft-light-muted", "--craft-light-accent",
        "--craft-light-accent-mark", "--craft-light-accent-fill",
        "--craft-light-accent-fill-hover", "--craft-light-accent-tint",
        "--craft-light-data-blue", "--craft-light-data-amber", "--craft-light-data-green",
    }
    missing_light = light_roles - definitions
    assert not missing_light, f"incomplete light theme: {', '.join(sorted(missing_light))}"


def check_css_api() -> None:
    report = audit_css()
    groups = report["groups"]
    assert not groups["catalogOnly"], f"classes used only by the catalog: {', '.join(groups['catalogOnly'])}"
    assert not groups["unused"], f"unused classes: {', '.join(groups['unused'])}"


def check_borders() -> None:
    adjacent = ({"top", "right"}, {"right", "bottom"}, {"bottom", "left"}, {"left", "top"})
    opposite = ({"top", "bottom"}, {"left", "right"})
    for path in CSS_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            directions = set(re.findall(r"border-(top|right|bottom|left)\s*:", match.group(2)))
            selector = match.group(1).strip()
            assert len(directions) < 3, f"three-sided border in {path.relative_to(ROOT)}: {selector}"
            assert not any(pair <= directions for pair in adjacent), f"corner border in {path.relative_to(ROOT)}: {selector}"
            assert not any(pair <= directions for pair in opposite), f"two directional borders can merge in {path.relative_to(ROOT)}: {selector}"


def check_catalog_grid() -> None:
    """The catalog grid draws borders only around items that exist."""
    css = (ROOT / "catalog/interfaces/catalog.css").read_text(encoding="utf-8")
    container = re.search(r"\.component-index\s*\{([^{}]+)\}", css)
    item = re.search(r"\.component-index a\s*\{([^{}]+)\}", css)
    assert container and item, "catalog grid rules not found"
    assert not re.search(r"\bborder\s*:", container.group(1)), "the component-index container draws a border around empty cells"
    assert "outline: 1px solid var(--line)" in item.group(1), "component-index cells do not draw their own border"
    assert not re.search(r"\.component-index(?:::[\w-]+|[^,{]*::[\w-]+)", css), "a component-index pseudo-element fakes empty cells"
    assert not re.search(r"\.component-index[^{}]*\{[^{}]*(?:linear|radial)-gradient", css), "a component-index gradient fakes table lines"


def check_state_marks() -> None:
    """A signal color paints the graphic mark, not the state text.

    There is one exception: a bordered label. The border and the text inside it
    are one detail, so the text takes the border color."""
    signal = re.compile(r"(?<![\w-])color\s*:\s*var\(--(ok|warn|error|status|data-[a-z]+)\b")
    for path in CSS_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            selector = match.group(1).split("*/")[-1].strip()
            if not signal.search(match.group(2)):
                continue
            assert MARK_SELECTOR.search(selector) or selector in LABEL_SELECTORS, (
                f"signal color paints text instead of a mark in {path.relative_to(ROOT)}: {selector}"
            )


def check_control_states() -> None:
    """Interactive controls tell hover apart from a persistent selection.

    A page-wide rule draws the visible focus. Hover cannot stand in for a
    persistent state, which has to stay after the pointer leaves and be visible
    with a keyboard or a touch screen. Static components are not listed."""
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    selectors = [match.group(1).strip() for match in re.finditer(r"([^{}]+)\{[^{}]*\}", theme)]
    marks = {
        "hover": (":hover",),
        "disabled": (":disabled", "[disabled]", ":has(input:disabled)"),
        "persistent": (":checked", ":indeterminate", "[aria-pressed", "[aria-selected", "[aria-current", "[aria-sort", "[open]"),
    }
    controls = {
        ".button": ("hover", "disabled", "persistent"),
        ".button--quiet": ("hover",),
        'input:not([type="checkbox"]': ("hover",),
        "textarea": ("hover", "disabled"),
        ".select-control select": ("hover", "disabled"),
        'input[type="checkbox"]': ("hover", "disabled", "persistent"),
        'input[type="radio"]': ("hover", "disabled", "persistent"),
        ".switch": ("hover", "disabled", "persistent"),
        ".range": ("hover", "disabled"),
        ".segmented": ("hover", "persistent"),
        ".tablist button": ("hover", "disabled", "persistent"),
        ".pagination__page": ("hover", "persistent"),
        ".breadcrumbs": ("hover", "persistent"),
        ".disclosure": ("hover", "persistent"),
        ".data-table__sort": ("hover", "persistent"),
        ".data-table tbody tr[data-interactive]": ("hover", "persistent"),
        ".section-nav__links a": ("hover", "persistent"),
        ".tag": ("hover",),
    }
    for control, required in controls.items():
        for state in required:
            found = any(
                control in selector and any(mark in selector for mark in marks[state])
                for selector in selectors
            )
            assert found, f"control {control} has no {state} state"

    assert ".data-table tbody tr:hover" not in theme, "a static table row must not look interactive"



def check_hover_paint() -> None:
    """Hover paints the text, it does not add a fill.

    One rule for the whole system: under the pointer the label turns accent and
    the background stays the same. A fill marks a persistent selection, and if
    hover uses it too, the two states look the same. Only controls whose label
    sits on an accent fill, or that have no text at all, change the fill on hover."""
    filled = (".button--primary", ".switch input", ".range")
    for path in (ASSETS / "interfaces/theme.css", ROOT / "catalog/interfaces/catalog.css"):
        css = path.read_text(encoding="utf-8")
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            selector = selector.strip()
            if ":hover" not in selector or not re.search(r"\bbackground(-color)?\s*:", body):
                continue
            assert any(control in selector for control in filled), (
                f"hover adds a fill in {path.relative_to(ROOT)}: {selector}"
            )
        # A control with its own border strengthens the border and the arrow on
        # hover, because the accent there belongs to focus. Other controls must
        # not dim the label to --text. Hover adds paint, it never removes it.
        bordered = (".select-control", ".field", ".switch", "input", "textarea")
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            selector = selector.strip()
            if ":hover" not in selector or "color: var(--text)" not in body:
                continue
            assert any(control in selector for control in bordered), (
                f"hover removes the accent instead of adding it "
                f"in {path.relative_to(ROOT)}: {selector}"
            )

def check_accessibility_contract() -> None:
    for path in CHECKED_HTML:
        if not path.is_file():
            continue
        parser = HeadingParser()
        parser.feed(path.read_text(encoding="utf-8"))
        assert parser.levels.count(1) == 1, f"{path.relative_to(ROOT)} needs exactly one h1"
        for previous, current in zip(parser.levels, parser.levels[1:]):
            assert current <= previous + 1, f"{path.relative_to(ROOT)} skips a heading level: h{previous} to h{current}"

    for surface in ("interfaces", "slides"):
        css = "\n".join(path.read_text(encoding="utf-8") for path in (ASSETS / surface).glob("*.css"))
        assert ":focus-visible" in css, f"format {surface} has no visible focus rule"
        assert "@media print" in css, f"format {surface} has no print rules"
    assert "prefers-reduced-motion" in (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8"), "the interface has no reduced motion rule"

    # A deck has one motion policy. deck.js reads the system setting in auto
    # mode and sets :root[data-motion-state], and CSS looks only at that
    # attribute. A media query of its own in the theme would turn off planned
    # animation again on someone else's computer.
    for path in (ASSETS / "slides").glob("*.css"):
        assert "prefers-reduced-motion" not in CSS_COMMENT_RE.sub("", path.read_text(encoding="utf-8")), f"prefers-reduced-motion in {path.relative_to(ROOT)}: data-motion-state decides deck motion"
    deck_js = (ASSETS / "slides/deck.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in deck_js and "motionState" in deck_js, "deck.js does not apply the motion policy"
    assert ':root[data-motion-state="off"] *' in (ASSETS / "slides/base.css").read_text(encoding="utf-8"), "base.css does not turn off motion by the deck policy"

    interface_theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    assert re.search(r"\.select-control select[^,{]*:not\(:disabled\)[^,{]*:hover", interface_theme), "select has no hover state"
    assert ".select-control:has(select:focus-visible)" in interface_theme, "the select arrow does not react to focus"
    assert ".sr-only" in interface_theme, "the visually hidden text utility is not defined"
    assert ".data-table--records td::before" in interface_theme, "the records table has no mobile labels"
    data_catalog = (ROOT / "catalog/interfaces/organisms.html").read_text(encoding="utf-8")
    record_table = re.search(r'<table class="data-table data-table--records">(.*?)</table>', data_catalog, re.DOTALL)
    assert record_table and all("data-label=" in tag for tag in re.findall(r"<td[^>]*>", record_table.group(1))), "mobile table cells do not repeat their headers in data-label"

    slide_theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    sizes = [float(value) for value in re.findall(r"font(?:-size)?\s*:[^;{}]*?([0-9.]+)cqw", slide_theme)]
    assert sizes and min(sizes) >= 1.4, f"slide content text is smaller than 1.4cqw: {min(sizes)}"

    slide_base = (ASSETS / "slides/base.css").read_text(encoding="utf-8")
    assert "--control-size: 2.5rem" in slide_base and "width: 2.5rem; height: 2.5rem" in slide_base, "deck control targets are smaller than 40 px"
    assert "@media (hover: none), (pointer: coarse)" in slide_base, "no touch mode for deck controls"
    assert ".help-reveal { opacity: 1; pointer-events: auto; }" in slide_base, "the deck control button is hidden on touch screens"


def check_spacing_scale() -> None:
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    expected = {1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 7: 32}
    for index, value in expected.items():
        assert re.search(rf"--space-{index}:\s*{value}px\s*;", theme), f"missing --space-{index}: {value}px"

    catalog = (ROOT / MANIFEST["surfaces"]["interface"]["testPage"]).read_text(encoding="utf-8")
    for index in expected:
        assert f"var(--space-{index})" in catalog, f"the catalog does not show --space-{index}"


def check_fragment_manifest() -> None:
    allowed_kinds = {"text", "html", "id", "number", "token"}
    for surface_id, surface in MANIFEST["surfaces"].items():
        target = surface.get("fragmentTarget")
        assert isinstance(target, str) and target, f"no fragmentTarget for {surface_id}"
        fragments = surface.get("fragments", [])
        ids = [fragment.get("id") for fragment in fragments]
        assert len(ids) == len(set(ids)) and all(ids), f"fragment ids of {surface_id} are not unique"
        for fragment in fragments:
            assert set(fragment) == {"id", "path", "purpose", "placeholders", "dependencies"}, f"incomplete fragment entry {fragment.get('id')}"
            path = ROOT / fragment["path"]
            assert path.is_file(), f"fragment not found: {fragment['path']}"
            assert isinstance(fragment["purpose"], str) and fragment["purpose"].strip(), f"no purpose for {fragment['id']}"
            placeholders = fragment["placeholders"]
            assert isinstance(placeholders, dict) and placeholders, f"no placeholders described for {fragment['id']}"
            assert set(placeholders.values()) <= allowed_kinds, f"unknown placeholder kind in {fragment['id']}"
            actual = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", path.read_text(encoding="utf-8")))
            assert actual == set(placeholders), f"placeholder metadata does not match {fragment['path']}"
            for dependency in fragment["dependencies"]:
                assert (ROOT / dependency).is_file(), f"dependency {dependency} not found for {fragment['id']}"
            if surface_id == "slides":
                html = path.read_text(encoding="utf-8")
                layouts = re.findall(r'data-slide-layout="([a-z-]+)"', html)
                assert layouts == [fragment["id"]], f"id and layout differ in {fragment['path']}"
        if surface_id == "slides":
            guidance = surface.get("layoutGuidance", {})
            assert set(guidance) == set(surface["catalogLayouts"]), "layout guidance does not cover the catalog layouts"
            guidance_fields = {"job", "useWhen", "avoidWhen", "variable", "fixed", "slots", "reveal", "alternatives", "signature"}
            fragments_by_id = {fragment["id"]: fragment for fragment in fragments}
            for layout_id, item in guidance.items():
                assert set(item) == guidance_fields, f"incomplete layout guidance for {layout_id}"
                assert isinstance(item["job"], str) and item["job"].strip(), f"no job described for {layout_id}"
                for field in ("useWhen", "avoidWhen", "variable", "fixed"):
                    assert isinstance(item[field], list) and all(isinstance(value, str) and value.strip() for value in item[field]), f"field {field} is empty for {layout_id}"
                assert isinstance(item["slots"], dict) and item["slots"], f"no slots described for {layout_id}"
                assert all(isinstance(value, str) and value.strip() for value in item["slots"].values()), f"empty slot description for {layout_id}"
                if layout_id in fragments_by_id:
                    assert set(item["slots"]) == set(fragments_by_id[layout_id]["placeholders"]), f"slot descriptions do not match placeholders for {layout_id}"
                assert set(item["reveal"]) == {"default", "guidance"}, f"no reveal described for {layout_id}"
                assert item["reveal"]["default"] in {"none", "optional"}, f"unknown reveal for {layout_id}"
                assert isinstance(item["alternatives"], dict) and item["alternatives"], f"no alternatives for {layout_id}"


def check_interface_components() -> None:
    surface = MANIFEST["surfaces"]["interface"]
    assert "componentCategories" not in surface, "the old category hierarchy is still in the registry"
    components = surface.get("components", [])
    foundations = surface.get("foundations", [])
    ids = [item.get("id") for item in [*foundations, *components]]
    assert ids and len(ids) == len(set(ids)), "interface system items are not unique"
    component_fields = {"id", "title", "level", "kind", "source", "rootClass", "dependencies", "summary"}
    foundation_fields = component_fields - {"level"}
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    for item in foundations:
        assert set(item) == foundation_fields and item["kind"] in {"foundation", "primitive", "fragment"}, f"incomplete Foundation entry {item.get('id')}"
    for item in components:
        assert set(item) == component_fields, f"incomplete component entry {item.get('id')}"
        assert item["level"] in {"atom", "molecule", "organism"}, f"unknown level for {item['id']}"
        assert item["kind"] in {"primitive", "fragment"}, f"unknown component kind {item['id']}"
    for item in [*foundations, *components]:
        assert item["title"].strip() and item["summary"].strip(), f"no description for {item['id']}"
        assert (ROOT / item["source"]).is_file(), f"source not found: {item['source']}"
        for dependency in item["dependencies"]:
            assert (ROOT / dependency).is_file(), f"dependency {dependency} not found for {item['id']}"
        if item["rootClass"]:
            assert re.search(rf"\.{re.escape(item['rootClass'])}(?![\w-])", theme), f"root class {item['rootClass']} is not defined"
    fragment_ids = {fragment["id"] for fragment in surface["fragments"]}
    registered_fragments = {item["id"] for item in [*foundations, *components] if item["kind"] == "fragment"}
    assert registered_fragments == fragment_ids, "the registry does not cover the interface fragments"


def check_interface_documentation() -> None:
    directory = ROOT / "catalog/interfaces"
    surface = MANIFEST["surfaces"]["interface"]
    expected_ids = {component["id"] for component in surface["components"]}
    expected_foundations = {item["id"] for item in surface["foundations"]}
    level_pages = {
        "foundations.html": ("Foundation", None),
        "atoms.html": ("Atoms", "atom"),
        "molecules.html": ("Molecules", "molecule"),
        "organisms.html": ("Organisms", "organism"),
        "templates.html": ("Templates", None),
        "pages.html": ("Pages", None),
    }
    expected_navigation = list(level_pages)
    documented: set[str] = set()

    for filename, (_, expected_level) in level_pages.items():
        path = directory / filename
        assert path.is_file(), f"missing level page {path.relative_to(ROOT)}"
        text = path.read_text(encoding="utf-8")
        primary = re.search(r'<div class="system-links">(.*?)</div>', text, re.DOTALL)
        assert primary and re.findall(r'href="([^"]+)"', primary.group(1)) == expected_navigation, f"navigation differs in {path.name}"
        current = re.findall(r'<a\b[^>]*aria-current="true"[^>]*>([^<]+)</a>', primary.group(1))
        assert current == [level_pages[filename][0]], f"wrong current catalog level in {path.name}"
        tags = re.findall(r'<section[^>]+data-component-doc="[^"]+"[^>]*>', text)
        actual = [re.search(r'data-component-doc="([^"]+)"', tag).group(1) for tag in tags]
        if expected_level:
            for tag in tags:
                level = re.search(r'data-atomic-level="([^"]+)"', tag)
                assert level and level.group(1) == expected_level, f"a component of another level on {path.name}"
            assert len(actual) == text.count('data-preview>'), f"not every component on {path.name} has a preview"
            assert len(actual) == text.count("data-preview-code"), f"not every component on {path.name} has code"
            assert len(actual) == text.count('class="component-api"'), f"not every component on {path.name} has an API reference"
        duplicates = documented & set(actual)
        assert not duplicates, f"components documented on several levels: {', '.join(sorted(duplicates))}"
        documented.update(actual)

    listing = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    syntax_roles = {
        ".syntax-tag, .syntax-keyword { color: var(--accent)": "element names in listings do not match slide highlighting",
        ".syntax-attr, .syntax-string { color: var(--craft-code-gold)": "attributes and strings do not use gold",
        ".syntax-doctype, .syntax-comment { color: var(--muted)": "doctype and comments in listings are not muted",
    }
    for rule, message in syntax_roles.items():
        assert rule in listing, message

    assert documented == expected_ids, "level pages do not cover the component registry"
    foundation_page = (directory / "foundations.html").read_text(encoding="utf-8")
    actual_foundations = set(re.findall(r'data-foundation-doc="([a-z-]+)"', foundation_page))
    assert actual_foundations == expected_foundations, "Foundation does not match the registry"

    pages = (directory / "pages.html").read_text(encoding="utf-8")
    recipe_ids = re.findall(r'data-recipe-doc="([a-z-]+)"', pages)
    assert recipe_ids == ["filtered-table", "master-detail", "validated-form"], "recipes on pages.html are not in the expected order"
    assert len(recipe_ids) == pages.count("data-preview-code"), "a recipe on pages.html has no live example and code"
    getting_started = (directory / "getting-started.html").read_text(encoding="utf-8")
    assert re.findall(r'data-recipe-doc="([a-z-]+)"', getting_started) == ["first-page"], "getting-started.html does not contain the first build"

    index = (directory / "index.html").read_text(encoding="utf-8")
    index_levels = re.findall(r'<div class="component-index[^"]*">(.*?)</div>', index, re.DOTALL)
    assert len(index_levels) == 1 and re.findall(r'href="([a-z-]+\.html)"', index_levels[0]) == list(level_pages), "the index page repeats the content of level pages"

    human_pages = [directory / "index.html", directory / "getting-started.html", *(directory / name for name in level_pages)]
    for path in human_pages:
        text = path.read_text(encoding="utf-8")
        primary = re.search(r'<div class="system-links">(.*?)</div>', text, re.DOTALL)
        assert primary and re.findall(r'href="([^"]+)"', primary.group(1)) == expected_navigation, f"primary navigation differs in {path.name}"
        if path.name == "index.html":
            assert re.search(r'<a class="system-name" href="index.html" aria-current="page">Craft</a>', text), "the Craft header does not mark the index page as current"
        assert 'href="sheet.html"' not in text, f"the test sheet is linked from user navigation in {path.name}"

    short_version = ".".join(MANIFEST["version"].split(".")[:2])
    for path in sorted(directory.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "system-version" in text:
            assert f'<span class="system-version">{short_version}</span>' in text, f"outdated version in {path.relative_to(ROOT)}"
        for href in re.findall(r'<a\b[^>]*href="([^"]+)"', text):
            parts = urlsplit(href)
            if parts.scheme or not parts.path:
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            assert target.is_file() and ROOT in target.parents, f"broken link {href} in {path.relative_to(ROOT)}"
            if parts.fragment:
                target_text = target.read_text(encoding="utf-8")
                assert re.search(rf'\bid="{re.escape(parts.fragment)}"', target_text), f"missing anchor {href} in {path.relative_to(ROOT)}"


def check_interface_patterns() -> None:
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    starter = (ASSETS / "interfaces/starter-index.html").read_text(encoding="utf-8")
    bare = (ASSETS / "interfaces/starter-bare.html").read_text(encoding="utf-8")
    fragments = {path.name: path.read_text(encoding="utf-8") for path in FRAGMENT_FILES if "interfaces" in path.parts}
    essential = {"page-head.html", "workspace-head.html", "metric-strip.html", "section.html", "split-workspace.html", "data-table.html", "empty-state.html", "section-nav.html"}
    assert essential <= set(fragments), "the base set of interface fragments is incomplete"
    assert "@page { margin: 8mm 14mm; }" in theme, "safe print margins are not set"
    assert ".section { break-inside: auto; }" in theme, "a long section cannot flow across pages"
    assert 'data-craft-layout="interface"' in starter, "the starter does not declare the interface layout"
    assert 'id="craft-content"' in starter, "the starter has no empty content area"
    assert "scoreboard" not in starter and "workbench" not in starter and "document-band" not in starter, "the starter forces a subject-specific composition"
    assert "scroll-region" in fragments["split-workspace.html"] and 'tabindex="0"' in fragments["split-workspace.html"], "the workspace is not reachable from the keyboard"
    assert "data-section-nav" in fragments["section-nav.html"], "the navigation fragment does not use the shared mechanics"
    assert "<footer" not in starter, "the starter has a decorative footer"
    assert 'data-craft-shell="app"' in starter and "data-theme-toggle" in starter, "the shell starter does not declare the shell or lost the theme toggle"
    assert 'data-craft-layout="interface"' in bare and 'id="craft-content"' in bare, "the bare starter does not declare the interface layout"
    assert "data-craft-shell" not in bare and "data-theme-toggle" not in bare and "workspace-head" not in bare, "the bare starter forces a shell"


def check_slide_layouts() -> None:
    registered = set(MANIFEST["surfaces"]["slides"].get("layouts", []))
    assert registered, "craft.json registers no slide layouts"
    fragments = [path.read_text(encoding="utf-8") for path in FRAGMENT_FILES if "slides" in path.parts]
    used = {value for html in fragments for value in re.findall(r'data-slide-layout="([a-z-]+)"', html)}
    unknown = used - registered
    missing = registered - used
    assert not unknown, f"unknown slide layouts: {', '.join(sorted(unknown))}"
    assert not missing, f"layouts without fragments: {', '.join(sorted(missing))}"
    for path in (path for path in FRAGMENT_FILES if "slides" in path.parts):
        html = path.read_text(encoding="utf-8")
        assert len(re.findall(r'<section class="slide\b', html)) == 1, f"{path.relative_to(ROOT)} must contain one slide"
        assert len(re.findall(r'data-slide-layout="[a-z-]+"', html)) == 1, f"{path.relative_to(ROOT)} does not declare a layout"
    starter = (ASSETS / "slides/starter/index.html").read_text(encoding="utf-8")
    assert re.findall(r'data-slide-layout="([a-z-]+)"', starter) == ["title"], "the starter deck must contain only the title slide"
    theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    syntax_roles = {
        ".code .hljs-type { color: var(--accent)": "keywords do not use the accent",
        ".code .hljs-name,": "element names are not accent colored",
        ".code .hljs-template-variable { color: var(--craft-code-gold)": "strings do not use gold",
        ".code .hljs-bullet { color: var(--craft-code-blue)": "numbers do not use blue",
    }
    for rule, message in syntax_roles.items():
        assert rule in theme, message
    # Gecko silently ignores a unitless calc in SVG geometry. The ring share
    # becomes a full ring, and the slide shows wrong data.
    assert "stroke-dasharray: calc(var(--value) * 1px" in theme, "the ring share is computed without units again"
    assert "stroke-dashoffset" not in theme, "the share start shifts the stroke instead of rotating, which Gecko loses"

    catalog_definition = MANIFEST["surfaces"]["slides"]
    catalog = (ROOT / catalog_definition["catalog"]).read_text(encoding="utf-8")
    catalog_layouts = set(re.findall(r'data-slide-layout="([a-z-]+)"', catalog))
    assert catalog_layouts == set(catalog_definition["catalogLayouts"]), "the catalog layout registry does not match the HTML"
    section_tags = re.findall(r'<section class="slide\b[^>]*>', catalog)
    examples = catalog_definition.get("catalogExamples", [])
    example_fields = {"id", "name", "layout", "job", "useWhen", "variable"}
    assert len(examples) == len(section_tags), "not every catalog source slide is described in the registry"
    assert len({item.get("id") for item in examples}) == len(examples), "catalog example ids are not unique"
    for item, tag in zip(examples, section_tags):
        assert set(item) == example_fields, f"incomplete example description {item.get('id')}"
        assert all(isinstance(item[field], str) and item[field].strip() for field in example_fields), f"empty example description {item.get('id')}"
        assert re.search(rf'data-catalog-example="{re.escape(item["id"])}"', tag), f"description {item['id']} does not match the catalog order"
        layout = re.search(r'data-slide-layout="([a-z-]+)"', tag)
        assert layout and layout.group(1) == item["layout"], f"layout of example {item['id']} does not match the HTML"
    chart_rows = re.findall(r'<div class="chart-row[^"]*"><span>[^<]+</span><strong data-count>[^<]+</strong>', catalog)
    assert len(chart_rows) == catalog.count('class="chart-row'), "not every horizontal chart row has a labeled, animated value"
    source_pages = len(re.findall(r'<section class="slide\b', catalog))
    fragment_count = len(re.findall(r'<[^>]+\bclass="[^"]*\bfrag\b[^"]*"', catalog))
    assert catalog_definition["catalogPages"] == source_pages + fragment_count, "the catalog page count does not match the reveal steps"
    flow_example = re.search(r'<section[^>]+data-catalog-example="flow"[^>]*>(.*?)</section>', catalog, re.DOTALL)
    assert flow_example and "flow-node--accent" not in flow_example.group(1), "the catalog overview flow must not force an accent node"
    chart_example = re.search(r'<section[^>]+data-catalog-example="bar-chart-finding"[^>]*>(.*?)</section>', catalog, re.DOTALL)
    assert chart_example and 'class="bar-chart"' in chart_example.group(1), "the chart must be visible before the finding is revealed"
    assert catalog_definition["catalogPages"] > source_pages, "the catalog does not test step reveal"
    assert catalog_definition["catalogPrintPages"] == catalog_definition["catalogPages"], "the PDF must contain every screen page"

    base = (ASSETS / "slides/base.css").read_text(encoding="utf-8")
    deck = (ASSETS / "slides/deck.js").read_text(encoding="utf-8")
    print_contracts = {
        "@page { size: 320mm 180mm; margin: 0; }": "slide printing lost the fixed 16:9 sheet",
        ".slide-canvas {\n  position: relative;\n  width: 100%;\n  height: 100%;": "the slide canvas can get clipped in Zen again",
        "html, body, .deck, .slides { height: 100% !important; }": "Zen will move the end of a slide to its own sheet again",
        ".slide[data-print-page]:last-child": "Firefox will add an empty last sheet again",
    }
    for rule, message in print_contracts.items():
        assert rule in base, message
    assert "page.setAttribute('data-print-page', '');" in deck, "not every screen step is marked for print"
    assert "canvas.className = 'slide-canvas';" in deck, "the deck does not create a separate print layout canvas"


def check_content() -> None:
    allowed_templates = {
        ASSETS / "interfaces/starter-index.html": {"TITLE"},
        ASSETS / "interfaces/starter-bare.html": {"TITLE"},
        ASSETS / "slides/starter/index.html": {"TITLE"},
        ROOT / "scripts/scaffold.py": {"TITLE", "BYLINE"},
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES or IGNORED_DIRS & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        placeholders = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", text))
        allowed = placeholders if path in FRAGMENT_FILES else allowed_templates.get(path, set())
        assert placeholders <= allowed, f"unexpected placeholders in {path.relative_to(ROOT)}: {placeholders}"


def check_language() -> None:
    """Craft text is English: docs, visible page text, messages and comments.

    Cyrillic is allowed only inside an element that declares its own lang,
    such as a font coverage sample. Docs also keep plain punctuation: straight
    quotes and no em dashes, since agents copy their style into new pages."""
    assert MANIFEST.get("language") == "en", "craft.json must declare English"
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or IGNORED_DIRS & set(path.parts):
            continue
        if path.suffix not in LANGUAGE_SUFFIXES and path.name not in LANGUAGE_FILES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix in {".html", ".svg"}:
            text = FOREIGN_LANG_BLOCK.sub(lambda match: "\n" * match.group(0).count("\n"), text)
        if path == RUSSIAN_GUIDE:
            # The Russian guide keeps its samples: fixed slide words, labels and quotes.
            continue
        match = CYRILLIC.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            raise AssertionError(
                f"Cyrillic text in {path.relative_to(ROOT)}:{line}. Craft is written in English; "
                "wrap a deliberate sample in an element with its own lang attribute"
            )

    for path in [ROOT / "README.md", ROOT / "SKILL.md", *sorted((ROOT / "references").rglob("*.md"))]:
        if path == RUSSIAN_GUIDE:
            continue
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        marks = sorted(set(re.findall(r"[\u00ab\u00bb\u201c\u201d\u2014]", text)))
        assert not marks, f"use straight quotes and no em dashes in {path.relative_to(ROOT)}: {' '.join(marks)}"

    for path in CHECKED_HTML:
        parser = LanguageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        assert parser.lang == "en", f"{path.relative_to(ROOT)} must have lang=en"

    for path in sorted([*(ROOT / "scripts").glob("*.py"), *(ROOT / "tests").rglob("*.py")]):
        assert ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))), f"no module docstring in {path.relative_to(ROOT)}"

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "name: Craft checks" in workflow and "Install PDF and QR tools" in workflow, "CI job names are not in English"
    assert "Fast checks" in makefile and "Remove generated" in makefile, "make help is not in English"


def check_markdown_links() -> None:
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for value in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in value or value.startswith("mailto:"):
                continue
            target = (path.parent / value).resolve()
            assert target.exists(), f"broken Markdown link {value} in {path.relative_to(ROOT)}"


def check_javascript() -> None:
    paths = [path for path in [*ASSETS.rglob("*.js"), *(ROOT / "catalog").rglob("*.js"), *(ROOT / "scripts").glob("*.mjs"), *(ROOT / "tests").rglob("*.mjs")] if "vendor" not in path.parts]
    for path in paths:
        run(node(), "--check", path)


def main() -> None:
    checks = (
        check_required,
        check_assets,
        check_tokens,
        check_css_api,
        check_borders,
        check_catalog_grid,
        check_state_marks,
        check_control_states,
        check_hover_paint,
        check_accessibility_contract,
        check_spacing_scale,
        check_fragment_manifest,
        check_interface_components,
        check_interface_documentation,
        check_interface_patterns,
        check_slide_layouts,
        check_content,
        check_language,
        check_markdown_links,
        check_javascript,
    )
    labels = {
        check_required: "required files",
        check_assets: "resources",
        check_tokens: "tokens",
        check_css_api: "public CSS API",
        check_borders: "borders",
        check_catalog_grid: "catalog grid",
        check_state_marks: "state marks",
        check_control_states: "control states",
        check_hover_paint: "hover paint",
        check_accessibility_contract: "accessibility contract",
        check_spacing_scale: "spacing scale",
        check_fragment_manifest: "fragment metadata",
        check_interface_components: "component registry",
        check_interface_documentation: "component docs",
        check_interface_patterns: "interface patterns",
        check_slide_layouts: "slide layouts",
        check_content: "content",
        check_language: "English text",
        check_markdown_links: "Markdown links",
        check_javascript: "JavaScript",
    }
    for check in checks:
        check()
        print(f"✓ {labels[check]}")
    print("Done: Craft source contracts hold")


if __name__ == "__main__":
    main()
