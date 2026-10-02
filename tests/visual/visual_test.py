#!/usr/bin/env python3
"""Updates or compares Craft baseline screenshots with ImageMagick."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from lib import ROOT, run

BASELINE = ROOT / "tests/visual/baseline"


def image_compare() -> str:
    found = shutil.which("compare")
    if not found:
        raise SystemExit("Visual comparison needs the compare command from ImageMagick")
    return found


def render(output: Path) -> None:
    run(sys.executable, ROOT / "scripts/render.py", "--output", output, "--clean")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Replace the reviewed visual baselines")
    parser.add_argument("--threshold", type=float, default=0.002, help="Allowed normalized mean difference")
    parser.add_argument("--diff-output", type=Path, default=ROOT / "artifacts/diff")
    parser.add_argument("--rendered", type=Path, help="Compare an existing render.py output instead of rendering again")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="craft-visual-") as directory:
        current = args.rendered.expanduser().resolve() if args.rendered else Path(directory) / "render"
        if not args.rendered:
            render(current)
        images = sorted(current.glob("*.png"))
        assert images, "renderer produced no PNG files"

        if args.update:
            BASELINE.mkdir(parents=True, exist_ok=True)
            for old in BASELINE.glob("*.png"):
                old.unlink()
            for image in images:
                shutil.copy2(image, BASELINE / image.name)
            print(f"Done: updated {len(images)} visual baselines in {BASELINE.relative_to(ROOT)}")
            return

        if not BASELINE.is_dir():
            raise SystemExit("No visual baselines. Run `make visual-update`, review the result and commit it to Git.")

        args.diff_output.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        compare = image_compare()
        for image in images:
            baseline = BASELINE / image.name
            if not baseline.is_file():
                failures.append(f"missing baseline: {image.name}")
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
        failures.extend(f"stale baseline: {name}" for name in sorted(extra))
        if failures:
            raise SystemExit("Visual changes found:\n- " + "\n- ".join(failures))

    print("Done: no visual changes")


if __name__ == "__main__":
    main()
