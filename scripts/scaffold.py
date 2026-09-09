#!/usr/bin/env python3
"""Создаёт автономный проект Craft из стартового шаблона выбранного формата."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "assets" / "shared"
INTERFACES = ROOT / "assets" / "interfaces"
SLIDES = ROOT / "assets" / "slides"
LANGUAGE_TAG = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*")
FONT_FACE = re.compile(r"@font-face\s*\{[^}]*\}\n?")
WEB_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
    '?family=Geologica:wght@300..700&amp;family=Onest:wght@400..600&amp;display=swap">'
)


def escaped_title(value: str) -> str:
    return html.escape(value, quote=True)


def copy_shared(target: Path, favicon: str, delivery: str) -> None:
    tokens = (SHARED / "tokens.css").read_text(encoding="utf-8")
    if delivery == "web":
        tokens = FONT_FACE.sub("", tokens)
    else:
        shutil.copytree(SHARED / "fonts", target / "fonts", dirs_exist_ok=True)
    (target / "tokens.css").write_text(tokens, encoding="utf-8")
    shutil.copy2(SHARED / favicon, target / "favicon.svg")


def apply_delivery(html: str, delivery: str, tokens_link: str) -> str:
    if delivery != "web":
        return html
    html = html.replace("<html lang=", '<html data-craft-delivery="web" lang=', 1)
    indent = html.split(tokens_link, 1)[0].rsplit("\n", 1)[1]
    links = WEB_FONT_LINKS.replace("\n", "\n" + indent)
    return html.replace(tokens_link, links + "\n" + indent + tokens_link, 1)


def scaffold_interface(target: Path, title: str, lang: str, delivery: str) -> None:
    copy_shared(target, "favicon-interface.svg", delivery)
    shutil.copy2(INTERFACES / "theme.css", target / "theme.css")
    shutil.copy2(INTERFACES / "theme.js", target / "theme.js")
    shutil.copy2(INTERFACES / "section-nav.js", target / "section-nav.js")

    html = (INTERFACES / "starter-index.html").read_text(encoding="utf-8")
    html = html.replace('href="../shared/favicon-interface.svg"', 'href="favicon.svg"', 1)
    html = html.replace('href="../shared/tokens.css"', 'href="tokens.css"', 1)
    html = html.replace("{{TITLE}}", escaped_title(title))
    html = html.replace('lang="ru"', f'lang="{lang}"', 1)
    html = apply_delivery(html, delivery, '<link rel="stylesheet" href="tokens.css">')
    (target / "index.html").write_text(html, encoding="utf-8")


def scaffold_slides(target: Path, title: str, lang: str, delivery: str) -> None:
    copy_shared(target, "favicon-slides.svg", delivery)
    for name in ("base.css", "theme.css", "deck.js", "code-highlight.js", "code-source.js"):
        output_name = "slides.css" if name == "theme.css" else name
        shutil.copy2(SLIDES / name, target / output_name)
    shutil.copytree(SLIDES / "vendor", target / "vendor", dirs_exist_ok=True)

    html = (SLIDES / "starter/index.html").read_text(encoding="utf-8")
    replacements = {
        'href="../../shared/favicon-slides.svg"': 'href="favicon.svg"',
        'href="../../shared/tokens.css"': 'href="tokens.css"',
        'href="../base.css"': 'href="base.css"',
        'href="../theme.css"': 'href="slides.css"',
        'src="../vendor/highlight.min.js"': 'src="vendor/highlight.min.js"',
        'src="../code-highlight.js"': 'src="code-highlight.js"',
        'src="../deck.js"': 'src="deck.js"',
    }
    for source, output in replacements.items():
        html = html.replace(source, output, 1)
    html = html.replace("{{TITLE}}", escaped_title(title))
    html = html.replace('lang="ru"', f'lang="{lang}"', 1)
    html = apply_delivery(html, delivery, '<link rel="stylesheet" href="tokens.css">')
    (target / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path, help="Новая или пустая целевая папка")
    parser.add_argument("--surface", choices=("interface", "slides"), default="interface")
    parser.add_argument("--template", choices=("blank", "deck", "slides"))
    parser.add_argument("--title", default=None)
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--delivery", choices=("local", "web"), default="local",
                        help="local: всё в папке проекта; web: шрифты с CDN для публикации в интернете")
    args = parser.parse_args()

    template = args.template or ("deck" if args.surface == "slides" else "blank")
    if template == "slides":
        template = "deck"
    if args.surface == "interface" and template != "blank":
        parser.error("формат interface поддерживает только минимальный шаблон blank")
    if args.surface == "slides" and template != "deck":
        parser.error("формат slides поддерживает шаблон deck")

    title = args.title or ("Новая презентация" if args.surface == "slides" else "Новый материал")
    if not LANGUAGE_TAG.fullmatch(args.lang):
        parser.error("--lang должен быть языковым тегом, например ru или en-US")
    target = args.target.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Непустая папка не будет перезаписана: {target}")
    target.mkdir(parents=True, exist_ok=True)

    if args.surface == "slides":
        scaffold_slides(target, title, args.lang, args.delivery)
    else:
        scaffold_interface(target, title, args.lang, args.delivery)

    print(f"Создан проект Craft формата {args.surface}: {target / 'index.html'}")


if __name__ == "__main__":
    main()
