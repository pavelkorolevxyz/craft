#!/usr/bin/env python3
"""Packs a Craft project into one HTML file with no external or local dependencies."""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

MIME = {
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
LINK_TAG = re.compile(r"<link\b[^>]*>")
SCRIPT_TAG = re.compile(r"<script\b([^>]*)></script>")
ATTRIBUTE = re.compile(r"([a-z-]+)\s*=\s*\"([^\"]*)\"")
CSS_URL = re.compile(r"url\(\s*[\"']?([^\"')]+?)[\"']?\s*\)")
LOCAL_REF = re.compile(r"\b(?:href|src)\s*=\s*\"(?!#|data:|https?:)[^\"]+\"")


def is_local(reference: str) -> bool:
    parsed = urlsplit(reference)
    return not parsed.scheme and not reference.startswith(("#", "//"))


def resolve(base: Path, reference: str) -> Path:
    target = (base / unquote(urlsplit(reference).path)).resolve()
    assert target.is_file(), f"asset not found: {reference}"
    return target


def data_uri(path: Path) -> str:
    mime = MIME.get(path.suffix)
    assert mime, f"unknown asset type: {path.name}"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def inline_css(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert "@import" not in text, f"@import is not supported: {path.name}"
    assert "</style" not in text.lower(), f"CSS cannot be inlined as is: {path.name}"

    def replace(match: re.Match[str]) -> str:
        reference = match.group(1)
        if not is_local(reference):
            return match.group(0)
        return f'url("{data_uri(resolve(path.parent, reference))}")'

    return CSS_URL.sub(replace, text)


def replace_link(match: re.Match[str], base: Path) -> str:
    tag = match.group(0)
    attributes = dict(ATTRIBUTE.findall(tag))
    reference = attributes.get("href", "")
    if not reference or not is_local(reference):
        return tag
    relations = (attributes.get("rel") or "").split()
    if "stylesheet" in relations:
        return f"<style>\n{inline_css(resolve(base, reference))}</style>"
    if "icon" in relations:
        uri = data_uri(resolve(base, reference))
        return tag.replace(f'href="{attributes["href"]}"', f'href="{uri}"')
    raise SystemExit(f"unsupported link rel in project: {tag}")


def replace_script(match: re.Match[str], base: Path) -> str:
    attributes = dict(ATTRIBUTE.findall(match.group(1)))
    reference = attributes.get("src", "")
    if not reference or not is_local(reference):
        return match.group(0)
    text = resolve(base, reference).read_text(encoding="utf-8")
    body = text.replace("</script", "<\\/script")
    return f"<script>\n{body}\n</script>"


def bundle(index: Path) -> str:
    base = index.parent
    html = index.read_text(encoding="utf-8")
    html = LINK_TAG.sub(lambda match: replace_link(match, base), html)
    html = SCRIPT_TAG.sub(lambda match: replace_script(match, base), html)
    leftover = LOCAL_REF.search(html)
    assert not leftover, f"local asset left over: {leftover.group(0)}"
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project folder or path to index.html")
    parser.add_argument("--output", type=Path, help="Output file. Defaults to index.single.html next to the project")
    args = parser.parse_args()

    target = args.project.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    assert index.is_file(), f"index.html not found: {index}"
    output = (args.output or index.with_name("index.single.html")).expanduser().resolve()
    assert output != index, "output must not overwrite the source index.html"

    output.write_text(bundle(index), encoding="utf-8")
    size = output.stat().st_size
    print(f"Built standalone file: {output} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
