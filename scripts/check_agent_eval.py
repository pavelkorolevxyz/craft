#!/usr/bin/env python3
"""Проверяет сохранённые результаты агентов, не доверяя их самоотчётам."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from lib import ROOT

DETAILS = ["Все 12 сценариев входа пройдены", "Повторный запрос создал два платежа",
           "Запуск после обновления индекса", "Изменение имени и фотографии работает"]
NAMES = ["Проверка входа", "Проверка оплаты", "Проверка поиска", "Проверка профиля"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--refresh", action="store_true", help="Повторить браузерный сценарий и снимки")
    parser.add_argument("--strict", action="store_true", help="Код 1, если хотя бы один критерий не выполнен")
    args = parser.parse_args()
    all_passed = True
    for run in args.runs:
        run = run.resolve()
        metadata = json.loads((run / "run.json").read_text())
        assert "returncode" in metadata, f"агент ещё работает: {run.name}"
        review = run / "review"
        review.mkdir(exist_ok=True)
        checks = {"completed": metadata["returncode"] == 0}
        validation = {}
        for surface in ("slides", "interface"):
            result = subprocess.run([sys.executable, str(ROOT / "scripts/check_project.py"), str(run / "output" / surface)],
                                    text=True, capture_output=True, timeout=120)
            (review / f"{surface}-validator.log").write_text(result.stdout + result.stderr)
            validation[surface] = result.returncode
            checks[f"{surface}.validator"] = result.returncode == 0
        if args.refresh or not (review / "browser.json").exists():
            subprocess.run(["node", str(ROOT / "tests/agent/browser.mjs"), str(run)], check=True, timeout=180)
        browser = json.loads((review / "browser.json").read_text())
        slides = browser["slides"]
        groups: dict[str, list[dict]] = {}
        for slide in slides:
            groups.setdefault(slide["source"], []).append(slide)
        criteria = [g for g in groups.values() if all(word in g[-1]["text"].lower() for word in ("скорость", "доступность", "стоимость"))]
        checks["slides.criteria"] = len(criteria) == 1 and [sum(word in s["text"].lower() for word in ("скорость", "доступность", "стоимость")) for s in criteria[0]] == [0, 1, 2, 3]
        flows = [g for g in groups.values() if g[0]["layout"] == "flow"]
        checks["slides.flow"] = len(flows) == 1 and [sum(bool(re.search(rf"\b{word}\b", s["text"], re.I)) for word in ("клиент", "сервер", "журнал")) for s in flows[0]] == [1, 2, 3]
        checks["slides.neutralFlow"] = bool(flows) and all(not re.search(r'class="[^"]*\bflow-node--accent\b', s["html"]) for g in flows for s in g)
        directions = [s for s in slides if "Обучение команды" in s["text"] and "Мониторинг" in s["text"]]
        checks["slides.independent"] = bool(directions) and all(s["layout"] == "list" for s in directions)
        comparisons = [s for s in slides if s["layout"] in ("comparison", "table") and "Ручная" in s["text"]]
        checks["slides.comparison"] = bool(comparisons) and all(not any(part.strip().lower() in {"было", "стало", "до", "после"} for part in s["text"].split("|")) for s in comparisons)
        checks["slides.values"] = any(all(re.search(rf"\b{n}\b", s["text"]) for n in ("40", "8", "12")) for s in comparisons)
        interactions = browser["interactions"]
        search = interactions["search-payment"]["text"]
        checks["interface.search"] = "Проверка оплаты" in search and all(name not in search for name in (NAMES[0], NAMES[2], NAMES[3]))
        empty = interactions["empty-result"]["text"]
        checks["interface.empty"] = browser["filterFound"] and bool(re.search(r"ничего не найдено|совпадений нет|нет результатов", empty, re.I))
        checks["interface.noStaleDetails"] = not any(detail in empty for detail in DETAILS)
        checks["interface.reset"] = browser["resetFound"] and all(name in interactions["reset"]["text"] for name in NAMES)
        checks["interface.keyboard"] = DETAILS[1] in interactions.get("keyboard-payment", {}).get("text", "")
        checks["interface.mouse"] = DETAILS[3] in interactions.get("mouse-profile", {}).get("text", "")
        checks["interface.widths"] = all(state["scrollWidth"] <= state["width"] for state in browser["interface"])
        for suffix, expected in (("filtered", [NAMES[1]]), ("empty", []), ("current", NAMES)):
            text = subprocess.check_output(["pdftotext", str(review / f"interface-{suffix}.pdf"), "-"], text=True)
            (review / f"interface-{suffix}.txt").write_text(text)
            checks[f"interface.print.{suffix}"] = [name for name in NAMES if name in text] == expected
        pdfinfo = subprocess.check_output(["pdfinfo", str(review / "slides.pdf")], text=True)
        pages = int(re.search(r"Pages:\s*(\d+)", pdfinfo)[1])
        checks["slides.printPages"] = pages == len(slides)
        result = {"run": run.name, "agent": metadata["agent"], "model": metadata["model"],
                  "returncode": metadata["returncode"], "seconds": metadata["seconds"], "pages": pages,
                  "validation": validation, "checks": checks,
                  "limitations": "Смысл цвета, читаемость и корректность самого тестового селектора требуют просмотра снимков. Проверки относятся только к tests/agent/task.md."}
        (review / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        failed = [name for name, passed in checks.items() if not passed]
        all_passed &= not failed
        print(f"{run.name}: {sum(checks.values())}/{len(checks)}; не выполнено: {', '.join(failed) or 'нет'}")
    if args.strict and not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
