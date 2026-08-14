#!/usr/bin/env python3
"""Обновляет или сравнивает эталонные снимки Craft через ImageMagick."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lib import ROOT, run

BASELINE = ROOT / "tests/visual/baseline"


def image_compare() -> str:
    found = shutil.which("compare")
    if not found:
        raise SystemExit("Для визуального сравнения требуется команда compare из ImageMagick")
    return found


def render(output: Path) -> None:
    run(sys.executable, ROOT / "scripts/render.py", "--output", output, "--clean")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Заменить проверенные визуальные эталоны")
    parser.add_argument("--threshold", type=float, default=0.002, help="Допустимая нормализованная средняя разница")
    parser.add_argument("--diff-output", type=Path, default=ROOT / "artifacts/diff")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="craft-visual-") as directory:
        current = Path(directory) / "render"
        render(current)
        images = sorted(current.glob("*.png"))
        assert images, "рендерер не создал файлы PNG"

        if args.update:
            BASELINE.mkdir(parents=True, exist_ok=True)
            for old in BASELINE.glob("*.png"):
                old.unlink()
            for image in images:
                shutil.copy2(image, BASELINE / image.name)
            print(f"Готово: обновлено визуальных эталонов: {len(images)}; папка: {BASELINE.relative_to(ROOT)}")
            return

        if not BASELINE.is_dir():
            raise SystemExit("Визуальных эталонов нет. Запустите `make visual-update`, проверьте результат и зафиксируйте его в Git.")

        args.diff_output.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        compare = image_compare()
        for image in images:
            baseline = BASELINE / image.name
            if not baseline.is_file():
                failures.append(f"отсутствует эталон: {image.name}")
                continue
            diff = args.diff_output / image.name
            process = subprocess.run(
                [compare, "-metric", "MAE", baseline, image, diff],
                text=True,
                capture_output=True,
            )
            metric = (process.stderr or process.stdout).strip().splitlines()[-1]
            normalized = re.search(r"\(([^)]+)\)", metric)
            ratio = float(normalized.group(1) if normalized else metric.split()[0])
            status = "✓" if ratio <= args.threshold else "✗"
            print(f"{status} {image.name}: {ratio:.3%}")
            if ratio > args.threshold:
                failures.append(f"{image.name}: {ratio:.3%} > {args.threshold:.3%}")

        extra = {path.name for path in BASELINE.glob("*.png")} - {path.name for path in images}
        failures.extend(f"устаревший эталон: {name}" for name in sorted(extra))
        if failures:
            raise SystemExit("Обнаружены визуальные изменения:\n- " + "\n- ".join(failures))

    print("Готово: визуальных изменений нет")


if __name__ == "__main__":
    main()
