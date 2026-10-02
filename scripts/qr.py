#!/usr/bin/env python3
"""Create a QR code for a slide: inline SVG with currentColor and the encoded value.

    python3 scripts/qr.py https://example.com            # SVG to stdout
    python3 scripts/qr.py https://example.com --link     # .qr-link block with a visible link

Requires qrencode. The script draws the modules as one currentColor path, so
they take the color of the .qr border in both themes. The data-qr attribute holds the
encoded value. The deck probe compares it with the link address and reads the
code with a scanner.
"""

from __future__ import annotations

import argparse
import html
import shutil
import subprocess


def matrix(value: str, level: str) -> list[list[bool]]:
    binary = shutil.which("qrencode")
    if not binary:
        raise SystemExit("qrencode is required: sudo apt install qrencode or brew install qrencode")
    output = subprocess.run(
        [binary, "-t", "ASCII", "-m", "0", "-l", level, value],
        check=True, text=True, capture_output=True,
    ).stdout
    rows = [line for line in output.splitlines() if line.strip()]
    # In ASCII mode each module takes two characters.
    return [[line[column] == "#" for column in range(0, len(line), 2)] for line in rows]


def svg(value: str, quiet: int = 2, level: str = "M") -> str:
    modules = matrix(value, level)
    size = len(modules) + quiet * 2
    runs: list[str] = []
    for y, row in enumerate(modules):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue
            start = x
            while x < len(row) and row[x]:
                x += 1
            runs.append(f"M{start + quiet} {y + quiet + 0.5:g}h{x - start}")
    escaped = html.escape(value, quote=True)
    return (
        f'<svg viewBox="0 0 {size} {size}" role="img" aria-label="QR: {escaped}" data-qr="{escaped}" shape-rendering="crispEdges">'
        f'<path fill="none" stroke="currentColor" d="{"".join(runs)}"/></svg>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("value", help="URL or text to encode")
    parser.add_argument("--quiet", type=int, default=2, help="Quiet zone around the matrix, in modules (default 2)")
    parser.add_argument("--level", choices=("L", "M", "Q", "H"), default="M", help="Error correction level")
    parser.add_argument("--link", action="store_true", help="Print a .qr-link block with a clickable address next to the code")
    args = parser.parse_args()
    code = svg(args.value, args.quiet, args.level)
    if args.link:
        shown = html.escape(args.value.removeprefix("https://").removeprefix("http://").rstrip("/"))
        href = html.escape(args.value, quote=True)
        code = f'<div class="qr-link">\n  <div class="qr">{code}</div>\n  <a href="{href}"><p class="where">{shown}</p></a>\n</div>'
    print(code)


if __name__ == "__main__":
    main()
