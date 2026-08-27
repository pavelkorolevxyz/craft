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
    "interface-starter": "Минимальный интерфейсный стартер",
    "interface-catalog-dark": "Каталог интерфейсов · тёмная тема",
    "interface-catalog-mobile": "Каталог интерфейсов · мобильный экран",
    "interface-catalog-light": "Каталог интерфейсов · светлая тема",
    "catalog-atoms-dark": "Атомы · неполный ряд · тёмная тема",
    "catalog-atoms-light": "Атомы · неполный ряд · светлая тема",
    "catalog-atoms-mobile": "Атомы · мобильный экран",
    "catalog-organisms-dark": "Организмы · две ячейки в последнем ряду",
    "slides-starter": "Минимальная колода",
    "slides-catalog-cover": "Каталог слайдов · титульная раскладка",
    "slides-catalog-content": "Каталог слайдов · содержимое",
    "slides-catalog-code": "Каталог слайдов · акцентная подсветка кода",
    "slides-catalog-recording": "Каталог слайдов · мобильная запись",
    "slides-catalog-grid": "Каталог слайдов · обзор сеткой",
    "slides-case-study-cover": "Мини-колода Craft · обложка",
    "slides-case-study-grid": "Мини-колода Craft · связный обзор",
    "slides-case-study-recording": "Мини-колода Craft · мобильная запись",
}

SHOTS = (
    Shot("interface-blank", "interface-starter", 1440, 900, "?theme=dark"),
    Shot("interface-catalog", "interface-catalog-dark", 1440, 900, "?theme=dark"),
    Shot("interface-catalog", "interface-catalog-mobile", 390, 844, "?theme=dark"),
    Shot("interface-catalog", "interface-catalog-light", 1440, 900, "?theme=light"),
    Shot("catalog-grid", "catalog-atoms-dark", 1200, 1200, "?theme=dark"),
    Shot("catalog-grid", "catalog-atoms-light", 1200, 1200, "?theme=light"),
    Shot("catalog-grid", "catalog-atoms-mobile", 390, 844, "?theme=dark"),
    Shot("catalog-grid", "catalog-organisms-dark", 900, 1200, "?theme=dark"),
    Shot("slides-deck", "slides-starter", 1280, 720, "#1"),
    Shot("slides-catalog", "slides-catalog-cover", 1280, 720, "#1"),
    Shot("slides-catalog", "slides-catalog-content", 1280, 720, "#5"),
    Shot("slides-catalog", "slides-catalog-code", 1280, 720, "?theme=dark#25"),
    Shot("slides-catalog", "slides-catalog-recording", 390, 844, "#1"),
    Shot("slides-catalog", "slides-catalog-grid", 1440, 900, "?view=grid#1"),
    Shot("slides-case-study", "slides-case-study-cover", 1280, 720, "?theme=light#1"),
    Shot("slides-case-study", "slides-case-study-grid", 1440, 900, "?theme=light&view=grid#1"),
    Shot("slides-case-study", "slides-case-study-recording", 390, 844, "?theme=light#4"),
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
        sources = {
            **{key: path / "index.html" for key, path in projects.items()},
            "interface-catalog": ROOT / "catalog/interfaces/sheet.html",
            "catalog-grid": ROOT / "tests/fixtures/interface-catalog-grid.html",
            "slides-catalog": ROOT / "catalog/slides/index.html",
            "slides-case-study": ROOT / "catalog/slides/case-study.html",
        }
        rendered: list[tuple[Shot, Path]] = []
        for shot in SHOTS:
            target = output / f"{shot.name}.png"
            screenshot(sources[shot.project], target, shot.width, shot.height, shot.suffix)
            rendered.append((shot, target))
            print(f"✓ {target.relative_to(output.parent)}")

        pdf = output / "slides.pdf"
        run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", sources["slides-catalog"].as_uri())
        assert pdf.stat().st_size > 30_000
        write_gallery(output, rendered)

    print(f"Готово: галерея проверки {output / 'index.html'}")


if __name__ == "__main__":
    main()
