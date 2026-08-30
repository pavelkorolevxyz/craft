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
        ROOT / "references/workflow.md",
        ROOT / "references/surfaces.md",
        ROOT / "references/extending.md",
        ROOT / "references/interfaces/design-language.md",
        ROOT / "references/interfaces/components.md",
        ROOT / "references/interfaces/atomic-design.md",
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

    component_tags: list[tuple[Path, str]] = []
    for path in CANONICAL_INTERFACE_PAGES:
        html = path.read_text(encoding="utf-8")
        component_tags.extend((path, tag) for tag in re.findall(r'<section[^>]+data-component-doc="[^"]+"[^>]*>', html))
    expected_components = len(MANIFEST["surfaces"]["interface"]["components"])
    assert len(component_tags) == expected_components, f"в атомарном реестре ожидалось {expected_components} компонента, найдено: {len(component_tags)}"
    for path, tag in component_tags:
        level = re.search(r'data-atomic-level="([^"]+)"', tag)
        assert level and level.group(1) in {"atom", "molecule", "organism"}, (
            f"у компонента в {path.relative_to(ROOT)} нет корректного data-atomic-level"
        )

    forbidden = [ROOT / "docs/cases", ROOT / "examples", ASSETS / "interfaces/specimen.html", ASSETS / "slides/specimen.html"]
    for path in forbidden:
        assert not path.exists(), f"публичные примеры и каталоги не входят в репозиторий: {path.relative_to(ROOT)}"
    fonts = list((ASSETS / "shared/fonts").glob("*.woff2"))
    expected = MANIFEST["requirements"]["fontFiles"]
    assert len(fonts) == expected, f"ожидалось локальных файлов шрифтов: {expected}, найдено: {len(fonts)}"

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    description = re.search(r'^description:\s*"([^"]+)"', skill, re.MULTILINE)
    assert description and len(description.group(1)) <= 57, "description навыка обрезается в индексе"
    assert len(skill.splitlines()) <= 60, "SKILL.md должен оставаться кратким роутером"
    assert "references/workflow.md" in skill and "## Обязательные требования" not in skill, "процесс и требования должны жить в справочниках"
    extending = (ROOT / "references/extending.md").read_text(encoding="utf-8")
    assert "## Разовая композиция" in extending and "## Поддерживаемая поверхность" in extending, "сценарии расширения Craft не разделены"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for package in ("craft-interface.zip", "craft-slides.zip", "craft-complete.zip"):
        assert package in readme, f"не описано назначение {package}"
    assert "sha256sum -c SHA256SUMS" in readme, "не описана проверка релизных архивов"
    case_study = ROOT / "catalog/slides/case-study.html"
    assert case_study.is_file() and "catalog/slides/case-study.html" in readme, "мини-колода не связана с README"
    case_html = case_study.read_text(encoding="utf-8")
    assert len(re.findall(r'<section class="slide\b', case_html)) == 8, "мини-колода должна содержать восемь исходных слайдов"
    for value in ("34", "19", "11", "58", MANIFEST["version"]):
        assert value in case_html, f"в мини-колоде отсутствует факт из реестра: {value}"


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


def check_catalog_grid() -> None:
    """Сетка каталога рисует рамки только вокруг существующих элементов."""
    css = (ROOT / "catalog/interfaces/catalog.css").read_text(encoding="utf-8")
    container = re.search(r"\.component-index\s*\{([^{}]+)\}", css)
    item = re.search(r"\.component-index a\s*\{([^{}]+)\}", css)
    assert container and item, "не найдены правила сетки каталога"
    assert not re.search(r"\bborder\s*:", container.group(1)), "контейнер component-index создаёт рамку вокруг пустых ячеек"
    assert "outline: 1px solid var(--line)" in item.group(1), "реальные ячейки component-index не владеют своей рамкой"
    assert not re.search(r"\.component-index(?:::[\w-]+|[^,{]*::[\w-]+)", css), "псевдоэлемент component-index имитирует пустые ячейки"
    assert not re.search(r"\.component-index[^{}]*\{[^{}]*(?:linear|radial)-gradient", css), "градиент component-index имитирует линии таблицы"


def check_state_marks() -> None:
    """Сигнальный цвет живёт в графической метке, а не в тексте состояния.

    Исключение одно: метка в рамке. Рамка и подпись внутри неё образуют одну
    деталь, поэтому подпись красится вместе с рамкой."""
    signal = re.compile(r"(?<![\w-])color\s*:\s*var\(--(ok|warn|error|status|data-[a-z]+)\b")
    for path in CSS_FILES:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            selector = match.group(1).split("*/")[-1].strip()
            if not signal.search(match.group(2)):
                continue
            assert MARK_SELECTOR.search(selector) or selector in LABEL_SELECTORS, (
                f"сигнальный цвет окрашивает текст, а не метку, в {path.relative_to(ROOT)}: {selector}"
            )


def check_control_states() -> None:
    """Интерактивные элементы различают наведение и постоянный выбор.

    Видимый фокус даёт общее правило страницы. Постоянное состояние нельзя
    заменять наведением: оно должно переживать уход указателя и читаться с
    клавиатуры и сенсорного экрана. Статические компоненты в список не входят."""
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
            assert found, f"у элемента управления {control} нет состояния «{state}»"

    assert ".data-table tbody tr:hover" not in theme, "статическая строка таблицы не должна притворяться интерактивной"



def check_hover_paint() -> None:
    """Наведение красит текст, а не подкладывает плоскость.

    Одно правило на всю систему: под курсором подпись уходит в акцент, фон
    остаётся прежним. Плоскость закреплена за постоянным выбором, и если её
    занимает наведение, два состояния становятся неразличимы. Заливку под
    курсором меняют только те элементы, у которых подпись лежит на акцентной
    плоскости или текста нет вовсе."""
    filled = (".button--primary", ".switch input", ".range")
    for path in (ASSETS / "interfaces/theme.css", ROOT / "catalog/interfaces/catalog.css"):
        css = path.read_text(encoding="utf-8")
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            selector = selector.strip()
            if ":hover" not in selector or not re.search(r"\bbackground(-color)?\s*:", body):
                continue
            assert any(control in selector for control in filled), (
                f"наведение подкладывает плоскость в {path.relative_to(ROOT)}: {selector}"
            )
        # Элемент управления с собственной рамкой под курсором усиливает рамку
        # и стрелку: акцент там занят фокусом. Остальным гасить подпись до
        # --text нельзя — наведение добавляет краску, а не убавляет.
        bordered = (".select-control", ".field", ".switch", "input", "textarea")
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            selector = selector.strip()
            if ":hover" not in selector or "color: var(--text)" not in body:
                continue
            assert any(control in selector for control in bordered), (
                f"наведение гасит акцент вместо того, чтобы его добавить, "
                f"в {path.relative_to(ROOT)}: {selector}"
            )

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
    assert re.search(r"\.select-control select[^,{]*:not\(:disabled\)[^,{]*:hover", interface_theme), "у select нет состояния наведения"
    assert ".select-control:has(select:focus-visible)" in interface_theme, "стрелка select не реагирует на фокус"
    assert ".sr-only" in interface_theme, "не определена утилита визуально скрытого текста"
    assert ".data-table--records td::before" in interface_theme, "у текстовой таблицы нет мобильных подписей"
    data_catalog = (ROOT / "catalog/interfaces/organisms.html").read_text(encoding="utf-8")
    record_table = re.search(r'<table class="data-table data-table--records">(.*?)</table>', data_catalog, re.DOTALL)
    assert record_table and all("data-label=" in tag for tag in re.findall(r"<td[^>]*>", record_table.group(1))), "ячейки мобильной таблицы не повторяют заголовки в data-label"

    slide_theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    sizes = [float(value) for value in re.findall(r"font(?:-size)?\s*:[^;{}]*?([0-9.]+)cqw", slide_theme)]
    assert sizes and min(sizes) >= 1.4, f"текст содержимого слайдов мельче 1.4cqw: {min(sizes)}"

    slide_base = (ASSETS / "slides/base.css").read_text(encoding="utf-8")
    assert "--control-size: 2.5rem" in slide_base and "width: 2.5rem; height: 2.5rem" in slide_base, "цели управления колодой меньше 40 px"
    assert "@media (hover: none), (pointer: coarse)" in slide_base, "нет touch-режима управления колодой"
    assert ".help-reveal { opacity: 1; pointer-events: auto; }" in slide_base, "на touch-экране не видна кнопка управления колодой"


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
        if surface_id == "slides":
            guidance = surface.get("layoutGuidance", {})
            assert set(guidance) == set(surface["catalogLayouts"]), "подсказки выбора не покрывают раскладки каталога"
            guidance_fields = {"job", "useWhen", "avoidWhen", "variable", "fixed", "slots", "reveal", "alternatives"}
            fragments_by_id = {fragment["id"]: fragment for fragment in fragments}
            for layout_id, item in guidance.items():
                assert set(item) == guidance_fields, f"неполная подсказка выбора {layout_id}"
                assert isinstance(item["job"], str) and item["job"].strip(), f"не описана работа {layout_id}"
                for field in ("useWhen", "avoidWhen", "variable", "fixed"):
                    assert isinstance(item[field], list) and all(isinstance(value, str) and value.strip() for value in item[field]), f"не заполнено поле {field} у {layout_id}"
                assert isinstance(item["slots"], dict) and item["slots"], f"не описаны изменяемые области {layout_id}"
                assert all(isinstance(value, str) and value.strip() for value in item["slots"].values()), f"пустое описание области у {layout_id}"
                if layout_id in fragments_by_id:
                    assert set(item["slots"]) == set(fragments_by_id[layout_id]["placeholders"]), f"описания подстановок расходятся у {layout_id}"
                assert set(item["reveal"]) == {"default", "guidance"}, f"не описано раскрытие {layout_id}"
                assert item["reveal"]["default"] in {"none", "optional"}, f"неизвестное раскрытие {layout_id}"
                assert isinstance(item["alternatives"], dict) and item["alternatives"], f"не указаны альтернативы {layout_id}"


def check_interface_components() -> None:
    surface = MANIFEST["surfaces"]["interface"]
    assert "componentCategories" not in surface, "старая иерархия категорий осталась в реестре"
    components = surface.get("components", [])
    foundations = surface.get("foundations", [])
    ids = [item.get("id") for item in [*foundations, *components]]
    assert ids and len(ids) == len(set(ids)), "элементы интерфейсной системы не уникальны"
    component_fields = {"id", "title", "level", "kind", "source", "rootClass", "dependencies", "summary"}
    foundation_fields = component_fields - {"level"}
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    for item in foundations:
        assert set(item) == foundation_fields and item["kind"] in {"foundation", "primitive", "fragment"}, f"неполная запись Foundation {item.get('id')}"
    for item in components:
        assert set(item) == component_fields, f"неполная запись компонента {item.get('id')}"
        assert item["level"] in {"atom", "molecule", "organism"}, f"неизвестный уровень у {item['id']}"
        assert item["kind"] in {"primitive", "fragment"}, f"неизвестный вид компонента {item['id']}"
    for item in [*foundations, *components]:
        assert item["title"].strip() and item["summary"].strip(), f"не описан элемент {item['id']}"
        assert (ROOT / item["source"]).is_file(), f"не найден источник {item['source']}"
        for dependency in item["dependencies"]:
            assert (ROOT / dependency).is_file(), f"не найдена зависимость {dependency} для {item['id']}"
        if item["rootClass"]:
            assert re.search(rf"\.{re.escape(item['rootClass'])}(?![\w-])", theme), f"не определён корневой класс {item['rootClass']}"
    fragment_ids = {fragment["id"] for fragment in surface["fragments"]}
    registered_fragments = {item["id"] for item in [*foundations, *components] if item["kind"] == "fragment"}
    assert registered_fragments == fragment_ids, "реестр не покрывает интерфейсные фрагменты"


def check_interface_documentation() -> None:
    directory = ROOT / "catalog/interfaces"
    surface = MANIFEST["surfaces"]["interface"]
    expected_ids = {component["id"] for component in surface["components"]}
    expected_foundations = {item["id"] for item in surface["foundations"]}
    level_pages = {
        "foundations.html": ("Foundation", None),
        "atoms.html": ("Атомы", "atom"),
        "molecules.html": ("Молекулы", "molecule"),
        "organisms.html": ("Организмы", "organism"),
        "templates.html": ("Шаблоны", None),
        "pages.html": ("Страницы", None),
    }
    expected_navigation = list(level_pages)
    documented: set[str] = set()

    for filename, (_, expected_level) in level_pages.items():
        path = directory / filename
        assert path.is_file(), f"нет страницы уровня {path.relative_to(ROOT)}"
        text = path.read_text(encoding="utf-8")
        primary = re.search(r'<div class="system-links">(.*?)</div>', text, re.DOTALL)
        assert primary and re.findall(r'href="([^"]+)"', primary.group(1)) == expected_navigation, f"навигация расходится в {path.name}"
        current = re.findall(r'<a\b[^>]*aria-current="true"[^>]*>([^<]+)</a>', primary.group(1))
        assert current == [level_pages[filename][0]], f"неверно отмечен уровень каталога в {path.name}"
        tags = re.findall(r'<section[^>]+data-component-doc="[^"]+"[^>]*>', text)
        actual = [re.search(r'data-component-doc="([^"]+)"', tag).group(1) for tag in tags]
        if expected_level:
            for tag in tags:
                level = re.search(r'data-atomic-level="([^"]+)"', tag)
                assert level and level.group(1) == expected_level, f"чужой уровень на странице {path.name}"
            assert len(actual) == text.count('data-preview>'), f"не у каждого компонента {path.name} есть preview"
            assert len(actual) == text.count("data-preview-code"), f"не у каждого компонента {path.name} есть код"
            assert len(actual) == text.count('class="component-api"'), f"не у каждого компонента {path.name} есть API-справочник"
        duplicates = documented & set(actual)
        assert not duplicates, f"компоненты описаны на нескольких уровнях: {', '.join(sorted(duplicates))}"
        documented.update(actual)

    listing = (directory / "catalog.css").read_text(encoding="utf-8")
    syntax_roles = {
        ".syntax-tag { color: var(--accent)": "имя элемента в листинге не совпадает с подсветкой слайдов",
        ".syntax-attr, .syntax-string { color: var(--craft-code-gold)": "атрибут и строка не используют золотой",
        ".syntax-doctype, .syntax-comment { color: var(--muted)": "служебные части листинга не приглушены",
    }
    for rule, message in syntax_roles.items():
        assert rule in listing, message

    assert documented == expected_ids, "страницы уровней не покрывают реестр компонентов"
    foundation_page = (directory / "foundations.html").read_text(encoding="utf-8")
    actual_foundations = set(re.findall(r'data-foundation-doc="([a-z-]+)"', foundation_page))
    assert actual_foundations == expected_foundations, "Foundation не совпадает с реестром"

    pages = (directory / "pages.html").read_text(encoding="utf-8")
    recipe_ids = re.findall(r'data-recipe-doc="([a-z-]+)"', pages)
    assert recipe_ids == ["filtered-table", "master-detail", "validated-form"], "страницы расходятся с ожидаемым порядком"
    assert len(recipe_ids) == pages.count("data-preview-code"), "страницы не имеют живого примера и кода"
    getting_started = (directory / "getting-started.html").read_text(encoding="utf-8")
    assert re.findall(r'data-recipe-doc="([a-z-]+)"', getting_started) == ["first-page"], "начало работы не содержит первую сборку"

    index = (directory / "index.html").read_text(encoding="utf-8")
    index_levels = re.findall(r'<div class="component-index[^"]*">(.*?)</div>', index, re.DOTALL)
    assert len(index_levels) == 1 and re.findall(r'href="([a-z-]+\.html)"', index_levels[0]) == list(level_pages), "главная дублирует содержимое страниц уровней"

    human_pages = [directory / "index.html", directory / "getting-started.html", *(directory / name for name in level_pages)]
    for path in human_pages:
        text = path.read_text(encoding="utf-8")
        primary = re.search(r'<div class="system-links">(.*?)</div>', text, re.DOTALL)
        assert primary and re.findall(r'href="([^"]+)"', primary.group(1)) == expected_navigation, f"основная навигация расходится в {path.name}"
        if path.name == "index.html":
            assert re.search(r'<a class="system-name" href="index.html" aria-current="page">Craft</a>', text), "главная не отмечена в заголовке Craft"
        assert 'href="sheet.html"' not in text, f"проверочный лист попал в пользовательскую навигацию {path.name}"

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
    theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    syntax_roles = {
        ".code .hljs-type { color: var(--accent)": "управляющие слова не используют акцент",
        ".code .hljs-name,": "имя элемента не покрашено акцентом",
        ".code .hljs-template-variable { color: var(--craft-code-gold)": "строки не используют золотой",
        ".code .hljs-bullet { color: var(--craft-code-blue)": "числа не используют синий",
    }
    for rule, message in syntax_roles.items():
        assert rule in theme, message
    # Gecko молча игнорирует calc без единиц измерения в геометрии SVG:
    # доля кольца превращается в целое кольцо, и слайд врёт про данные.
    assert "stroke-dasharray: calc(var(--value) * 1px" in theme, "доля кольца снова считается без единиц измерения"
    assert "stroke-dashoffset" not in theme, "начало доли снова смещает штрих вместо поворота и потеряется в Gecko"

    catalog_definition = MANIFEST["surfaces"]["slides"]
    catalog = (ROOT / catalog_definition["catalog"]).read_text(encoding="utf-8")
    catalog_layouts = set(re.findall(r'data-slide-layout="([a-z-]+)"', catalog))
    assert catalog_layouts == set(catalog_definition["catalogLayouts"]), "реестр раскладок каталога расходится с HTML"
    section_tags = re.findall(r'<section class="slide\b[^>]*>', catalog)
    examples = catalog_definition.get("catalogExamples", [])
    example_fields = {"id", "name", "layout", "job", "useWhen", "variable"}
    assert len(examples) == len(section_tags), "не каждый исходный слайд каталога описан в реестре"
    assert len({item.get("id") for item in examples}) == len(examples), "идентификаторы примеров каталога не уникальны"
    for item, tag in zip(examples, section_tags):
        assert set(item) == example_fields, f"неполное описание примера {item.get('id')}"
        assert all(isinstance(item[field], str) and item[field].strip() for field in example_fields), f"пустое описание примера {item.get('id')}"
        assert re.search(rf'data-catalog-example="{re.escape(item["id"])}"', tag), f"описание {item['id']} расходится с порядком каталога"
        layout = re.search(r'data-slide-layout="([a-z-]+)"', tag)
        assert layout and layout.group(1) == item["layout"], f"раскладка примера {item['id']} расходится с HTML"
    chart_rows = re.findall(r'<div class="chart-row[^"]*"><span>[^<]+</span><strong data-count>[^<]+</strong>', catalog)
    assert len(chart_rows) == catalog.count('class="chart-row'), "не у каждой строки горизонтального графика подписано и анимировано значение"
    source_pages = len(re.findall(r'<section class="slide\b', catalog))
    assert catalog_definition["catalogPages"] > source_pages, "каталог не проверяет пошаговое раскрытие"
    assert catalog_definition["catalogPrintPages"] == catalog_definition["catalogPages"], "PDF должен содержать все экранные страницы"

    base = (ASSETS / "slides/base.css").read_text(encoding="utf-8")
    deck = (ASSETS / "slides/deck.js").read_text(encoding="utf-8")
    print_contracts = {
        "@page { size: 320mm 180mm; margin: 0; }": "печать слайдов потеряла фиксированный лист 16:9",
        ".slide-canvas {\n  position: relative;\n  width: 100%;\n  height: 100%;": "внутренняя область слайда снова может обрезаться в Zen",
        "html, body, .deck, .slides { height: 100% !important; }": "Zen снова будет переносить хвост слайда на отдельный лист",
        ".slide[data-print-page]:last-child": "Firefox снова добавит пустой последний лист",
    }
    for rule, message in print_contracts.items():
        assert rule in base, message
    assert "page.setAttribute('data-print-page', '');" in deck, "не все экранные шаги отмечены для печати"
    assert "canvas.className = 'slide-canvas';" in deck, "колода не создаёт независимую область печатной раскладки"


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
        "foundation", "geologica", "highlight.js", "html", "imagemagick", "javascript", "json", "markdown", "node.js", "onest",
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
        check_required: "обязательные файлы",
        check_assets: "ресурсы",
        check_tokens: "токены",
        check_css_api: "публичный CSS API",
        check_borders: "рамки",
        check_catalog_grid: "сетка каталога",
        check_state_marks: "метки состояний",
        check_control_states: "состояния управления",
        check_hover_paint: "краска наведения",
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
