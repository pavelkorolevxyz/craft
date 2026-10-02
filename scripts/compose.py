#!/usr/bin/env python3
"""Adds a parameterized Craft fragment to an existing local project."""

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
    """Bad input or bad project structure."""


def project_index(path: Path) -> Path:
    target = path.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    if not index.is_file():
        raise ComposeError(f"index.html not found: {index}")
    return index


def detect_surface(document: str) -> str:
    interface = 'data-craft-layout="interface"' in document
    slides = bool(re.search(r'class="[^"]*\bslides\b', document))
    if interface == slides:
        raise ComposeError("cannot tell the project format for sure")
    return "interface" if interface else "slides"


def parse_assignments(values: list[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ComposeError(f"{option}: expected NAME=VALUE")
        name, content = value.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ComposeError(f"{option}: invalid name {name}")
        if name in result:
            raise ComposeError(f"{option}: value {name} passed twice")
        result[name] = content
    return result


def validate_value(name: str, kind: str, value: str) -> str:
    if kind == "html":
        return value
    if kind == "id" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", value):
        raise ComposeError(f"{name}: invalid HTML id")
    if kind == "number":
        try:
            number = float(value)
        except ValueError as error:
            raise ComposeError(f"{name}: expected a number") from error
        if not math.isfinite(number):
            raise ComposeError(f"{name}: expected a finite number")
    if kind == "token" and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ComposeError(f"{name}: expected one safe name")
    return html_module.escape(value, quote=True)


def container_bounds(document: str, selector: str) -> tuple[int, int]:
    if selector.startswith("#"):
        value = re.escape(selector[1:])
        marker = rf'\bid\s*=\s*(?:"{value}"|\'{value}\')'
    elif selector.startswith("."):
        value = re.escape(selector[1:])
        marker = rf'\bclass\s*=\s*(?:"[^"]*\b{value}\b[^"]*"|\'[^\']*\b{value}\b[^\']*\')'
    else:
        raise ComposeError(f"unsupported fragmentTarget: {selector}")
    opening = re.search(rf'<(?P<tag>[a-zA-Z][\w:-]*)\b(?=[^>]*{marker})[^>]*>', document)
    if not opening:
        raise ComposeError(f"container {selector} not found in project")
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
    raise ComposeError(f"container {selector} is not closed")


def ensure_dependencies(document: str, project: Path, dependencies: list[str], copy_files: bool = True) -> str:
    for dependency in dependencies:
        source = ROOT / dependency
        # The path inside the format is kept, so assets/slides/vendor/x.js goes to vendor/x.js.
        relative = Path(*Path(dependency).parts[2:]).as_posix()
        target = project / relative
        if copy_files and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        escaped = re.escape(relative)
        if target.suffix == ".js" and not re.search(rf'<script\b[^>]*src=["\'](?:\./)?{escaped}["\']', document):
            document = document.replace("</body>", f'<script src="{relative}"></script>\n</body>')
        if target.suffix == ".css" and not re.search(rf'<link\b[^>]*href=["\'](?:\./)?{escaped}["\']', document):
            document = document.replace("</head>", f'<link rel="stylesheet" href="{relative}">\n</head>')
    return document


def atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


SLIDE_KEY = re.compile(r"[a-z0-9][a-z0-9-]*")


def apply_slide_key(document: str, rendered: str, key: str | None) -> str:
    """Gives the source slide a stable key. The page number changes, the key does not."""
    if not key:
        raise ComposeError("the slide needs a stable key: --key slide-name")
    if not SLIDE_KEY.fullmatch(key):
        raise ComposeError("--key: lowercase Latin letters, digits and hyphens, for example pricing-risks")
    if re.search(rf'\bdata-key\s*=\s*["\']{re.escape(key)}["\']', document):
        raise ComposeError(f"slide key already taken: {key}")
    result, count = re.subn(r'<section class="slide\b([^>]*)>', lambda match: f'<section class="slide{match.group(1)} data-key="{key}">', rendered, count=1)
    if count != 1:
        raise ComposeError("source slide not found in the fragment")
    return result


def compose(index: Path, fragment_id: str, text_values: dict[str, str], html_values: dict[str, str], html_files: dict[str, str], dry_run: bool, key: str | None = None) -> str:
    document = index.read_text(encoding="utf-8")
    surface_id = detect_surface(document)
    surface = MANIFEST["surfaces"][surface_id]
    fragments = {fragment["id"]: fragment for fragment in surface["fragments"]}
    if fragment_id not in fragments:
        available = ", ".join(fragments)
        raise ComposeError(f"unknown fragment {fragment_id} for {surface_id}. Available: {available}")
    fragment = fragments[fragment_id]
    kinds: dict[str, str] = fragment["placeholders"]

    supplied: dict[str, tuple[str, str]] = {}
    for name, value in text_values.items():
        supplied[name] = ("set", value)
    for name, value in html_values.items():
        if name in supplied:
            raise ComposeError(f"{name}: value passed in more than one way")
        supplied[name] = ("html", value)
    for name, filename in html_files.items():
        if name in supplied:
            raise ComposeError(f"{name}: value passed in more than one way")
        source = Path(filename).expanduser()
        if not source.is_file():
            raise ComposeError(f"{name}: HTML file not found {source}")
        supplied[name] = ("html", source.read_text(encoding="utf-8"))

    unknown = set(supplied) - set(kinds)
    missing = set(kinds) - set(supplied)
    if unknown:
        raise ComposeError(f"unknown placeholders: {', '.join(sorted(unknown))}")
    if missing:
        raise ComposeError(f"placeholders not set: {', '.join(sorted(missing))}")

    rendered = (ROOT / fragment["path"]).read_text(encoding="utf-8")
    ids: list[str] = []
    for name, kind in kinds.items():
        mode, value = supplied[name]
        if kind == "html" and mode != "html":
            raise ComposeError(f"{name}: pass HTML with --html or --html-file")
        if kind != "html" and mode != "set":
            raise ComposeError(f"{name}: pass type {kind} with --set")
        rendered = rendered.replace(f"{{{{{name}}}}}", validate_value(name, kind, value))
        if kind == "id":
            ids.append(value)
    for value in ids:
        if re.search(rf'\bid\s*=\s*["\']{re.escape(value)}["\']', document):
            raise ComposeError(f"id already exists in project: {value}")

    if surface_id == "slides":
        rendered = apply_slide_key(document, rendered, key)
    elif key:
        raise ComposeError("--key works only with slides")

    document = ensure_dependencies(document, index.parent, fragment["dependencies"], copy_files=not dry_run)
    _, close = container_bounds(document, surface["fragmentTarget"])
    separator = "" if document[:close].endswith("\n") else "\n"
    result = document[:close] + separator + rendered.rstrip() + "\n" + document[close:]
    if not dry_run:
        atomic_write(index, result)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project folder or index.html")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--fragment", help="Fragment id")
    selection.add_argument("--list-fragments", action="store_true", help="List the fragments available for the format")
    parser.add_argument("--set", dest="sets", action="append", default=[], metavar="NAME=VALUE", help="Text, id, number or name")
    parser.add_argument("--html", action="append", default=[], metavar="NAME=MARKUP", help="Explicitly trusted HTML markup")
    parser.add_argument("--html-file", action="append", default=[], metavar="NAME=PATH", help="Markup from a local file")
    parser.add_argument("--key", help="Stable slide key for the #key address, the deck map and edit reports")
    parser.add_argument("--list-placeholders", action="store_true", help="Show the contract of the chosen fragment")
    parser.add_argument("--dry-run", action="store_true", help="Check and print the fragment without changing the project")
    args = parser.parse_args()
    if args.list_placeholders and not args.fragment:
        parser.error("--list-placeholders needs --fragment")

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
                raise ComposeError(f"unknown fragment {args.fragment}. Available: {available}")
            print(f"{fragment['id']}: {fragment['purpose']}")
            guidance = surface.get("layoutGuidance", {}).get(fragment["id"])
            if guidance:
                print(f"Job: {guidance['job']}")
                print("Use when:")
                for item in guidance["useWhen"]:
                    print(f"  + {item}")
                print("Avoid when:")
                for item in guidance["avoidWhen"]:
                    print(f"  - {item}")
                print("Fixed:")
                for item in guidance["fixed"]:
                    print(f"  ! {item}")
                print("Variable:")
                for item in guidance["variable"]:
                    print(f"  · {item}")
                print("Before building, write down the point, the data relation, the first frame, the reveal steps and the reason for the accent.")
                print("Layout rules: references/slides/selection.md")
                print(f"Template reveal: {guidance['reveal']['default']}")
                print(f"  {guidance['reveal']['guidance']}")
                print("Placeholders:")
            for name, kind in fragment["placeholders"].items():
                note = guidance.get("slots", {}).get(name) if guidance else None
                suffix = f". {note}" if note else ""
                print(f"  {name}: {kind}{suffix}")
            if guidance and guidance["alternatives"]:
                print("Alternatives:")
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
            args.key,
        )
    except (ComposeError, OSError) as error:
        parser.error(str(error))
    if args.dry_run:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    else:
        print(f"✓ added fragment {args.fragment}: {index}")


if __name__ == "__main__":
    main()
