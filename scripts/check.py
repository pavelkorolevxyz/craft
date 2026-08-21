#!/usr/bin/env python3
"""Быстрые проверки контрактов исходников Craft с минимумом зависимостей."""

from __future__ import annotations

import ast
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lib import ASSETS, MANIFEST, ROOT, node, run

TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py"}
CSS_FILES = list(ASSETS.rglob("*.css"))
HTML_FILES = [ROOT / path for surface in MANIFEST["surfaces"].values() for path in surface["entrypoints"]]
EXAMPLE_HTML_FILES = [ROOT / "examples/observability/index.html"]
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
        ASSETS / "interfaces/specimen.css",
        ASSETS / "interfaces/specimen.js",
        ASSETS / "slides/base.css",
        ASSETS / "slides/theme.css",
        ASSETS / "slides/deck.js",
        ROOT / "examples/observability/dashboard.css",
        ROOT / "examples/observability/dashboard.js",
        ROOT / "examples/observability/telemetry.js",
        *HTML_FILES,
        *EXAMPLE_HTML_FILES,
    ]
    for path in required:
        assert path.is_file(), f"отсутствует {path.relative_to(ROOT)}"
    fonts = list((ASSETS / "shared/fonts").glob("*.woff2"))
    expected = MANIFEST["requirements"]["fontFiles"]
    assert len(fonts) == expected, f"ожидалось локальных файлов шрифтов: {expected}, найдено: {len(fonts)}"


def check_assets() -> None:
    for path in [*HTML_FILES, *EXAMPLE_HTML_FILES]:
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


def check_accessibility_contract() -> None:
    heading_files = [*HTML_FILES, *EXAMPLE_HTML_FILES]
    for path in heading_files:
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

    slide_theme = (ASSETS / "slides/theme.css").read_text(encoding="utf-8")
    sizes = [float(value) for value in re.findall(r"font(?:-size)?\s*:[^;{}]*?([0-9.]+)cqw", slide_theme)]
    assert sizes and min(sizes) >= 1.4, f"текст содержимого слайдов мельче 1.4cqw: {min(sizes)}"


def check_spacing_scale() -> None:
    theme = (ASSETS / "interfaces/theme.css").read_text(encoding="utf-8")
    expected = {1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48}
    for index, value in expected.items():
        assert re.search(rf"--space-{index}:\s*{value}px\s*;", theme), f"нет --space-{index}: {value}px"

    specimen = (ASSETS / "interfaces/specimen.html").read_text(encoding="utf-8")
    for index in expected:
        assert f"var(--space-{index})" in specimen, f"каталог не показывает --space-{index}"


def check_content() -> None:
    allowed_templates = {
        ASSETS / "interfaces/starter-index.html": {"TITLE", "DATE"},
        ASSETS / "slides/starter/index.html": {"TITLE"},
        ROOT / "scripts/scaffold.py": {"TITLE", "DATE"},
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES or {".git", ".ralph"} & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        placeholders = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", text))
        assert placeholders <= allowed_templates.get(path, set()), f"неожиданные подстановки в {path.relative_to(ROOT)}: {placeholders}"

    searchable = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not ({".git", ".ralph"} & set(path.parts))
    ).lower()
    personal_terms = ["pa" + "vel", "koro" + "lev", "па" + "вел", "коро" + "л"]
    assert not any(term in searchable for term in personal_terms), "персональные названия не входят в Craft"


def check_language() -> None:
    assert MANIFEST.get("language") == "ru", "в craft.json должен быть указан русский язык"
    allowed_latin = {
        "aa", "api", "cdn", "chromium", "ci", "cli", "craft", "css", "edge-01", "esc", "example.com",
        "geologica", "highlight.js", "html", "imagemagick", "javascript", "json", "markdown", "node.js", "onest",
        "p95", "p99", "pdf", "px", "python", "qr", "saas", "svg", "url", "wcag",
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

    for path in [*HTML_FILES, *EXAMPLE_HTML_FILES]:
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
    paths = (
        ASSETS / "interfaces/specimen.js",
        ASSETS / "slides/deck.js",
        ASSETS / "slides/code-highlight.js",
        ROOT / "examples/observability/dashboard.js",
        ROOT / "examples/observability/telemetry.js",
    )
    for path in paths:
        run(node(), "--check", path)


def main() -> None:
    checks = (
        check_required,
        check_assets,
        check_tokens,
        check_borders,
        check_accessibility_contract,
        check_spacing_scale,
        check_content,
        check_language,
        check_markdown_links,
        check_javascript,
    )
    labels = {
        check_required: "обязательные файлы",
        check_assets: "ресурсы",
        check_tokens: "токены",
        check_borders: "рамки",
        check_accessibility_contract: "контракт доступности",
        check_spacing_scale: "шкала отступов",
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
