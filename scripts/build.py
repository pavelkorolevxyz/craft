#!/usr/bin/env python3
"""Создаёт воспроизводимые релизные архивы Craft без внешних зависимостей."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from lib import MANIFEST, ROOT, sha256

DIST = ROOT / "dist"
FORBIDDEN_RELEASE_PARTS = {"tests", "docs", "examples", "output", "artifacts"}
RUNTIME_SCRIPTS = (
    "scripts/lib.py",
    "scripts/scaffold.py",
    "scripts/compose.py",
    "scripts/check_project.py",
)


def files_under(*roots: str) -> list[Path]:
    files: set[Path] = set()
    for value in roots:
        path = ROOT / value
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(
                item for item in path.rglob("*")
                if item.is_file() and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}
            )
        else:
            raise FileNotFoundError(value)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def validate_release_files(package: str, files: list[Path]) -> None:
    for source in files:
        relative = source.relative_to(ROOT)
        assert not (FORBIDDEN_RELEASE_PARTS & set(relative.parts)), f"{package}: запрещённый путь в релизе: {relative}"
        assert "specimen" not in source.name, f"{package}: тестовый каталог попал в релиз: {relative}"
    assert any("fragments" in source.parts for source in files), f"{package}: в релизе нет универсальных фрагментов"


def write_archive(target: Path, package: str, files: list[Path]) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in files:
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{package}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if source.suffix == ".py" else 0o644) << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DIST)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if args.clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    common = ["assets/shared", "references/identity.md", "references/surfaces.md", "craft.json"]
    packages = {
        "craft-interface": files_under(*common, "assets/interfaces", "references/interfaces", "catalog/interfaces"),
        "craft-slides": files_under(*common, "assets/slides", "references/slides", "catalog/slides"),
        "craft-complete": files_under(
            "SKILL.md",
            "craft.json",
            "assets",
            "catalog",
            "references",
            *RUNTIME_SCRIPTS,
        ),
    }

    release: dict[str, object] = {
        "name": MANIFEST["name"],
        "version": MANIFEST["version"],
        "packages": {},
    }
    package_data: dict[str, object] = release["packages"]  # type: ignore[assignment]
    for name, files in packages.items():
        validate_release_files(name, files)
        if name == "craft-complete":
            packaged_scripts = {path.relative_to(ROOT).as_posix() for path in files if "scripts" in path.parts}
            assert packaged_scripts == set(RUNTIME_SCRIPTS), "craft-complete: неверный набор исполняемых команд"
        archive = output / f"{name}.zip"
        write_archive(archive, name, files)
        package_data[name] = {
            "file": archive.name,
            "bytes": archive.stat().st_size,
            "sha256": sha256(archive),
            "entries": len(files),
        }
        print(f"✓ {archive.name}")

    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums = output / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in sorted(output.glob("*.zip"))),
        encoding="utf-8",
    )
    print(f"Готово: релиз собран в {output}")


if __name__ == "__main__":
    main()
