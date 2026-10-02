#!/usr/bin/env python3
"""Print the deck map: page number to slide key, reveal step and title.

    python3 scripts/deck_map.py ./output/talk            # the whole map
    python3 scripts/deck_map.py ./output/talk 19 20      # only these pages
    python3 scripts/deck_map.py ./output/talk --final    # page numbers in final mode
    python3 scripts/deck_map.py ./output/talk --json

Page numbers change every time slides move. The data-key stays with its
source slide. Before an edit by page number, resolve the number to a key and
put the triple "key, step, title" in the edit report. No browser is needed.
The script reads the source the same way deck.js builds the map.
"""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[dict] = []
        self.depth = 0
        self.current: dict | None = None
        self.title_depth: int | None = None
        self.in_slides = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag in {"br", "img", "source", "meta", "link", "input", "hr", "wbr", "col", "area", "track", "embed"}:
            return
        self.depth += 1
        if self.current is None and tag == "section" and "slide" in classes:
            self.current = {
                "key": values.get("data-key"),
                "layout": values.get("data-slide-layout"),
                "status": values.get("data-status"),
                "local": values.get("data-composition") == "local",
                "frags": 0,
                "title": "",
                "depth": self.depth,
            }
            return
        if self.current is None:
            return
        if "frag" in classes and (not self.current["frags"] or values.get("data-frag") != "with-previous"):
            self.current["frags"] += 1
        if not self.current["title"] and self.title_depth is None and (tag in {"h1", "h2", "h3"} or "slide-title" in classes):
            self.title_depth = self.depth

    def handle_endtag(self, tag: str) -> None:
        if self.current is not None and self.title_depth == self.depth:
            self.title_depth = None
            self.current["title"] = re.sub(r"\s+", " ", self.current["title"]).strip() or " "
        if self.current is not None and tag == "section" and self.current["depth"] == self.depth:
            self.current["title"] = self.current["title"].strip()
            del self.current["depth"]
            self.slides.append(self.current)
            self.current = None
        self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.title_depth is not None:
            self.current["title"] += data


def deck_map(index: Path, final: bool = False, show_skipped: bool = False) -> list[dict]:
    parser = DeckParser()
    parser.feed(index.read_text(encoding="utf-8"))
    pages: list[dict] = []
    for number, slide in enumerate(parser.slides, start=1):
        if slide["status"] == "skip" and not show_skipped:
            continue
        key = slide["key"] or f"slide-{number}"
        steps = slide["frags"]
        for step in range(steps if final else 0, steps + 1):
            pages.append({
                "page": len(pages) + 1,
                "key": key,
                "keyMissing": not slide["key"],
                "step": step,
                "steps": steps,
                "layout": slide["layout"],
                "status": slide["status"],
                "title": slide["title"],
            })
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, help="Deck folder or index.html")
    parser.add_argument("pages", nargs="*", type=int, help="Page numbers to resolve")
    parser.add_argument("--final", action="store_true", help="Page numbers in ?reveal=final mode")
    parser.add_argument("--skipped", action="store_true", help="Count data-status=\"skip\" slides")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    target = args.project.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    if not index.is_file():
        raise SystemExit(f"index.html not found: {index}")
    pages = deck_map(index, args.final, args.skipped)
    if args.pages:
        wanted = set(args.pages)
        missing = wanted - {item["page"] for item in pages}
        if missing:
            raise SystemExit(f"the deck has {len(pages)} pages, missing: {', '.join(map(str, sorted(missing)))}")
        pages = [item for item in pages if item["page"] in wanted]
    if args.json:
        print(json.dumps(pages, ensure_ascii=False, indent=2))
        return
    for item in pages:
        step = f"{item['step']}/{item['steps']}" if item["steps"] else "-"
        status = f" [{item['status']}]" if item["status"] else ""
        warning = " (no data-key)" if item["keyMissing"] else ""
        print(f"{item['page']:>4}  #{item['key']}/{item['step']}  step {step:<5} {item['layout'] or '?':<18} {item['title']}{status}{warning}")


if __name__ == "__main__":
    main()
