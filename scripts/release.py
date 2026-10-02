#!/usr/bin/env python3
"""Releases a finished Craft deck or page as an archive for the host.

    python3 scripts/release.py ./output/talk --out ./dist --limit-mb 32 --pdf
    python3 scripts/release.py ./output/talk --published https://example.com/talk/

The command:
- takes only the files the material links to: HTML, CSS, scripts,
  posters, video sources, fonts. Notes, backups, alternative decks
  and draft artifacts stay out of the archive, and it prints their list;
- refuses to release draft slides and unfilled placeholders;
- appends ?v=<hash> to links so a host with a long cache serves
  fresh CSS and scripts;
- writes manifest.json with the date, commit and hashes, plus README.txt for the organizer;
- prints the size and the heaviest files, and checks the host limit;
- unpacks the archive into a clean folder and checks it over file:// with no network;
- with --published, compares the published files with the manifest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from lib import MANIFEST, ROOT

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_URL = re.compile(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+([\"'])([^\"']+)\1", re.I)
JS_PATH = re.compile(r"[\"'`]([\w./-]+\.(?:png|jpe?g|webp|avif|gif|svg|mp4|webm|mov|m4v|ogg|mp3|wav|vtt|json|woff2?))[\"'`]")
REFERENCE_ATTRIBUTES = {"href", "src", "poster", "data", "srcset"}


class References(HTMLParser):
    """Collects HTML links: asset attributes and any path-like values."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str, str]] = []  # (tag, attribute, value)
        self.styles: list[str] = []
        self.in_style = False
        self.draft: list[str] = []
        self.placeholders = 0
        self.in_slide = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        classes = values.get("class", "").split()
        if tag == "section" and "slide" in classes and values.get("data-status") == "draft":
            self.draft.append(values.get("data-key") or "no key")
        if "placeholder" in classes:
            self.placeholders += 1
        if tag == "style":
            self.in_style = True
        if values.get("style"):
            self.styles.append(values["style"])
        for name, value in values.items():
            if not value:
                continue
            if name == "srcset":
                for candidate in value.split(","):
                    if candidate.strip():
                        self.found.append((tag, name, candidate.strip().split()[0]))
            elif name in REFERENCE_ATTRIBUTES or name.startswith("data-"):
                self.found.append((tag, name, value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.styles.append(data)


def local_target(root: Path, base: Path, value: str) -> Path | None:
    reference = value.strip()
    if not reference or reference.startswith(("#", "data:", "blob:", "mailto:", "tel:", "javascript:")):
        return None
    parts = urlsplit(reference)
    if parts.scheme or reference.startswith("//"):
        return None
    target = (base / unquote(parts.path)).resolve()
    if target == root or root not in target.parents or not target.is_file():
        return None
    return target


def collect(index: Path) -> tuple[set[Path], References]:
    root = index.parent
    parser = References()
    parser.feed(index.read_text(encoding="utf-8"))
    files = {index}
    queue: list[Path] = []
    for _, _, value in parser.found:
        target = local_target(root, root, value)
        if target and target not in files:
            files.add(target)
            queue.append(target)
    for style in parser.styles:
        for match in [*CSS_URL.finditer(CSS_COMMENT.sub("", style)), *CSS_IMPORT.finditer(style)]:
            target = local_target(root, root, match.group(2))
            if target and target not in files:
                files.add(target)
                queue.append(target)
    while queue:
        path = queue.pop()
        if path.suffix == ".css":
            text = CSS_COMMENT.sub("", path.read_text(encoding="utf-8"))
            values = [match.group(2) for match in [*CSS_URL.finditer(text), *CSS_IMPORT.finditer(text)]]
        elif path.suffix in {".js", ".mjs"}:
            # A script may build a media path itself. Take only strings
            # that point to existing project files.
            values = [match.group(1) for match in JS_PATH.finditer(path.read_text(encoding="utf-8"))]
        else:
            continue
        for value in values:
            base = path.parent if path.suffix == ".css" else root
            target = local_target(root, base, value) or local_target(root, root, value)
            if target and target not in files:
                files.add(target)
                queue.append(target)
    return files, parser


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def version_references(text: str, base: Path, root: Path, hashes: dict[Path, str], css: bool) -> str:
    """Appends ?v=<hash> to local links so the host cache does not serve an old file."""

    def versioned(value: str, relative_to: Path) -> str:
        target = local_target(root, relative_to, value)
        if not target or target not in hashes:
            return value
        parts = urlsplit(value)
        query = f"v={hashes[target][:10]}"
        fragment = f"#{parts.fragment}" if parts.fragment else ""
        return f"{parts.path}?{query}{fragment}"

    if css:
        text = CSS_URL.sub(lambda match: f"url({match.group(1)}{versioned(match.group(2), base)}{match.group(1)})", text)
        return CSS_IMPORT.sub(lambda match: f"@import {match.group(1)}{versioned(match.group(2), base)}{match.group(1)}", text)
    pattern = re.compile(r'(\s(?:href|src|poster|data)=")([^"]+)(")')
    text = pattern.sub(lambda match: match.group(1) + versioned(match.group(2), root) + match.group(3), text)
    return re.sub(r"url\(([\"']?)([^\"')]+)\1\)", lambda match: f"url({match.group(1)}{versioned(match.group(2), root)}{match.group(1)})", text)


def git_state(path: Path) -> dict[str, object]:
    try:
        sha = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--", "."], check=True, text=True, capture_output=True).stdout.strip())
        return {"commit": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def human(size: int) -> str:
    return f"{size / 1024 / 1024:.1f} MB" if size >= 1024 * 1024 else f"{size / 1024:.0f} KB"


ORGANIZER = """{title}

How to open
1. Unpack the whole archive. Do not open files straight from the archive.
2. Open index.html in Chrome, Firefox or Edge. No internet needed.
3. Press F for full screen.
4. If a video does not start on its own, click it once.

Controls
Forward: right arrow, Space, PageDown or a clicker.
Back: left arrow or PageUp.
To the start: Home. Key help: H.

Pages on screen: {pages}. Archive size: {size}.
Built {date}{commit}.
"""


def build(args: argparse.Namespace) -> Path:
    source = args.project.expanduser().resolve()
    index = source / "index.html" if source.is_dir() else source
    if not index.is_file():
        raise SystemExit(f"index.html not found: {index}")
    root = index.parent
    files, parser = collect(index)

    problems: list[str] = []
    if parser.draft and not args.allow_draft:
        problems.append(f"draft slides (data-status=\"draft\"): {', '.join(parser.draft)}. Finish them, mark them skip or pass --allow-draft")
    if parser.placeholders and not args.allow_draft:
        problems.append(f"unfilled .placeholder elements: {parser.placeholders}")
    if problems:
        raise SystemExit("Release stopped:\n  " + "\n  ".join(problems))

    everything = {path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts}
    excluded = sorted(everything - files)
    hashes = {path: digest(path) for path in files}

    name = args.name or root.name
    out = args.out.expanduser().resolve()
    stage = out / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for path in sorted(files):
        target = stage / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".css":
            target.write_text(version_references(path.read_text(encoding="utf-8"), path.parent, root, hashes, css=True), encoding="utf-8")
        elif path == index:
            target.write_text(version_references(path.read_text(encoding="utf-8"), root, root, hashes, css=False), encoding="utf-8")
        else:
            shutil.copy2(path, target)

    title_match = re.search(r"<title>([^<]*)</title>", index.read_text(encoding="utf-8"))
    title = (title_match.group(1).strip() if title_match else name) or name
    pages = None
    report = None
    if not args.skip_check:
        # Check the built copy, with versioned links and without notes and backups.
        with tempfile.TemporaryDirectory(prefix="craft-release-report-") as directory:
            report_path = Path(directory) / "report.json"
            command = [sys.executable, str(ROOT / "scripts/check_project.py"), str(stage)]
            if args.check == "static":
                command.append("--static-only")
            else:
                command += ["--report", str(report_path)]
                if args.check == "full":
                    command.append("--full")
            result = subprocess.run(command, text=True, capture_output=True)
            print(result.stdout, end="")
            if result.returncode != 0:
                raise SystemExit(result.stderr.strip() or "the built copy failed the check")
            if report_path.is_file():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                pages = len(report["pages"])

    if args.pdf:
        pdf = stage / f"{name}.pdf"
        from lib import chromium_args
        subprocess.run([*chromium_args(1280, 720), f"--print-to-pdf={pdf}", (stage / "index.html").as_uri() + "?reveal=steps&motion=static"], check=True, capture_output=True)
        hashes[pdf] = digest(pdf)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    state = git_state(root)
    manifest = {
        "name": name,
        "title": title,
        "built": now,
        "craft": MANIFEST["version"],
        "source": state,
        "pages": pages,
        "files": {
            path.relative_to(stage).as_posix(): {"bytes": path.stat().st_size, "sha256": digest(path)}
            for path in sorted(stage.rglob("*")) if path.is_file()
        },
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    archive = out / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                bundle.write(path, f"{name}/{path.relative_to(stage).as_posix()}")
        size = archive.stat().st_size
        commit = f", commit {str(state['commit'])[:10]}{' with uncommitted changes' if state['dirty'] else ''}" if state["commit"] else ""
        readme = ORGANIZER.format(title=title, pages=pages or "?", size=human(size), date=now[:10], commit=commit)
        if args.readme:
            # The author's text for the organizer, with the build line at the end.
            readme = args.readme.read_text(encoding="utf-8").rstrip() + f"\n\nBuilt {now[:10]}{commit}.\n"
        bundle.writestr(f"{name}/README.txt", readme)
    (stage / "README.txt").write_text(readme, encoding="utf-8")

    # Check the archive the way the organizer gets it: unpacked into an
    # unrelated folder, with no source project nearby. The files are the ones
    # the browser already checked, so the contracts show whether every link
    # still resolves inside the archive.
    if not args.skip_check:
        with tempfile.TemporaryDirectory(prefix="craft-release-") as directory:
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(directory)
            unpacked = Path(directory) / name
            command = [sys.executable, str(ROOT / "scripts/check_project.py"), str(unpacked), "--static-only"]
            result = subprocess.run(command, text=True, capture_output=True)
            if result.returncode != 0:
                raise SystemExit(f"the unpacked archive failed the check:\n{result.stderr}")

    size = archive.stat().st_size
    total = sum(item["bytes"] for item in manifest["files"].values())
    print(f"\n✓ {archive}: {human(size)}, {human(total)} unpacked")
    heaviest = sorted(manifest["files"].items(), key=lambda item: item[1]["bytes"], reverse=True)[:8]
    print("Heaviest files:")
    for path, item in heaviest:
        print(f"  {human(item['bytes']):>9}  {path}")
    if report:
        seen: set[str] = set()
        for image in report.get("images", []):
            natural, needed = image["natural"][0], image["at1920"][0]
            source = image["src"].split("?", 1)[0]
            if source in seen or not natural or not needed:
                continue
            seen.add(source)
            if natural > needed * 2.5:
                print(f"  ! {source}: {natural} px but shown at up to {needed} px, can be smaller")
    if excluded:
        weight = sum(path.stat().st_size for path in excluded)
        print(f"Left out of the archive ({len(excluded)} files, {human(weight)}):")
        for path in excluded[:12]:
            print(f"  {path.relative_to(root)}")
        if len(excluded) > 12:
            print(f"  … and {len(excluded) - 12} more")
    if args.limit_mb and size > args.limit_mb * 1024 * 1024:
        raise SystemExit(f"archive is {human(size)}, over the host limit of {args.limit_mb} MB")
    return archive


def check_published(url: str, manifest_path: Path) -> None:
    """Compares the published files with the manifest, since the host may serve an old version."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = url if url.endswith("/") else url + "/"
    stale: list[str] = []
    for relative, item in manifest["files"].items():
        if relative in {"manifest.json", "README.txt"}:
            continue
        address = urljoin(base, relative) + f"?v={item['sha256'][:10]}"
        try:
            with urllib.request.urlopen(address, timeout=30) as response:
                body = response.read()
        except OSError as error:
            stale.append(f"{relative}: failed to open ({error})")
            continue
        # index.html and CSS on the host carry versioned links, as in the archive.
        if hashlib.sha256(body).hexdigest() != item["sha256"]:
            stale.append(f"{relative}: differs from the release")
    if stale:
        raise SystemExit("The published version differs from the release:\n  " + "\n  ".join(stale))
    print(f"✓ published version matches the manifest: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, help="Material folder or index.html")
    parser.add_argument("--out", type=Path, default=Path("dist"), help="Where to put the archive, ./dist by default")
    parser.add_argument("--name", help="Name of the archive and of the folder inside it")
    parser.add_argument("--limit-mb", type=float, help="Archive size limit on the host")
    parser.add_argument("--pdf", action="store_true", help="Add a PDF with all reveals to the archive")
    parser.add_argument("--readme", type=Path, help="Your own README.txt for the organizer instead of the default one")
    parser.add_argument("--allow-draft", action="store_true", help="Allow draft slides and placeholders")
    parser.add_argument("--check", choices=("static", "render", "full"), default="full",
                        help="How deeply to check the built copy: contracts, rendering, or everything (default)")
    parser.add_argument("--skip-check", action="store_true", help="Skip checking the built copy. For debugging only")
    parser.add_argument("--published", help="URL of the published version to compare with the manifest")
    args = parser.parse_args()

    if args.published and args.project.suffix == ".json":
        check_published(args.published, args.project)
        return
    archive = build(args)
    if args.published:
        check_published(args.published, archive.parent / archive.stem / "manifest.json")


if __name__ == "__main__":
    main()
