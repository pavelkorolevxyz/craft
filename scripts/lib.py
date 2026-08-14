"""Общие вспомогательные функции для команд разработки Craft."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MANIFEST = json.loads((ROOT / "craft.json").read_text(encoding="utf-8"))


def run(*args: str | Path, cwd: Path = ROOT, capture: bool = True) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=capture)


def chromium() -> str:
    configured = os.environ.get("CHROMIUM")
    found = configured or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not found:
        raise SystemExit("Требуется Chromium. Если браузера нет в PATH, укажите CHROMIUM=/путь/к/браузеру.")
    return found


def node() -> str:
    found = shutil.which("node")
    if not found:
        raise SystemExit("Для проверки синтаксиса JavaScript требуется Node.js.")
    return found


def scaffold(target: Path, surface: str, template: str, title: str = "Проверка Craft") -> None:
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
        "--date",
        "2026-01-01",
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
