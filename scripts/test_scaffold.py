#!/usr/bin/env python3
"""Создаёт все шаблоны Craft и проверяет их в Chromium."""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from lib import MANIFEST, chromium_args, run, scaffold_matrix


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            self.paths.append(values["href"] or "")
        if tag in {"script", "img", "source", "video"} and values.get("src"):
            self.paths.append(values["src"] or "")


def validate_output(key: str, output: Path) -> None:
    index = output / "index.html"
    assert index.is_file(), f"{key}: отсутствует index.html"
    assert (output / "tokens.css").is_file(), f"{key}: отсутствует tokens.css"
    expected_fonts = MANIFEST["requirements"]["fontFiles"]
    assert len(list((output / "fonts").glob("*.woff2"))) == expected_fonts

    html = index.read_text(encoding="utf-8")
    assert not re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", html), f"{key}: необработанная подстановка"
    parser = LocalAssetParser()
    parser.feed(html)
    for value in parser.paths:
        assert not value.startswith(("http://", "https://", "//")), f"{key}: внешний ресурс {value}"
        target = output / value.split("?", 1)[0].split("#", 1)[0]
        assert target.is_file(), f"{key}: сломанный ресурс {value}"


def dump_probe(output: Path, script: str, width: int, height: int) -> str:
    source = output / "index.html"
    probe = output / "__probe.html"
    html = source.read_text(encoding="utf-8")
    probe.write_text(html.replace("</body>", f"<script>{script}</script></body>"), encoding="utf-8")
    return run(
        *chromium_args(width, height),
        "--dump-dom",
        probe.as_uri(),
    ).stdout


def test_interfaces(key: str, output: Path) -> None:
    for width, height in ((1440, 900), (500, 844)):
        dumped = dump_probe(
            output,
            "document.title=`probe:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}`",
            width,
            height,
        )
        match = re.search(r"<title>probe:(\d+):(\d+):(\d+)</title>", dumped)
        assert match, f"{key}: браузерная проверка не выполнена"
        scroll_width, viewport, mains = map(int, match.groups())
        assert scroll_width <= viewport, f"{key}: горизонтальное переполнение при {width}px ({scroll_width}>{viewport})"
        assert mains == 1, f"{key}: ожидалась одна основная область main"


def test_slides(key: str, output: Path, work: Path) -> None:
    dumped = dump_probe(
        output,
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));"
        "const current=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const deck=document.querySelector('.deck');"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "deck.scrollTop=(deck.scrollHeight-deck.clientHeight)*.37;"
        "const stripBefore=Math.round(deck.scrollTop/(deck.scrollHeight-deck.clientHeight)*100);"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const stripAfter=Math.round(deck.scrollLeft/(deck.scrollWidth-deck.clientWidth)*100);"
        "deck.scrollLeft=(deck.scrollWidth-deck.clientWidth)*.62;"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const stripReturn=Math.round(deck.scrollTop/(deck.scrollHeight-deck.clientHeight)*100);"
        "document.title=`probe:${document.querySelectorAll('.slide').length}:${document.querySelectorAll('.slide[data-active]').length}:`+"
        "`${current}:${stripBefore}:${stripAfter}:${stripReturn}:${deck.dataset.stripDirection}`",
        1280,
        720,
    )
    match = re.search(r"<title>probe:(\d+):(\d+):(\d+):(\d+):(\d+):(\d+):(\w+)</title>", dumped)
    assert match, f"{key}: проверка механики колоды не выполнена"
    pages, active, current, strip_before, strip_after, strip_return = map(int, match.groups()[:6])
    strip_direction = match.group(7)
    assert pages >= 6 and active == 1 and current == 2, f"{key}: недопустимое состояние колоды {match.groups()}"
    assert strip_direction == "vertical" and strip_before == strip_after == 37 and strip_return == 62, f"{key}: позиция ленты не сохранена {match.groups()}"

    pdf = work / f"{key}.pdf"
    run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", output.joinpath("index.html").as_uri())
    assert pdf.is_file() and pdf.stat().st_size > 30_000, f"{key}: экспорт PDF не выполнен"
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        info = run(pdfinfo, pdf).stdout
        count = re.search(r"^Pages:\s+(\d+)", info, re.M)
        assert count and int(count.group(1)) == pages, f"{key}: количество страниц PDF отличается от механики колоды"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=Path, help="Сохранить созданные проекты в этой папке")
    args = parser.parse_args()

    context = None if args.keep else tempfile.TemporaryDirectory(prefix="craft-test-")
    root = args.keep.resolve() if args.keep else Path(context.name)
    root.mkdir(parents=True, exist_ok=True)
    try:
        outputs = scaffold_matrix(root / "projects")
        for key, output in outputs.items():
            validate_output(key, output)
            if key.startswith("interface-"):
                test_interfaces(key, output)
            else:
                test_slides(key, output, root)
            print(f"✓ {key}")
        print("Готово: создание проектов, поведение браузера, переполнение и экспорт PDF проверены")
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
