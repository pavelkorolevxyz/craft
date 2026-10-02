"""Shared helpers for the Craft development commands."""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MANIFEST = json.loads((ROOT / "scripts/craft.json").read_text(encoding="utf-8"))


def run(*args: str | Path, cwd: Path = ROOT, capture: bool = True) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=capture)


def chromium() -> str:
    configured = os.environ.get("CHROMIUM")
    found = configured or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not found:
        raise SystemExit("Chromium is required. If it is not on PATH, set CHROMIUM=/path/to/browser.")
    return found


def node() -> str:
    found = shutil.which("node")
    if not found:
        raise SystemExit("Node.js is required to check JavaScript syntax.")
    return found


class BrowserSession:
    """One Chromium for a test run instead of a cold start per page (browser_session.mjs)."""

    _shared: "BrowserSession | None" = None

    def __init__(self) -> None:
        self.process = subprocess.Popen(
            [node(), str(ROOT / "scripts/browser_session.mjs")],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        atexit.register(self.close)

    @classmethod
    def shared(cls) -> "BrowserSession":
        if cls._shared is None or cls._shared.process.poll() is not None:
            cls._shared = cls()
        return cls._shared

    def request(self, **payload: object) -> dict:
        assert self.process.stdin and self.process.stdout
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        answer = json.loads(self.process.stdout.readline() or "{}")
        if "error" in answer or not answer:
            raise AssertionError(f"browser session: {answer.get('error', 'no answer')}")
        return answer

    def dump(self, url: str, width: int, height: int, title: str = "") -> str:
        """The DOM once the page has set a new title, like chromium --dump-dom."""
        return self.request(op="dump", url=url, width=width, height=height, title=title)["html"]

    def pdf(self, url: str, target: Path, width: int, height: int) -> int:
        return self.request(op="pdf", url=url, width=width, height=height, path=str(target))["bytes"]

    def shot(self, url: str, target: Path, width: int, height: int) -> int:
        return self.request(op="shot", url=url, width=width, height=height, path=str(target))["bytes"]

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def scaffold(target: Path, surface: str, template: str, title: str = "Craft check") -> None:
    args: list[str | Path] = [
        sys.executable,
        ROOT / "scripts/scaffold.py",
        target,
        "--surface",
        surface,
        "--template",
        template,
        "--title",
        title,
    ]
    run(*args)


def scaffold_matrix(root: Path) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    for surface, definition in MANIFEST["surfaces"].items():
        for template in definition["templates"]:
            key = f"{surface}-{template}"
            target = root / key
            scaffold(target, surface, template)
            outputs[key] = target
    return outputs


def chromium_args(width: int, height: int) -> list[str]:
    return [
        chromium(),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=1200",
        f"--window-size={width},{height}",
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
