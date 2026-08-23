#!/usr/bin/env python3
"""Быстрые проверки контрактов исходников Craft с минимумом зависимостей."""

from __future__ import annotations

import ast
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from audit_css import audit as audit_css
from lib import ASSETS, MANIFEST, ROOT, node, run

TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py"}
# output/ — черновая песочница вне репозитория, её содержимое не проверяется.
IGNORED_DIRS = {".git", ".ralph", "output", "dist", "artifacts", "__pycache__"}
CATALOG_HTML = sorted((ROOT / "catalog").rglob("*.html"))
CSS_FILES = [*ASSETS.rglob("*.css"), ROOT / "catalog/interfaces/catalog.css"]
HTML_FILES = [ROOT / path for surface in MANIFEST["surfaces"].values() for path in surface["entrypoints"]]
FRAGMENT_DEFINITIONS = [fragment for surface in MANIFEST["surfaces"].values() for fragment in surface.get("fragments", [])]
FRAGMENT_FILES = [ROOT / fragment["path"] for fragment in FRAGMENT_DEFINITIONS]
CHECKED_HTML = [*HTML_FILES, *CATALOG_HTML]
MARK_SELECTOR = re.compile(r"\.icon\b|-mark\b|-dot\b|-status\b|::before|::after|\bsvg\b")
RAW_COLOR = re.compile(r"(?<![\w-])(?:#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\([^)]*\))")


class LanguageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang: str | None = None
        self.skip = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if tag in {"script", "style", "code"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "code"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.text.append(data)


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


def check_required() -> None:
    required = [
        ROOT / "SKILL.md",
        ROOT / "README.md",
        ROOT / "craft.json",
        ROOT / "references/identity.md",
        ROOT / "references/surfaces.md",
        ROOT / "references/extending.md",
        ROOT / "references/interfaces/design-language.md",
        ROOT / "references/interfaces/components.md",
        ROOT / "references/interfaces/patterns.md",
        ROOT / "references/slides/design-language.md",
        ROOT / "references/slides/authoring.md",
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
        assert path.is_file(), f"отсутствует {path.relative_to(ROOT)}"
    forbidden = [ROOT / "docs/cases", ROOT / "examples", ASSETS / "interfaces/specimen.html", ASSETS / "slides/specimen.html"]
    for path in forbidden:
        assert not path.exists(), f"публичные примеры и каталоги не входят в репозиторий: {path.relative_to(ROOT)}"
    fonts = list((ASSETS / "shared/fonts").glob("*.woff2"))
    expected = MANIFEST["requirements"]["fontFiles"]
    assert len(fonts) == expected, f"ожидалось локальных файлов шрифтов: {expected}, найдено: {len(fonts)}"


def check_assets() -> None:
    for path in CHECKED_HTML:
        parser = AssetParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for value in parser.assets:
            parts = urlsplit(value)
            assert not parts.scheme and not parts.netloc, f"внешний ресурс времени выполнения {value} в {path.relative_to(ROOT)}"
            target = (path.parent / unquote(parts.path)).resolve()
            assert target.is_file(), f"сломанный ресурс {value} в {path.relative_to(ROOT)}"


def check_tokens() -> None:
    tokens = ASSETS / "shared/tokens.css"
    for path in CSS_FILES:
        if path == tokens:
            continue
        match = RAW_COLOR.search(path.read_text(encoding="utf-8"))
        assert not match, f"сырой цвет {match.group(0)} вне assets/shared/tokens.css в {path.relative_to(ROOT)}"

    css = "\n".join(path.read_text(encoding="utf-8") for path in CSS_FILES)
    definitions = set(re.findall(r"(--[\w-]+)\s*:", css))
    usages = set(re.findall(r"var\((--[\w-]+)", css))
    dynamic = set(MANIFEST["dynamicCssProperties"])
    unknown = usages - definitions - dynamic
    assert not unknown, f"неопределённые свойства CSS: {', '.join(sorted(unknown))}"

    light_roles = {
        "--craft-light-bg", "--craft-light-surface", "--craft-light-sunken",
        "--craft-light-line", "--craft-light-line-strong", "--craft-light-text",
        "--craft-light-text-body", "--craft-light-muted", "--craft-light-accent",
        "--craft-light-accent-mark", "--craft-light-accent-fill",
        "--craft-light-accent-fill-hover", "--craft-light-accent-tint",
        "--craft-light-data-blue", "--craft-light-data-amber", "--craft-light-data-green",
    }
    missing_light = light_roles - definitions
    assert not missing_light, f"неполная светлая тема: {', '.join(sorted(missing_light))}"


def check_css_api() -> None:
    report = audit_css()
    groups = report["groups"]
    assert not groups["catalogOnly"], f"классы используются только каталогом: {', '.join(groups['catalogOnly'])}"
    assert not groups["unused"], f"неиспользуемые классы: {', '.join(groups['unused'])}"


def check_borders() -> None:
    adjacent = ({"top", "right"}, {"right", "bottom"}, {"bottom", "left"}, {"left", "top"})
    opposite = ({"top", "bottom"}, {"left", "right"})
    for path in CSS_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            directions = set(re.findall(r"border-(top|right|bottom|left)\s*:", match.group(2)))
            selector = match.group(1).strip()
            assert len(directions) < 3, f"трёхсторонняя рамка в {path.relative_to(ROOT)}: {selector}"
            assert not any(pair <= directions for pair in adjacent), f"угловая рамка в {path.relative_to(ROOT)}: {selector}"
            assert not any(pair <= directions for pair in opposite), f"две направленные границы могут слипнуться в {path.relative_to(ROOT)}: {selector}"


def check_state_marks() -> None:
    """Сигнальный цвет живёт в графической метке, а не в тексте состояния."""
    signal = re.compile(r"(?<![\w-])color\s*:\s*var\(--(ok|warn|error|data-[a-z]+)\)")
    for path in CSS_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            selector = match.group(1).strip()
            if not signal.search(match.group(2)):
                continue
            assert MARK_SELECTOR.search(selector), (
                f"сигнальный цвет окрашивает текст, а не метку, в {path.relative_to(ROOT)}: {selector}"
            )


def check_control_states() -> None:
    """У каждого элемента управления различимы наведение и недоступность.

    Видимый фокус даёт общее правило страницы, поэтому здесь проверяются те
    состояния, которые компонент описывает сам. Список закрыт: новый элемент
    управления добавляется в него вместе с правилами темы."""
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    selectors = [match.group(1).strip() for match in re.finditer(r"([^{}]+)\{[^{}]*\}", theme)]
    marks = {
        "hover": (":hover",),
        "disabled": (":disabled", "[disabled]", ":has(input:disabled)"),
    }
    controls = {
        ".button": ("hover", "disabled"),
        ".button--quiet": ("hover",),
        "textarea": ("hover", "disabled"),
        ".select-control select": ("hover", "disabled"),
        'input[type="checkbox"]': ("hover", "disabled"),
        'input[type="radio"]': ("hover", "disabled"),
        ".switch input": ("hover", "disabled"),
        ".range": ("disabled",),
        ".segmented span": ("hover",),
        ".tablist button": ("hover", "disabled"),
        ".pagination__page": ("hover",),
        ".breadcrumbs a": ("hover",),
        ".disclosure > summary": ("hover",),
        ".data-table__sort": ("hover",),
        ".section-nav__links a": ("hover",),
    }
    for control, required in controls.items():
        for state in required:
            found = any(
                control in selector and any(mark in selector for mark in marks[state])
                for selector in selectors
            )
            assert found, f"у элемента управления {control} нет состояния «{state}»"


def check_accessibility_contract() -> None:
    for path in CHECKED_HTML:
        if not path.is_file():
            continue
        parser = HeadingParser()
        parser.feed(path.read_text(encoding="utf-8"))
        assert parser.levels.count(1) == 1, f"в {path.relative_to(ROOT)} нужен ровно один h1"
        for previous, current in zip(parser.levels, parser.levels[1:]):
            assert current <= previous + 1, f"в {path.relative_to(ROOT)} пропущен уровень h{previous} → h{current}"

    for surface in ("interfaces", "slides"):
        css = "\n".join(path.read_text(encoding="utf-8") for path in (ASSETS / surface).glob("*.css"))
        assert ":focus-visible" in css, f"у формата {surface} нет правила видимого фокуса"
        assert "prefers-reduced-motion" in css, f"у формата {surface} нет правила уменьшения движения"
        assert "@media print" in css, f"у формата {surface} нет правил печати"

    interface_theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    assert ".select-control select:not(:disabled):hover" in interface_theme, "у select нет состояния наведения"
    assert ".select-control:has(select:focus-visible)" in interface_theme, "стрелка select не реагирует на фокус"

    slide_theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    sizes = [float(value) for value in re.findall(r"font(?:-size)?\s*:[^;{}]*?([0-9.]+)cqw", slide_theme)]
    assert sizes and min(sizes) >= 1.4, f"текст содержимого слайдов мельче 1.4cqw: {min(sizes)}"


def check_spacing_scale() -> None:
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    expected = {1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 7: 32}
    for index, value in expected.items():
        assert re.search(rf"--space-{index}:\s*{value}px\s*;", theme), f"нет --space-{index}: {value}px"

    catalog = (ROOT / MANIFEST["surfaces"]["interface"]["testPage"]).read_text(encoding="utf-8")
    for index in expected:
        assert f"var(--space-{index})" in catalog, f"каталог не показывает --space-{index}"


def check_fragment_manifest() -> None:
    allowed_kinds = {"text", "html", "id", "number", "token"}
    for surface_id, surface in MANIFEST["surfaces"].items():
        target = surface.get("fragmentTarget")
        assert isinstance(target, str) and target, f"для {surface_id} не задан fragmentTarget"
        fragments = surface.get("fragments", [])
        ids = [fragment.get("id") for fragment in fragments]
        assert len(ids) == len(set(ids)) and all(ids), f"идентификаторы фрагментов {surface_id} не уникальны"
        for fragment in fragments:
            assert set(fragment) == {"id", "path", "purpose", "placeholders", "dependencies"}, f"неполная запись фрагмента {fragment.get('id')}"
            path = ROOT / fragment["path"]
            assert path.is_file(), f"не найден фрагмент {fragment['path']}"
            assert isinstance(fragment["purpose"], str) and fragment["purpose"].strip(), f"не описано назначение {fragment['id']}"
            placeholders = fragment["placeholders"]
            assert isinstance(placeholders, dict) and placeholders, f"не описаны подстановки {fragment['id']}"
            assert set(placeholders.values()) <= allowed_kinds, f"неизвестный тип подстановки в {fragment['id']}"
            actual = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", path.read_text(encoding="utf-8")))
            assert actual == set(placeholders), f"метаданные подстановок расходятся с {fragment['path']}"
            for dependency in fragment["dependencies"]:
                assert (ROOT / dependency).is_file(), f"не найдена зависимость {dependency} для {fragment['id']}"
            if surface_id == "slides":
                html = path.read_text(encoding="utf-8")
                layouts = re.findall(r'data-slide-layout="([a-z-]+)"', html)
                assert layouts == [fragment["id"]], f"id и раскладка расходятся в {fragment['path']}"


def check_interface_components() -> None:
    surface = MANIFEST["surfaces"]["interface"]
    categories = surface.get("componentCategories", [])
    category_ids = [category.get("id") for category in categories]
    assert category_ids and len(category_ids) == len(set(category_ids)), "категории компонентов не уникальны"
    assert all(set(category) == {"id", "title"} and category["title"].strip() for category in categories), "неполная категория компонентов"

    components = surface.get("components", [])
    component_ids = [component.get("id") for component in components]
    assert component_ids and len(component_ids) == len(set(component_ids)), "компоненты интерфейса не уникальны"
    fields = {"id", "title", "category", "kind", "source", "rootClass", "dependencies", "summary"}
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    for component in components:
        assert set(component) == fields, f"неполная запись компонента {component.get('id')}"
        assert component["category"] in category_ids, f"неизвестная категория у {component['id']}"
        assert component["kind"] in {"foundation", "primitive", "fragment"}, f"неизвестный вид компонента {component['id']}"
        assert component["title"].strip() and component["summary"].strip(), f"не описан компонент {component['id']}"
        assert (ROOT / component["source"]).is_file(), f"не найден источник {component['source']}"
        for dependency in component["dependencies"]:
            assert (ROOT / dependency).is_file(), f"не найдена зависимость {dependency} для {component['id']}"
        root_class = component["rootClass"]
        if root_class:
            assert re.search(rf"\.{re.escape(root_class)}(?![\w-])", theme), f"не определён корневой класс {root_class}"

    fragment_ids = {fragment["id"] for fragment in surface["fragments"]}
    registered_fragments = {component["id"] for component in components if component["kind"] == "fragment"}
    assert registered_fragments == fragment_ids, "реестр компонентов не покрывает интерфейсные фрагменты"


def check_interface_documentation() -> None:
    directory = ROOT / "catalog/interfaces"
    surface = MANIFEST["surfaces"]["interface"]
    category_pages = {category["id"]: directory / f"{category['id']}.html" for category in surface["componentCategories"]}
    expected_ids = {component["id"] for component in surface["components"]}
    documented: set[str] = set()
    index = (directory / "index.html").read_text(encoding="utf-8")

    expected_navigation = ["foundations.html", "layout.html", "actions.html", "forms.html", "navigation.html", "data.html", "feedback.html", "overlays.html", "recipes.html"]
    for category, path in category_pages.items():
        assert path.is_file(), f"нет страницы категории {path.relative_to(ROOT)}"
        text = path.read_text(encoding="utf-8")
        actual = re.findall(r'data-component-doc="([a-z-]+)"', text)
        expected = [component["id"] for component in surface["components"] if component["category"] == category]
        assert actual == expected, f"страница {path.name} расходится с реестром компонентов"
        assert len(actual) == text.count('data-preview>'), f"не у каждого компонента {path.name} есть preview"
        assert len(actual) == text.count("data-preview-code"), f"не у каждого компонента {path.name} есть код"
        assert len(actual) == text.count('class="component-notes"'), f"не у каждого компонента {path.name} описано применение"
        assert len(actual) == text.count('class="component-api"'), f"не у каждого компонента {path.name} есть API-справочник"
        navigation = re.search(r'<div class="system-links">(.*?)</div>', text, re.DOTALL)
        assert navigation, f"в {path.name} нет общей навигации"
        links = re.findall(r'href="([a-z-]+\.html)"', navigation.group(1))
        assert links == expected_navigation, f"навигация расходится в {path.name}"
        for component_id in actual:
            assert f'href="{path.name}#{component_id}"' in index, f"индекс не ведёт к {component_id}"
        documented.update(actual)
    assert documented == expected_ids, "документация не покрывает реестр компонентов"

    recipes = (directory / "recipes.html").read_text(encoding="utf-8")
    recipe_ids = re.findall(r'data-recipe-doc="([a-z-]+)"', recipes)
    assert len(recipe_ids) == 3 and len(recipe_ids) == recipes.count("data-preview-code"), "рецепты не имеют живого примера и кода"

    short_version = ".".join(MANIFEST["version"].split(".")[:2])
    for path in sorted(directory.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "system-version" in text:
            assert f'<span class="system-version">{short_version}</span>' in text, f"устаревшая версия в {path.relative_to(ROOT)}"
        for href in re.findall(r'<a\b[^>]*href="([^"]+)"', text):
            parts = urlsplit(href)
            if parts.scheme or not parts.path:
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            assert target.is_file() and ROOT in target.parents, f"неработающая ссылка {href} в {path.relative_to(ROOT)}"
            if parts.fragment:
                target_text = target.read_text(encoding="utf-8")
                assert re.search(rf'\bid="{re.escape(parts.fragment)}"', target_text), f"нет якоря {href} в {path.relative_to(ROOT)}"


def check_interface_patterns() -> None:
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    starter = (ASSETS / "interfaces/starter-index.html").read_text(encoding="utf-8")
    fragments = {path.name: path.read_text(encoding="utf-8") for path in FRAGMENT_FILES if "interfaces" in path.parts}
    essential = {"page-head.html", "workspace-head.html", "metric-strip.html", "section.html", "split-workspace.html", "data-table.html", "empty-state.html", "section-nav.html"}
    assert essential <= set(fragments), "неполный базовый набор интерфейсных фрагментов"
    assert "@page { margin: 8mm 14mm; }" in theme, "не заданы безопасные поля печати"
    assert ".section { break-inside: auto; }" in theme, "длинная секция не может течь между страницами"
    assert 'data-craft-layout="interface"' in starter, "стартер не объявляет универсальную поверхность"
    assert 'id="craft-content"' in starter, "в стартере нет пустой области композиции"
    assert "scoreboard" not in starter and "workbench" not in starter and "document-band" not in starter, "стартер навязывает предметную композицию"
    assert "scroll-region" in fragments["split-workspace.html"] and 'tabindex="0"' in fragments["split-workspace.html"], "рабочая область недоступна с клавиатуры"
    assert "data-section-nav" in fragments["section-nav.html"], "фрагмент навигации не подключает общую механику"
    assert "<footer" not in starter, "стартер содержит декоративный футер"


def check_slide_layouts() -> None:
    registered = set(MANIFEST["surfaces"]["slides"].get("layouts", []))
    assert registered, "в craft.json не зарегистрированы слайдовые раскладки"
    fragments = [path.read_text(encoding="utf-8") for path in FRAGMENT_FILES if "slides" in path.parts]
    used = {value for html in fragments for value in re.findall(r'data-slide-layout="([a-z-]+)"', html)}
    unknown = used - registered
    missing = registered - used
    assert not unknown, f"неизвестные слайдовые раскладки: {', '.join(sorted(unknown))}"
    assert not missing, f"нет фрагментов раскладок: {', '.join(sorted(missing))}"
    for path in (path for path in FRAGMENT_FILES if "slides" in path.parts):
        html = path.read_text(encoding="utf-8")
        assert len(re.findall(r'<section class="slide\b', html)) == 1, f"{path.relative_to(ROOT)} должен содержать один слайд"
        assert len(re.findall(r'data-slide-layout="[a-z-]+"', html)) == 1, f"{path.relative_to(ROOT)} не объявляет раскладку"
    starter = (ASSETS / "slides/starter/index.html").read_text(encoding="utf-8")
    assert re.findall(r'data-slide-layout="([a-z-]+)"', starter) == ["title"], "стартовая колода должна содержать только титульный слайд"

    catalog_definition = MANIFEST["surfaces"]["slides"]
    catalog = (ROOT / catalog_definition["catalog"]).read_text(encoding="utf-8")
    catalog_layouts = set(re.findall(r'data-slide-layout="([a-z-]+)"', catalog))
    assert catalog_layouts == set(catalog_definition["catalogLayouts"]), "реестр раскладок каталога расходится с HTML"
    source_pages = len(re.findall(r'<section class="slide\b', catalog))
    assert catalog_definition["catalogPages"] > source_pages, "каталог не проверяет пошаговое раскрытие"


def check_content() -> None:
    allowed_templates = {
        ASSETS / "interfaces/starter-index.html": {"TITLE"},
        ASSETS / "slides/starter/index.html": {"TITLE"},
        ROOT / "scripts/scaffold.py": {"TITLE"},
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES or IGNORED_DIRS & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        placeholders = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", text))
        allowed = placeholders if path in FRAGMENT_FILES else allowed_templates.get(path, set())
        assert placeholders <= allowed, f"неожиданные подстановки в {path.relative_to(ROOT)}: {placeholders}"

    searchable = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not (IGNORED_DIRS & set(path.parts))
    ).lower()
    personal_terms = ["pa" + "vel", "koro" + "lev", "па" + "вел", "коро" + "л"]
    assert not any(term in searchable for term in personal_terms), "персональные названия не входят в Craft"


def check_language() -> None:
    assert MANIFEST.get("language") == "ru", "в craft.json должен быть указан русский язык"
    allowed_latin = {
        "aa", "api", "cdn", "chromium", "ci", "cli", "craft", "css", "esc", "example.com",
        "geologica", "highlight.js", "html", "imagemagick", "javascript", "json", "markdown", "node.js", "onest",
        "pdf", "px", "python", "qr", "svg", "url", "wcag",
    }

    for path in [ROOT / "README.md", ROOT / "SKILL.md", *sorted((ROOT / "references").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"\A---.*?---", "", text, flags=re.S)
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`]*`", "", text)
        text = re.sub(r"\]\([^)]*\)", "]", text)
        words = {word.lower().rstrip("-") for word in re.findall(r"\b[A-Za-z][A-Za-z0-9.-]*\b", text)}
        unknown = words - allowed_latin
        assert not unknown, f"английские слова в {path.relative_to(ROOT)}: {', '.join(sorted(unknown))}"


    for path in CHECKED_HTML:
        parser = LanguageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        assert parser.lang == "ru", f"в {path.relative_to(ROOT)} должен быть lang=ru"
        visible = " ".join(parser.text)
        visible = re.sub(r"\{\{[A-Z][A-Z0-9_]*\}\}|#[0-9a-fA-F]{3,8}\b", "", visible)
        words = {word.lower().rstrip("-") for word in re.findall(r"\b[A-Za-z][A-Za-z0-9.-]*\b", visible) if len(word) > 1}
        unknown = words - allowed_latin
        assert not unknown, f"английский текст в {path.relative_to(ROOT)}: {', '.join(sorted(unknown))}"

    for path in sorted((ROOT / "scripts").glob("*.py")):
        docstring = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
        assert docstring and re.search(r"[А-Яа-яЁё]", docstring), f"docstring не переведён в {path.relative_to(ROOT)}"

    for path in [*CSS_FILES, *ASSETS.rglob("*.js")]:
        if "vendor" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        comments = re.findall(r"/\*(.*?)\*/|//([^\n]*)", text, flags=re.S)
        for pair in comments:
            comment = " ".join(pair)
            if re.search(r"[A-Za-z]{3}", comment):
                assert re.search(r"[А-Яа-яЁё]", comment), f"английский комментарий в {path.relative_to(ROOT)}"

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "name: Проверки Craft" in workflow and "Установить инструменты" in workflow
    assert "Быстрые проверки" in makefile and "Удалить созданные" in makefile


def check_markdown_links() -> None:
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for value in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in value or value.startswith("mailto:"):
                continue
            target = (path.parent / value).resolve()
            assert target.exists(), f"сломанная ссылка Markdown {value} в {path.relative_to(ROOT)}"


def check_javascript() -> None:
    paths = [path for path in [*ASSETS.rglob("*.js"), *(ROOT / "catalog").rglob("*.js")] if "vendor" not in path.parts]
    for path in paths:
        run(node(), "--check", path)


def main() -> None:
    checks = (
        check_required,
        check_assets,
        check_tokens,
        check_css_api,
        check_borders,
        check_state_marks,
        check_control_states,
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
        check_required: "обязательные файлы",
        check_assets: "ресурсы",
        check_tokens: "токены",
        check_css_api: "публичный CSS API",
        check_borders: "рамки",
        check_state_marks: "метки состояний",
        check_control_states: "состояния управления",
        check_accessibility_contract: "контракт доступности",
        check_spacing_scale: "шкала отступов",
        check_fragment_manifest: "метаданные фрагментов",
        check_interface_components: "реестр компонентов",
        check_interface_documentation: "документация компонентов",
        check_interface_patterns: "паттерны интерфейсов",
        check_slide_layouts: "раскладки слайдов",
        check_content: "содержимое",
        check_language: "русский язык",
        check_markdown_links: "ссылки Markdown",
        check_javascript: "JavaScript",
    }
    for check in checks:
        check()
        print(f"✓ {labels[check]}")
    print("Готово: контракты исходников Craft соблюдены")


if __name__ == "__main__":
    main()
