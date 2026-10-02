#!/usr/bin/env python3
"""Checks that the deck state pass catches past breakages.

Each fixture reproduces one class of bug from real work on a talk:
clipped text, a jumping reveal, an empty static frame, a hidden clip
that keeps playing, and so on. The good deck must pass. Each broken one
must fail with a clear message.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib import ROOT, node, scaffold

PROBE = ROOT / "scripts/deck_probe.mjs"
CHECK_PROJECT = ROOT / "scripts/check_project.py"
MEDIA = ROOT / "tests/fixtures/media"
QR = subprocess.run(
    [sys.executable, str(ROOT / "scripts/qr.py"), "https://example.com/", "--link"],
    check=True, text=True, capture_output=True,
).stdout if shutil.which("qrencode") else None

LIST = """<section class="slide" data-slide-layout="list" data-key="points">
  <div class="pad"><h2 class="slide-title">Three points</h2>
    <ul class="bullets">
      <li data-n="01"><div><h3>The first point appears with the heading</h3></div></li>
      <li class="frag" data-n="02"><div><h3>Second point</h3></div></li>
      <li class="frag" data-n="03"><div><h3>Third point</h3></div></li>
    </ul>
    <p class="type-note frag" data-frag="with-previous">The caption appears with the third point</p></div>
  <p class="slide-number"></p>
</section>"""

METRIC = """<section class="slide" data-slide-layout="metrics" data-key="numbers">
  <div class="pad"><p class="slide-title">Number</p>
    <div class="scoreboard"><div class="frag"><div><div class="v type-metric" data-count>12,400</div><div class="k">views</div></div></div></div>
  </div>
  <p class="slide-number"></p>
</section>"""

FLOW = """<section class="slide s-flow" data-slide-layout="flow" data-key="path">
  <div class="pad"><p class="slide-title">Request path</p>
    <div class="flow place-fill">
      <div class="flow-node"><strong>Client</strong></div>
      <div class="flow-step frag"><b class="flow-arrow" aria-hidden="true"></b><div class="flow-node"><strong>Server</strong></div></div>
    </div></div>
  <p class="slide-number"></p>
</section>"""

VIDEO = """<section class="slide s-figure" data-slide-layout="figure" data-key="{key}">
  <div class="pad"><p class="slide-title">Recording</p>
    <div class="figure columns content-aside place-fill">
      <div class="frame"><video preload="none" class="media-contain" src="clip.webm" poster="clip-poster.png" {attrs}></video></div>
      <div class="content-block"><p class="frag type-note">Note on the recording</p></div>
    </div>
  </div>
  <p class="slide-number"></p>
</section>"""

END = """<section class="slide s-end" data-slide-layout="end" data-key="end">
  <div class="pad"><h2 class="type-hero">Thank you</h2>
  {qr}
  </div>
  <p class="slide-number"></p>
</section>"""

BENTO = """<section class="slide s-bento" data-slide-layout="bento" data-key="stack">
  <div class="pad"><p class="slide-title">Stack</p>
    <div class="bento">
      <ul class="bento-row"><li class="bento-tile" style="--span:4">Python</li><li class="bento-tile" style="--span:4">SQLite</li><li class="bento-tile" style="--span:4">Electron</li></ul>
      <ul class="bento-row"><li class="bento-tile" style="--span:6">React</li><li class="bento-tile is-accent" style="--span:6">FFmpeg</li></ul>
    </div></div>
  <p class="slide-number"></p>
</section>"""

DEMO = """<section class="slide s-shot" data-slide-layout="screenshot" data-key="demo-full">
  <figure class="shot"><video preload="none" class="media-cover" src="clip.webm" poster="clip-poster.png" aria-label="Recording" loop></video></figure>
  <p class="slide-title" data-exit="intended">Demo</p>
  <p class="slide-number"></p>
</section>"""

GOOD = "\n".join([
    BENTO, DEMO,
    LIST, METRIC, FLOW,
    VIDEO.format(key="demo", attrs='loop data-playback-rate="1.5"'),
    VIDEO.format(key="scene-a", attrs='loop data-media="scene" data-scene="bg"'),
    VIDEO.format(key="scene-b", attrs='loop data-media="scene" data-scene="bg"'),
    END.format(qr=QR or ""),
])

STATEMENT = """<section class="slide s-statement" data-slide-layout="statement" data-key="{key}">
  <div class="pad">{body}</div>
  <p class="slide-number"></p>
</section>"""

# Name, slides, local CSS, local JS, expected message substring.
CASES: list[tuple[str, str, str, str, str | None]] = [
    ("good deck", GOOD, "", "", None),
    ("text clipped by container",
     STATEMENT.format(key="clip", body='<div style="height:4cqh;overflow:hidden"><h2 class="type-hero">A long statement that does not fit the given height</h2></div>'),
     "", "", "text clipped by container"),
    ("reveal shifts shown content", LIST, ".frag:not([data-shown]) { display: none; }", "", "reveal shifts content already shown"),
    ("animation with a final frame reaches the end in static mode",
     STATEMENT.format(key="late", body='<h2 class="type-hero late">Statement</h2>'),
     ".late { opacity: 0; } .late { animation: late-in .3s 1s forwards; } @keyframes late-in { to { opacity: 1; } }",
     "", None),
    ("content appears only with motion",
     STATEMENT.format(key="late", body='<h2 class="type-hero late">Statement</h2>'),
     '.late { opacity: 0; } :root[data-motion-state="on"] .late { animation: late-in .3s forwards; } @keyframes late-in { to { opacity: 1; } }',
     "", "content is invisible in the static frame"),
    ("missing slide key", LIST.replace(' data-key="points"', ""), "", "", "has no data-key"),
    ("layout does not match the template",
     '<section class="slide" data-slide-layout="end" data-key="fake-end"><div class="pad"><h2>Thank you</h2></div><p class="slide-number"></p></section>',
     "", "", "is declared but"),
    ("local composition without a reason",
     '<section class="slide" data-slide-layout="list" data-composition="local" data-key="local"><div class="pad"><p class="slide-title">Custom</p></div><p class="slide-number"></p></section>',
     "", "", "data-local-reason"),
    ("caption before the image",
     '<section class="slide s-figure" data-slide-layout="figure" data-key="cap"><div class="pad"><p class="slide-title">Frame</p><figure class="frame"><figcaption class="frag">Caption</figcaption><img class="frag media-contain" src="clip-poster.png" alt="Frame"></figure></div><p class="slide-number"></p></section>',
     "", "", "caption appears before its content"),
    ("QR as an image without a link",
     END.format(qr='<div class="qr-link"><div class="qr"><img src="clip-poster.png" alt="QR"></div></div>'),
     "", "", "inline svg"),
    ("animation pages the deck",
     STATEMENT.format(key="auto", body='<h2 class="type-hero jump">Statement</h2>') + LIST,
     "[data-reveal] .jump, [data-reveal].slide .jump { animation: nudge .2s; } @keyframes nudge { from { transform: translateY(1cqh); } }",
     "addEventListener('animationend', () => craftDeck.go(craftDeck.current + 1));",
     "animation switched the page"),
    ("content covers the panel",
     STATEMENT.format(key="cover", body='<h2 class="type-hero">Statement</h2><div class="cover-all"></div>'),
     ".slide { isolation: auto !important; } .cover-all { position: fixed; left: 0; right: 0; bottom: 0; height: 40vh; z-index: 50; background: var(--bg); }",
     "", "is covered by"),
    ("hidden clip plays", GOOD,
     "", "setInterval(() => document.querySelectorAll('video').forEach((video) => video.play().catch(() => {})), 100);",
     "video on a hidden page is playing"),
    ("print loses a page", LIST, "@media print { .slide[data-print-page]:nth-child(3) { display: none !important; } }", "", "PDF with all reveals"),
    ("bento reveals in steps", BENTO.replace('<li class="bento-tile" style="--span:6">React</li>', '<li class="bento-tile frag" style="--span:6">React</li>'), "", "", "bento shows as one page"),
    ("bento tiles of different heights", BENTO, ".bento-tile:first-child { align-self: start; }", "", "bento tiles in one row have different heights"),
    ("counter wraps the number",
     METRIC.replace('class="scoreboard"', 'class="scoreboard" style="width:6cqw"').replace("12,400", "11 111"),
     "[data-count] { white-space: normal !important; font-variant-numeric: proportional-nums !important; }", "", "counter number takes"),
]

# Source rules the static check catches without a browser.
STATIC_CASES: list[tuple[str, str, str, str]] = [
    ("manual line break", STATEMENT.format(key="br", body='<h2 class="type-hero">First<br>second</h2>'), "", "manual <br>"),
    ("custom motion policy", LIST, "@media (prefers-reduced-motion: reduce) { .bullets { opacity: 1; } }", "prefers-reduced-motion"),
    ("plain space in counter", METRIC.replace("12,400", "12 400"), "", "plain space"),
    ("counter without group separator", METRIC.replace("12,400", "12400"), "", "no group separator"),
    ("clip loads at once", DEMO.replace('preload="none" ', ""), "", "without preload"),
]


def build(root: Path, name: str, slides: str, css: str = "", js: str = "") -> Path:
    project = root / name.replace(" ", "-")
    scaffold(project, "slides", "deck", "State check")
    for item in MEDIA.iterdir():
        shutil.copy2(item, project / item.name)
    index = project / "index.html"
    document = index.read_text(encoding="utf-8")
    marker = "\n</div>\n</div>\n"
    assert marker in document, "the starter changed the .slides structure"
    document = document.replace(marker, "\n" + slides + marker, 1)
    if css:
        (project / "local.css").write_text(css, encoding="utf-8")
        document = document.replace("</head>", '<link rel="stylesheet" href="local.css">\n</head>', 1)
    if js:
        (project / "local.js").write_text(js, encoding="utf-8")
        document = document.replace("</body>", '<script src="local.js"></script>\n</body>', 1)
    index.write_text(document, encoding="utf-8")
    return index


# Each broken deck runs only the pass that is meant to catch it; the source
# checks run every time. The good deck runs every pass.
CASE_PASSES = {
    "text clipped by container": "frames",
    "reveal shifts shown content": "frames",
    "animation with a final frame reaches the end in static mode": "frames,motion",
    "content appears only with motion": "frames",
    "QR as an image without a link": "frames",
    "animation pages the deck": "motion",
    "content covers the panel": "phone",
    "hidden clip plays": "video",
    "print loses a page": "print",
    "bento tiles of different heights": "frames",
    "counter wraps the number": "motion",
}


def probe(index: Path, passes: str | None = None) -> dict:
    command = [node(), str(PROBE), str(index)]
    if passes is not None:
        command += ["--passes", passes]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=600)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_case(root: Path, case: tuple[str, str, str, str, str | None]) -> str:
    name, slides, css, js, expected = case
    report = probe(build(root, name, slides, css, js), None if expected is None and name == "good deck" else CASE_PASSES.get(name, ""))
    messages = [item["message"] for item in report["errors"]]
    if expected is None:
        assert not messages, f"{name}: the good deck failed:\n" + "\n".join(messages)
        if name == "good deck":
            assert report["pdf"] == {"steps": len(report["pages"]), "final": report["sources"]}, f"{name}: wrong PDF {report['pdf']}"
        videos = [item for item in report["warnings"] if item["kind"] == "video"]
        assert not videos, f"{name}: video warnings: {videos}"
    else:
        assert any(expected in message for message in messages), f"{name}: expected error \"{expected}\", got:\n" + "\n".join(messages or ["no errors"])
    return name


def main() -> None:
    if not QR:
        print("! qrencode not found: checking the good deck without a QR")
    with tempfile.TemporaryDirectory(prefix="craft-probe-") as directory:
        root = Path(directory)
        for name, slides, css, expected in STATIC_CASES:
            index = build(root, name, slides, css)
            result = subprocess.run([sys.executable, str(CHECK_PROJECT), str(index.parent), "--static-only"], cwd=ROOT, text=True, capture_output=True)
            assert result.returncode != 0 and expected in result.stderr, f"{name}: expected error \"{expected}\": {result.stdout}{result.stderr}"
            print(f"✓ {name}")
        for name, value in (("comma in counter", "12,400"), ("no-break space in counter", "12&nbsp;400")):
            index = build(root, name, METRIC.replace("12,400", value))
            result = subprocess.run([sys.executable, str(CHECK_PROJECT), str(index.parent), "--static-only"], cwd=ROOT, text=True, capture_output=True)
            assert result.returncode == 0, f"{name}: separator was rejected: {result.stdout}{result.stderr}"
            print(f"✓ {name}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name in pool.map(lambda case: run_case(root, case), CASES):
                print(f"✓ {name}")
    print("Done: the state check catches past breakages and passes the good deck")


if __name__ == "__main__":
    main()
