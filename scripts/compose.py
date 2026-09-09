#!/usr/bin/env python3
"""Добавляет параметризованный фрагмент Craft в существующий локальный проект."""

from __future__ import annotations

import argparse
import html as html_module
import math
import re
import shutil
import tempfile
from pathlib import Path

from lib import MANIFEST, ROOT


class ComposeError(ValueError):
    """Ошибка входных данных или структуры проекта."""


def project_index(path: Path) -> Path:
    target = path.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    if not index.is_file():
        raise ComposeError(f"не найден index.html: {index}")
    return index


def detect_surface(document: str) -> str:
    interface = 'data-craft-layout="interface"' in document
    slides = bool(re.search(r'class="[^"]*\bslides\b', document))
    if interface == slides:
        raise ComposeError("не удалось однозначно определить формат проекта")
    return "interface" if interface else "slides"


def parse_assignments(values: list[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ComposeError(f"{option}: ожидается ИМЯ=ЗНАЧЕНИЕ")
        name, content = value.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ComposeError(f"{option}: недопустимое имя {name}")
        if name in result:
            raise ComposeError(f"{option}: значение {name} передано повторно")
        result[name] = content
    return result


def validate_value(name: str, kind: str, value: str) -> str:
    if kind == "html":
        return value
    if kind == "id" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", value):
        raise ComposeError(f"{name}: недопустимый HTML id")
    if kind == "number":
        try:
            number = float(value)
        except ValueError as error:
            raise ComposeError(f"{name}: ожидается число") from error
        if not math.isfinite(number):
            raise ComposeError(f"{name}: ожидается конечное число")
    if kind == "token" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ComposeError(f"{name}: ожидается одно безопасное имя")
    return html_module.escape(value, quote=True)


def container_bounds(document: str, selector: str) -> tuple[int, int]:
    if selector.startswith("#"):
        value = re.escape(selector[1:])
        marker = rf'\bid\s*=\s*(?:"{value}"|\'{value}\')'
    elif selector.startswith("."):
        value = re.escape(selector[1:])
        marker = rf'\bclass\s*=\s*(?:"[^"]*\b{value}\b[^"]*"|\'[^\']*\b{value}\b[^\']*\')'
    else:
        raise ComposeError(f"неподдерживаемый fragmentTarget: {selector}")
    opening = re.search(rf'<(?P<tag>[a-zA-Z][\w:-]*)\b(?=[^>]*{marker})[^>]*>', document)
    if not opening:
        raise ComposeError(f"в проекте не найден контейнер {selector}")
    tag = opening.group("tag")
    depth = 1
    for match in re.finditer(rf'</?{re.escape(tag)}\b[^>]*>', document[opening.end():], flags=re.I):
        token = match.group(0)
        if token.startswith("</"):
            depth -= 1
            if depth == 0:
                close_start = opening.end() + match.start()
                return opening.end(), close_start
        elif not token.rstrip().endswith("/>"):
            depth += 1
    raise ComposeError(f"контейнер {selector} не закрыт")


def ensure_dependencies(document: str, project: Path, dependencies: list[str], copy_files: bool = True) -> str:
    for dependency in dependencies:
        source = ROOT / dependency
        target = project / source.name
        if copy_files and not target.exists():
            shutil.copy2(source, target)
        escaped = re.escape(target.name)
        if target.suffix == ".js" and not re.search(rf'<script\b[^>]*src=["\'][^"\']*{escaped}["\']', document):
            document = document.replace("</body>", f'<script src="{target.name}"></script>\n</body>')
        if target.suffix == ".css" and not re.search(rf'<link\b[^>]*href=["\'][^"\']*{escaped}["\']', document):
            document = document.replace("</head>", f'<link rel="stylesheet" href="{target.name}">\n</head>')
    return document


def atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def compose(index: Path, fragment_id: str, text_values: dict[str, str], html_values: dict[str, str], html_files: dict[str, str], dry_run: bool) -> str:
    document = index.read_text(encoding="utf-8")
    surface_id = detect_surface(document)
    surface = MANIFEST["surfaces"][surface_id]
    fragments = {fragment["id"]: fragment for fragment in surface["fragments"]}
    if fragment_id not in fragments:
        available = ", ".join(fragments)
        raise ComposeError(f"неизвестный фрагмент {fragment_id} для {surface_id}; доступны: {available}")
    fragment = fragments[fragment_id]
    kinds: dict[str, str] = fragment["placeholders"]

    supplied: dict[str, tuple[str, str]] = {}
    for name, value in text_values.items():
        supplied[name] = ("set", value)
    for name, value in html_values.items():
        if name in supplied:
            raise ComposeError(f"{name}: значение передано несколькими способами")
        supplied[name] = ("html", value)
    for name, filename in html_files.items():
        if name in supplied:
            raise ComposeError(f"{name}: значение передано несколькими способами")
        source = Path(filename).expanduser()
        if not source.is_file():
            raise ComposeError(f"{name}: не найден HTML-файл {source}")
        supplied[name] = ("html", source.read_text(encoding="utf-8"))

    unknown = set(supplied) - set(kinds)
    missing = set(kinds) - set(supplied)
    if unknown:
        raise ComposeError(f"неизвестные подстановки: {', '.join(sorted(unknown))}")
    if missing:
        raise ComposeError(f"не заданы подстановки: {', '.join(sorted(missing))}")

    rendered = (ROOT / fragment["path"]).read_text(encoding="utf-8")
    ids: list[str] = []
    for name, kind in kinds.items():
        mode, value = supplied[name]
        if kind == "html" and mode != "html":
            raise ComposeError(f"{name}: HTML передаётся через --html или --html-file")
        if kind != "html" and mode != "set":
            raise ComposeError(f"{name}: тип {kind} передаётся через --set")
        rendered = rendered.replace(f"{{{{{name}}}}}", validate_value(name, kind, value))
        if kind == "id":
            ids.append(value)
    for value in ids:
        if re.search(rf'\bid\s*=\s*["\']{re.escape(value)}["\']', document):
            raise ComposeError(f"id уже существует в проекте: {value}")

    document = ensure_dependencies(document, index.parent, fragment["dependencies"], copy_files=not dry_run)
    _, close = container_bounds(document, surface["fragmentTarget"])
    separator = "" if document[:close].endswith("\n") else "\n"
    result = document[:close] + separator + rendered.rstrip() + "\n" + document[close:]
    if not dry_run:
        atomic_write(index, result)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Папка проекта или index.html")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--fragment", help="Идентификатор фрагмента")
    selection.add_argument("--list-fragments", action="store_true", help="Показать доступные фрагменты формата")
    parser.add_argument("--set", dest="sets", action="append", default=[], metavar="ИМЯ=ЗНАЧЕНИЕ", help="Текст, id, число или имя")
    parser.add_argument("--html", action="append", default=[], metavar="ИМЯ=РАЗМЕТКА", help="Явно доверенная HTML-разметка")
    parser.add_argument("--html-file", action="append", default=[], metavar="ИМЯ=ПУТЬ", help="Разметка из локального файла")
    parser.add_argument("--list-placeholders", action="store_true", help="Показать контракт выбранного фрагмента")
    parser.add_argument("--dry-run", action="store_true", help="Проверить и вывести фрагмент без изменения проекта")
    args = parser.parse_args()
    if args.list_placeholders and not args.fragment:
        parser.error("--list-placeholders требует --fragment")

    try:
        index = project_index(args.project)
        document = index.read_text(encoding="utf-8")
        surface = MANIFEST["surfaces"][detect_surface(document)]
        if args.list_fragments:
            for item in surface["fragments"]:
                print(f"{item['id']}: {item['purpose']}")
            return
        fragment = next((item for item in surface["fragments"] if item["id"] == args.fragment), None)
        if args.list_placeholders:
            if not fragment:
                available = ", ".join(item["id"] for item in surface["fragments"])
                raise ComposeError(f"неизвестный фрагмент {args.fragment}; доступны: {available}")
            print(f"{fragment['id']}: {fragment['purpose']}")
            guidance = surface.get("layoutGuidance", {}).get(fragment["id"])
            if guidance:
                print(f"Работа: {guidance['job']}")
                print("Подходит, когда:")
                for item in guidance["useWhen"]:
                    print(f"  + {item}")
                print("Не подходит, когда:")
                for item in guidance["avoidWhen"]:
                    print(f"  - {item}")
                print("Обязательные условия:")
                for item in guidance["fixed"]:
                    print(f"  ! {item}")
                print("Можно менять:")
                for item in guidance["variable"]:
                    print(f"  · {item}")
                print("До сборки: запиши мысль, отношение данных, первый кадр, шаги раскрытия и причину акцента.")
                print("Правила выбора: references/slides/selection.md")
                print(f"Раскрытие исходного шаблона: {guidance['reveal']['default']}")
                print(f"  {guidance['reveal']['guidance']}")
                print("Подстановки:")
            for name, kind in fragment["placeholders"].items():
                note = guidance.get("slots", {}).get(name) if guidance else None
                suffix = f". {note}" if note else ""
                print(f"  {name}: {kind}{suffix}")
            if guidance and guidance["alternatives"]:
                print("Альтернативы:")
                for item, reason in guidance["alternatives"].items():
                    print(f"  {item}: {reason}")
            return
        rendered = compose(
            index,
            args.fragment,
            parse_assignments(args.sets, "--set"),
            parse_assignments(args.html, "--html"),
            parse_assignments(args.html_file, "--html-file"),
            args.dry_run,
        )
    except (ComposeError, OSError) as error:
        parser.error(str(error))
    if args.dry_run:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    else:
        print(f"✓ добавлен фрагмент {args.fragment}: {index}")


if __name__ == "__main__":
    main()
