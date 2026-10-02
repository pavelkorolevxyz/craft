#!/usr/bin/env python3
"""Creates a standalone Craft project from the starter of the chosen format."""

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


def scaffold_interface(target: Path, title: str, lang: str, delivery: str, template: str) -> None:
    copy_shared(target, "favicon-interface.svg", delivery)
    shutil.copy2(INTERFACES / "theme.css", target / "theme.css")
    shutil.copy2(INTERFACES / "theme.js", target / "theme.js")
    shutil.copy2(INTERFACES / "section-nav.js", target / "section-nav.js")

    starter = "starter-bare.html" if template == "bare" else "starter-index.html"
    html = (INTERFACES / starter).read_text(encoding="utf-8")
    html = html.replace('href="../shared/favicon-interface.svg"', 'href="favicon.svg"', 1)
    html = html.replace('href="../shared/tokens.css"', 'href="tokens.css"', 1)
    html = html.replace("{{TITLE}}", escaped_title(title))
    html = html.replace('lang="en"', f'lang="{lang}"', 1)
    html = apply_delivery(html, delivery, '<link rel="stylesheet" href="tokens.css">')
    (target / "index.html").write_text(html, encoding="utf-8")


def cover_slide(title: str, author: str) -> str:
    fragment = (SLIDES / "fragments/cover.html").read_text(encoding="utf-8").rstrip()
    fragment = fragment.replace("{{TITLE}}", escaped_title(title)).replace("{{BYLINE}}", escaped_title(author))
    fragment = fragment.replace('data-slide-layout="cover">', 'data-slide-layout="cover" data-key="cover">', 1)
    return "\n".join("  " + line for line in fragment.splitlines())


def scaffold_slides(target: Path, title: str, lang: str, delivery: str, author: str | None) -> None:
    copy_shared(target, "favicon-slides.svg", delivery)
    for name in ("base.css", "theme.css", "deck.js", "media.js", "code-highlight.js", "code-source.js"):
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
        'src="../media.js"': 'src="media.js"',
    }
    for source, output in replacements.items():
        html = html.replace(source, output, 1)
    if author:
        # A talk with an author opens with a cover. The title card stays for material without a speaker.
        html = re.sub(r'  <section class="slide s-title-card".*?</section>', lambda _: cover_slide(title, author), html, count=1, flags=re.S)
    html = html.replace("{{TITLE}}", escaped_title(title))
    html = html.replace('lang="en"', f'lang="{lang}"', 1)
    html = apply_delivery(html, delivery, '<link rel="stylesheet" href="tokens.css">')
    (target / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path, help="New or empty target folder")
    parser.add_argument("--surface", choices=("interface", "slides"), default="interface")
    parser.add_argument("--template", choices=("blank", "bare", "deck", "slides"),
                        help="interface: blank with the shell (header, theme toggle) or bare with styles only")
    parser.add_argument("--title", default=None)
    parser.add_argument("--author", help="slides: talk author. The deck opens with the cover slide instead of the title card")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--delivery", choices=("local", "web"), default="local",
                        help="local: everything in the project folder. web: fonts from a CDN for publishing online")
    args = parser.parse_args()

    template = args.template or ("deck" if args.surface == "slides" else "blank")
    if template == "slides":
        template = "deck"
    if args.surface == "interface" and template not in ("blank", "bare"):
        parser.error("the interface format supports the blank and bare templates")
    if args.author and args.surface != "slides":
        parser.error("--author works only with slides")
    if args.surface == "slides" and template != "deck":
        parser.error("the slides format supports the deck template")

    title = args.title or ("New presentation" if args.surface == "slides" else "New page")
    if not LANGUAGE_TAG.fullmatch(args.lang):
        parser.error("--lang must be a language tag, for example en or ru-RU")
    target = args.target.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Will not overwrite a non-empty folder: {target}")
    target.mkdir(parents=True, exist_ok=True)

    if args.surface == "slides":
        scaffold_slides(target, title, args.lang, args.delivery, args.author)
    else:
        scaffold_interface(target, title, args.lang, args.delivery, template)

    print(f"Created Craft {args.surface} project: {target / 'index.html'}")


if __name__ == "__main__":
    main()
