#!/usr/bin/env python3
"""Запускает полный набор проверок Craft."""

from __future__ import annotations

import sys

from lib import ROOT, run


def main() -> None:
    run(sys.executable, ROOT / "scripts/check.py", capture=False)
    run(sys.executable, ROOT / "scripts/test_scaffold.py", capture=False)
    print("Готово: полная проверка Craft пройдена")


if __name__ == "__main__":
    main()
