#!/usr/bin/env python3
"""Показывает использование классов публичного CSS API Craft."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from lib import ASSETS, MANIFEST, ROOT

CLASS = re.compile(r"\.(-?[_a-zA-Z]+[\w-]*)")


def class_definitions(paths: list[Path]) -> dict[str, list[str]]:
    definitions: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"([^{}]+)\{", text):
            selector = match.group(1)
            for name in CLASS.findall(selector):
                relative = path.relative_to(ROOT).as_posix()
                if relative not in definitions[name]:
                    definitions[name].append(relative)
    return dict(definitions)


def contains(text: str, name: str) -> bool:
    return bool(re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text))


def read_all(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.is_file())


def audit() -> dict[str, object]:
    css_paths = [
        ASSETS / "shared/tokens.css",
        ASSETS / "interfaces/theme.css",
        ASSETS / "slides/base.css",
        ASSETS / "slides/theme.css",
    ]
    public_html: list[Path] = []
    for surface in MANIFEST["surfaces"].values():
        public_html.extend(ROOT / path for path in surface["entrypoints"])
        public_html.extend(ROOT / fragment["path"] for fragment in surface["fragments"])
    public_js = list(ASSETS.rglob("*.js"))
    references = sorted((ROOT / "references").rglob("*.md")) + [ROOT / "README.md", ROOT / "SKILL.md"]
    catalogs = sorted((ROOT / "catalog").rglob("*.html"))

    definitions = class_definitions(css_paths)
    public_text = read_all([*public_html, *public_js])
    reference_text = read_all(references)
    catalog_text = read_all(catalogs)
    dynamic = set(MANIFEST.get("dynamicCssClasses", []))
    catalog_classes = {name for surface in MANIFEST["surfaces"].values() for name in surface.get("catalogCssClasses", [])}
    unknown_dynamic = (dynamic | catalog_classes) - set(definitions)
    assert not unknown_dynamic, f"не определены зарегистрированные классы: {', '.join(sorted(unknown_dynamic))}"
    missing_catalog_classes = {name for name in catalog_classes if not contains(catalog_text, name)}
    assert not missing_catalog_classes, f"каталог не показывает классы: {', '.join(sorted(missing_catalog_classes))}"
    groups: dict[str, list[str]] = {"runtime": [], "documented": [], "catalogOnly": [], "unused": []}
    for name in sorted(definitions):
        if name in dynamic or name in catalog_classes or contains(public_text, name):
            groups["runtime"].append(name)
        elif contains(reference_text, name):
            groups["documented"].append(name)
        elif contains(catalog_text, name):
            groups["catalogOnly"].append(name)
        else:
            groups["unused"].append(name)
    return {
        "summary": {key: len(value) for key, value in groups.items()} | {"defined": len(definitions)},
        "groups": groups,
        "definitions": definitions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Вывести полный машиночитаемый отчёт")
    parser.add_argument("--fail-on-unused", action="store_true", help="Завершиться ошибкой при неиспользуемых классах")
    args = parser.parse_args()
    report = audit()
    groups: dict[str, list[str]] = report["groups"]  # type: ignore[assignment]
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary: dict[str, int] = report["summary"]  # type: ignore[assignment]
        print(
            "CSS API: "
            f"определено {summary['defined']}, в публичной механике {summary['runtime']}, "
            f"только в документации {summary['documented']}, только в каталоге {summary['catalogOnly']}, "
            f"не используется {summary['unused']}"
        )
        for key, title in (("documented", "Только документация"), ("catalogOnly", "Только каталог"), ("unused", "Не используется")):
            values = groups[key]
            if values:
                print(f"{title}: {', '.join(values)}")
    if args.fail_on_unused and (groups["catalogOnly"] or groups["unused"]):
        raise SystemExit("Найдены классы вне публичной механики")


if __name__ == "__main__":
    main()
