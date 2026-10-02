#!/usr/bin/env python3
"""Test the deck release archive: contents, drafts, cache busting, size limit and publishing."""

from __future__ import annotations

import functools
import http.server
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib import ROOT
from test_probe import GOOD, STATEMENT, build

RELEASE = ROOT / "scripts/release.py"


def release(*args: str | Path, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(RELEASE), *map(str, args)], cwd=ROOT, text=True, capture_output=True, timeout=900)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, "the release should have stopped"
    return result


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="craft-deck-release-") as directory:
        root = Path(directory)
        draft = STATEMENT.format(key="later", body='<h2 class="type-hero">Not ready yet</h2>').replace('data-key="later"', 'data-key="later" data-status="draft"')
        index = build(root, "deck", GOOD + draft)
        project = index.parent
        (project / "notes.md").write_text("speaker notes", encoding="utf-8")
        (project / "index.backup.html").write_text("<!doctype html>", encoding="utf-8")
        (project / "old").mkdir()
        (project / "old/collage.png").write_bytes(b"\0" * 4096)
        (project / "unused.webm").write_bytes((project / "clip.webm").read_bytes())
        out = root / "dist"

        stopped = release(project, "--out", out, "--check", "static", success=False)
        assert "draft slides" in stopped.stderr and "later" in stopped.stderr, stopped.stderr
        print("✓ a draft stops the release")

        index.write_text(index.read_text(encoding="utf-8").replace(' data-status="draft"', ""), encoding="utf-8")
        result = release(project, "--out", out, "--check", "render", "--limit-mb", "5")
        archive = out / "deck.zip"
        with zipfile.ZipFile(archive) as bundle:
            names = {name.removeprefix("deck/") for name in bundle.namelist()}
            packed = bundle.read("deck/index.html").decode("utf-8")
        for expected in ("index.html", "clip.webm", "clip-poster.png", "deck.js", "media.js", "base.css", "manifest.json", "README.txt"):
            assert expected in names, f"archive is missing {expected}"
        assert any(name.startswith("fonts/") for name in names), "archive is missing the fonts from CSS"
        for unexpected in ("notes.md", "index.backup.html", "old/collage.png", "unused.webm"):
            assert unexpected not in names, f"archive contains {unexpected}"
        assert 'src="deck.js?v=' in packed and 'src="clip.webm?v=' in packed, "links have no version query"
        assert "notes.md" in result.stdout, "the list of excluded files is not printed"
        print("✓ archive holds only used files, links carry a version query")

        small = release(project, "--out", root / "small", "--check", "static", "--limit-mb", "0.01", success=False)
        assert "limit" in small.stderr, small.stderr
        print("✓ the platform size limit is checked")

        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root / "site")
        site = root / "site/deck"
        manifest = site / "manifest.json"
        server, url = serve(site)
        try:
            release(manifest, "--published", url)
            (site / "base.css").write_text("/* old version */", encoding="utf-8")
            stale = release(manifest, "--published", url, success=False)
            assert "base.css" in stale.stderr, stale.stderr
        finally:
            server.shutdown()
        print("✓ the published version is checked against manifest")
    print("Done: deck release checked")


if __name__ == "__main__":
    main()
