#!/usr/bin/env python3
"""Создаёт автономный проект Craft из стартового шаблона выбранного формата."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "assets" / "shared"
INTERFACES = ROOT / "assets" / "interfaces"
SLIDES = ROOT / "assets" / "slides"


def copy_shared(target: Path) -> None:
    shutil.copy2(SHARED / "tokens.css", target / "tokens.css")
    shutil.copytree(SHARED / "fonts", target / "fonts", dirs_exist_ok=True)


def scaffold_interface(target: Path, template: str, title: str, lang: str, report_date: str) -> None:
    copy_shared(target)
    shutil.copy2(INTERFACES / "theme.css", target / "theme.css")

    if template == "design-system":
        shutil.copy2(INTERFACES / "specimen.css", target / "specimen.css")
        shutil.copy2(INTERFACES / "specimen.js", target / "specimen.js")
        html = (INTERFACES / "specimen.html").read_text(encoding="utf-8")
        html = html.replace('href="../shared/tokens.css"', 'href="tokens.css"', 1)
    else:
        html = (INTERFACES / "starter-index.html").read_text(encoding="utf-8")
        html = html.replace('href="../shared/tokens.css"', 'href="tokens.css"', 1)
        html = html.replace("{{TITLE}}", title)
        html = html.replace("{{DATE}}", report_date)

    html = html.replace('lang="ru"', f'lang="{lang}"', 1)
    (target / "index.html").write_text(html, encoding="utf-8")


def scaffold_slides(target: Path, title: str, lang: str) -> None:
    copy_shared(target)
    for name in ("base.css", "theme.css", "deck.js", "code-highlight.js", "code-source.js"):
        output_name = "slides.css" if name == "theme.css" else name
        shutil.copy2(SLIDES / name, target / output_name)
    shutil.copytree(SLIDES / "vendor", target / "vendor", dirs_exist_ok=True)

    html = (SLIDES / "starter/index.html").read_text(encoding="utf-8")
    replacements = {
        'href="../../shared/tokens.css"': 'href="tokens.css"',
        'href="../base.css"': 'href="base.css"',
        'href="../theme.css"': 'href="slides.css"',
        'src="../vendor/highlight.min.js"': 'src="vendor/highlight.min.js"',
        'src="../code-highlight.js"': 'src="code-highlight.js"',
        'src="../deck.js"': 'src="deck.js"',
    }
    for source, output in replacements.items():
        html = html.replace(source, output, 1)
    html = html.replace("{{TITLE}}", title)
    html = html.replace('lang="ru"', f'lang="{lang}"', 1)
    (target / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path, help="Новая или пустая целевая папка")
    parser.add_argument("--surface", choices=("interface", "slides"), default="interface")
    parser.add_argument("--template", choices=("report", "design-system", "deck", "slides"))
    parser.add_argument("--title", default=None)
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--date", default=date.today().isoformat(), help="Дата отчёта в формате ГГГГ-ММ-ДД")
    args = parser.parse_args()

    template = args.template or ("deck" if args.surface == "slides" else "report")
    if template == "slides":
        template = "deck"
    if args.surface == "interface" and template not in {"report", "design-system"}:
        parser.error("формат interface поддерживает шаблоны report и design-system")
    if args.surface == "slides" and template != "deck":
        parser.error("формат slides поддерживает шаблон deck")

    title = args.title or ("Новая презентация" if args.surface == "slides" else "Локальный отчёт")
    target = args.target.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Непустая папка не будет перезаписана: {target}")
    target.mkdir(parents=True, exist_ok=True)

    if args.surface == "slides":
        scaffold_slides(target, title, args.lang)
    else:
        scaffold_interface(target, template, title, args.lang, args.date)

    print(f"Создан проект Craft формата {args.surface}: {target / 'index.html'}")


if __name__ == "__main__":
    main()
