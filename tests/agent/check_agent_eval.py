#!/usr/bin/env python3
"""Check saved agent results without trusting the agents' own reports."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from lib import ROOT

DETAILS = ["All 12 login scenarios passed", "A retried request created two payments",
           "Runs after the index update", "Changing the name and photo works"]
NAMES = ["Login check", "Payment check", "Search check", "Profile check"]
CRITERIA = ("speed", "availability", "cost")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--refresh", action="store_true", help="Rerun the browser script and screenshots")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if any criterion fails")
    args = parser.parse_args()
    all_passed = True
    for run in args.runs:
        run = run.resolve()
        metadata = json.loads((run / "run.json").read_text())
        assert "returncode" in metadata, f"the agent is still running: {run.name}"
        review = run / "review"
        review.mkdir(exist_ok=True)
        checks = {"completed": metadata["returncode"] == 0}
        validation = {}
        for surface in ("slides", "interface"):
            result = subprocess.run([sys.executable, str(ROOT / "scripts/check_project.py"), str(run / "output" / surface), "--full"],
                                    text=True, capture_output=True, timeout=900)
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
        criteria = [g for g in groups.values() if all(word in g[-1]["text"].lower() for word in CRITERIA)]
        checks["slides.criteria"] = len(criteria) == 1 and [sum(word in s["text"].lower() for word in CRITERIA) for s in criteria[0]] == [0, 1, 2, 3]
        flows = [g for g in groups.values() if g[0]["layout"] == "flow"]
        checks["slides.flow"] = len(flows) == 1 and [sum(bool(re.search(rf"\b{word}s?\b", s["text"], re.I)) for word in ("client", "server", "log")) for s in flows[0]] == [1, 2, 3]
        checks["slides.neutralFlow"] = bool(flows) and all(not re.search(r'class="[^"]*\bflow-node--accent\b', s["html"]) for g in flows for s in g)
        directions = [s for s in slides if "team training" in s["text"].lower() and "monitoring" in s["text"].lower()]
        checks["slides.independent"] = bool(directions) and all(s["layout"] == "list" for s in directions)
        comparisons = [s for s in slides if s["layout"] in ("comparison", "table") and "manual" in s["text"].lower()]
        checks["slides.comparison"] = bool(comparisons) and all(not any(part.strip().lower() in {"before", "after"} for part in s["text"].split("|")) for s in comparisons)
        checks["slides.values"] = any(all(re.search(rf"\b{n}\b", s["text"]) for n in ("40", "8", "12")) for s in comparisons)
        interactions = browser["interactions"]
        search = interactions["search-payment"]["text"]
        checks["interface.search"] = NAMES[1] in search and all(name not in search for name in (NAMES[0], NAMES[2], NAMES[3]))
        empty = interactions["empty-result"]["text"]
        checks["interface.empty"] = browser["filterFound"] and bool(re.search(r"nothing found|no matches|no results", empty, re.I))
        checks["interface.noStaleDetails"] = not any(detail in empty for detail in DETAILS)
        checks["interface.reset"] = browser["resetFound"] and all(name in interactions["reset"]["text"] for name in NAMES)
        checks["interface.keyboard"] = DETAILS[1] in interactions.get("keyboard-payment", {}).get("text", "")
        checks["interface.mouse"] = DETAILS[3] in interactions.get("mouse-profile", {}).get("text", "")
        checks["interface.widths"] = all(state["scrollWidth"] <= state["width"] for state in browser["interface"])
        for suffix, expected in (("filtered", [NAMES[1]]), ("empty", []), ("current", NAMES)):
            text = subprocess.check_output(["pdftotext", str(review / f"interface-{suffix}.pdf"), "-"], text=True)
            (review / f"interface-{suffix}.txt").write_text(text)
            checks[f"interface.print.{suffix}"] = [name for name in NAMES if name in text] == expected
        # Stable keys, explained local compositions and the release archive.
        checks["slides.keys"] = all(re.search(r'data-key="[a-z0-9-]+"', s["html"]) and "data-key-generated" not in s["html"] for s in slides)
        locals_ = [s for s in slides if 'data-composition="local"' in s["html"]]
        checks["slides.localReason"] = all(re.search(r'data-local-reason="[^"]+"', s["html"]) for s in locals_)
        archives = sorted((run / "output/release").glob("*.zip")) if (run / "output/release").is_dir() else []
        packed: list[str] = []
        if archives:
            with zipfile.ZipFile(archives[0]) as bundle:
                packed = bundle.namelist()
        checks["slides.release"] = (
            len(archives) == 1 and archives[0].stat().st_size <= 10 * 1024 * 1024
            and any(name.endswith("/manifest.json") for name in packed)
            and any(name.endswith("/README.txt") for name in packed)
            and not any(name.endswith((".md", ".pdf.tmp")) for name in packed)
        )
        pdfinfo = subprocess.check_output(["pdfinfo", str(review / "slides.pdf")], text=True)
        pages = int(re.search(r"Pages:\s*(\d+)", pdfinfo)[1])
        checks["slides.printPages"] = pages == len(slides)
        result = {"run": run.name, "agent": metadata["agent"], "model": metadata["model"],
                  "returncode": metadata["returncode"], "seconds": metadata["seconds"], "pages": pages,
                  "validation": validation, "checks": checks,
                  "limitations": "Color meaning, readability and the correctness of the test selector itself need a look at the screenshots. The checks apply only to tests/agent/task.md."}
        (review / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        failed = [name for name, passed in checks.items() if not passed]
        all_passed &= not failed
        print(f"{run.name}: {sum(checks.values())}/{len(checks)}; failed: {', '.join(failed) or 'none'}")
    if args.strict and not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
