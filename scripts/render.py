#!/usr/bin/env python3
"""Создаёт воспроизводимую галерею для проверки всех форматов Craft."""

from __future__ import annotations

import argparse
import html
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from lib import ROOT, chromium_args, run, scaffold_matrix


@dataclass(frozen=True)
class Shot:
    project: str
    name: str
    width: int
    height: int
    suffix: str = ""


SHOT_LABELS = {
    "report-desktop": "Отчёт · широкий экран",
    "report-mobile": "Отчёт · мобильный экран",
    "system-desktop": "Каталог · широкий экран",
    "system-mobile": "Каталог · мобильный экран",
    "slides-cover": "Слайды · обложка",
    "slides-content": "Слайды · содержимое",
    "slides-recording": "Слайды · запись на мобильном экране",
    "slides-grid": "Слайды · обзор сеткой",
}

SHOTS = (
    Shot("interface-report", "report-desktop", 1440, 900),
    Shot("interface-report", "report-mobile", 500, 844),
    Shot("interface-design-system", "system-desktop", 1440, 900),
    Shot("interface-design-system", "system-mobile", 500, 844),
    Shot("slides-deck", "slides-cover", 1280, 720, "#1"),
    Shot("slides-deck", "slides-content", 1280, 720, "#5"),
    Shot("slides-deck", "slides-recording", 500, 844, "#1"),
    Shot("slides-deck", "slides-grid", 1440, 900, "?view=grid#1"),
)


def screenshot(source: Path, target: Path, width: int, height: int, suffix: str) -> None:
    run(
        *chromium_args(width, height),
        f"--screenshot={target}",
        source.as_uri() + suffix,
    )
    assert target.is_file() and target.stat().st_size > 4_000, f"пустой снимок {target}"


def write_gallery(output: Path, rendered: list[tuple[Shot, Path]]) -> None:
    figures = "\n".join(
        f'<figure><img src="{html.escape(path.name)}" alt="{html.escape(SHOT_LABELS[shot.name])}">'
        f'<figcaption>{html.escape(SHOT_LABELS[shot.name])} · {shot.width}×{shot.height}</figcaption></figure>'
        for shot, path in rendered
    )
    document = f"""<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Проверка рендеров Craft</title>
<style>
  * {{ box-sizing: border-box }}
  body {{ margin: 0; padding: 24px; color: #eee; background: #111; font: 14px/1.5 system-ui }}
  h1 {{ margin: 0 0 24px; font-size: 28px }}
  main {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,420px),1fr)); gap: 24px }}
  figure {{ margin: 0; border: 1px solid #333; background: #181818 }}
  img {{ display: block; width: 100%; height: auto }}
  figcaption {{ padding: 10px 12px; border-top: 1px solid #333; color: #aaa }}
</style>
<h1>Проверка рендеров Craft</h1><main>{figures}</main></html>"""
    (output / "index.html").write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/render")
    parser.add_argument("--clean", action="store_true", help="Сначала удалить целевую папку")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if args.clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="craft-render-") as directory:
        projects = scaffold_matrix(Path(directory))
        rendered: list[tuple[Shot, Path]] = []
        for shot in SHOTS:
            target = output / f"{shot.name}.png"
            screenshot(projects[shot.project] / "index.html", target, shot.width, shot.height, shot.suffix)
            rendered.append((shot, target))
            print(f"✓ {target.relative_to(output.parent)}")

        pdf = output / "slides.pdf"
        run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", projects["slides-deck"].joinpath("index.html").as_uri())
        assert pdf.stat().st_size > 30_000
        write_gallery(output, rendered)

    print(f"Готово: галерея проверки {output / 'index.html'}")


if __name__ == "__main__":
    main()
