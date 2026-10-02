#!/usr/bin/env python3
"""Builds the GitHub Pages site with the home page, the catalogs and the shared assets."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ("interface-showcase-dark.png", "interface-catalog-dark.png", "slides-catalog-grid.png", "slides-case-study-cover.png")
# Sample cards show the shots at about 300 px, so 720 px covers a 2x screen.
PREVIEW_WIDTH = 720


def preview(source: Path, target: Path) -> None:
    """Writes a WebP preview of a baseline screenshot with ImageMagick."""
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        raise SystemExit("pages.py needs ImageMagick (magick or convert) to build the previews")
    subprocess.run([tool, str(source), "-resize", f"{PREVIEW_WIDTH}x", "-quality", "80", str(target)], check=True)


def build(target: Path, repository: str) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in ("assets", "catalog"):
        shutil.copytree(ROOT / name, target / name)
    (target / "images").mkdir()
    for name in IMAGES:
        preview(ROOT / "tests/visual/baseline" / name, target / "images" / Path(name).with_suffix(".webp").name)

    # The home page lives in site/ and links to ../assets. On the site it sits at the root.
    home = (ROOT / "site/index.html").read_text(encoding="utf-8").replace('"../assets/', '"assets/')
    home = home.replace("https://github.com/OWNER/REPO", repository).replace("OWNER/REPO", repository.removeprefix("https://github.com/"))
    (target / "index.html").write_text(home, encoding="utf-8")

    # References and the README stay off the site. Links to them point to the repository.
    for page in (target / "catalog").rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        linked = re.sub(r'href="(?:\.\./)+((?:README|SKILL)\.md|references/[^"]+\.md)"',
                        lambda match: f'href="{repository}/blob/main/{match.group(1)}"', html)
        if linked != html:
            page.write_text(linked, encoding="utf-8")
    (target / ".nojekyll").write_text("", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/pages")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"),
                        help="GitHub repository as owner/name. In Actions it comes from GITHUB_REPOSITORY")
    args = parser.parse_args()
    if not args.repository:
        parser.error("pass --repository owner/name")
    build(args.out.resolve(), f"https://github.com/{args.repository}")
    print(f"Done: site built in {args.out}")


if __name__ == "__main__":
    main()
