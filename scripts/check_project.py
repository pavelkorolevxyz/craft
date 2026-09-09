#!/usr/bin/env python3
"""Проверяет автономный интерфейс или слайдовую колоду, созданные с Craft."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from lib import chromium_args, run

PLACEHOLDER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_IMPORT = re.compile(r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s;]+)", re.I)
CSS_URL = re.compile(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", re.I)
VIEWPORTS = ((1440, 900), (390, 844), (320, 720))
WEB_DELIVERY = re.compile(r"<html\b[^>]*\bdata-craft-delivery=\"web\"")
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net", "unpkg.com"}


class ProjectParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []
        self.h1_count = 0
        self.interface = False
        self.slides = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if values.get("data-craft-layout") == "interface":
            self.interface = True
        if tag == "section" and "slide" in (values.get("class") or "").split():
            self.slides = True
        if tag == "link" and values.get("href"):
            self.assets.append(values["href"] or "")
        if tag in {"script", "img", "source", "video", "audio", "track", "iframe", "embed"} and values.get("src"):
            self.assets.append(values["src"] or "")
        if tag == "object" and values.get("data"):
            self.assets.append(values["data"] or "")
        if tag == "video" and values.get("poster"):
            self.assets.append(values["poster"] or "")
        if tag in {"img", "source"} and values.get("srcset"):
            self.assets.extend(
                candidate.strip().split()[0]
                for candidate in (values["srcset"] or "").split(",")
                if candidate.strip()
            )
        if values.get("style"):
            self.assets.extend(css_references(values["style"] or ""))


def project_index(path: Path) -> Path:
    target = path.expanduser().resolve()
    index = target / "index.html" if target.is_dir() else target
    assert index.is_file(), f"не найден index.html: {index}"
    return index


def css_references(text: str) -> list[str]:
    source = CSS_COMMENT.sub("", text)
    return [*CSS_IMPORT.findall(source), *CSS_URL.findall(source)]


def validate_reference(root: Path, base: Path, value: str, origin: Path, web: bool = False) -> None:
    reference = value.strip()
    if not reference or reference.startswith("#"):
        return
    parsed = urlsplit(reference)
    if parsed.scheme in {"data", "blob"}:
        return
    if parsed.scheme or reference.startswith("//"):
        allowed = web and parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
        detail = "внешний ресурс вне белого списка" if web else "внешний ресурс в локальном проекте"
        assert allowed, f"{detail} в {origin.relative_to(root)}: {reference}"
        return
    relative = Path(unquote(parsed.path))
    assert not relative.is_absolute(), f"абсолютный путь к ресурсу в {origin.relative_to(root)}: {reference}"
    target = (base / relative).resolve()
    assert target == root or root in target.parents, f"ресурс выходит за папку проекта в {origin.relative_to(root)}: {reference}"
    assert target.is_file(), f"сломанный локальный ресурс в {origin.relative_to(root)}: {reference}"


def check_staged_reveals(text: str) -> None:
    """У перечисления с раскрытием все пункты появляются после заголовка."""
    sections = re.findall(r'<section\b[^>]*class="[^"]*\bslide\b[^"]*"[^>]*>.*?</section>', text, re.DOTALL)
    for section in sections:
        layout_match = re.search(r'data-slide-layout="([a-z-]+)"', section)
        if not layout_match:
            continue
        layout = layout_match.group(1)
        if layout == "list":
            item_attrs = re.findall(r'<li\b([^>]*)>', section)
        elif layout == "steps":
            item_attrs = re.findall(r'<div\b([^>]*)>\s*<div class="n">', section)
        elif layout == "timeline":
            item_attrs = re.findall(r'<li\b([^>]*)>', section)
        elif layout == "metrics":
            item_attrs = re.findall(r'<div(?:\s+[^>]*)?>\s*<div\b([^>]*)>\s*<div class="v\b', section)
        else:
            continue
        staged = [bool(re.search(r'class="[^"]*\bfrag\b', attrs)) for attrs in item_attrs]
        if any(staged):
            assert all(staged), f"{layout}: при пошаговом раскрытии каждый пункт, включая первый, должен иметь class=\"frag\""


def check_static(index: Path, resource_root: Path | None = None) -> str:
    root = index.parent
    resources = resource_root.expanduser().resolve() if resource_root else root
    assert resources == root or resources in root.parents, "папка ресурсов должна содержать проверяемый проект"
    project_files = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".html", ".css", ".js"}]
    web = bool(WEB_DELIVERY.search(index.read_text(encoding="utf-8")))
    html_parsers: dict[Path, ProjectParser] = {}
    for path in project_files:
        text = path.read_text(encoding="utf-8")
        match = PLACEHOLDER.search(text)
        assert not match, f"необработанная подстановка {match.group(0)} в {path.relative_to(root)}"
        if path.suffix == ".html":
            parser = ProjectParser()
            parser.feed(text)
            html_parsers[path] = parser
            for value in parser.assets:
                validate_reference(resources, path.parent, value, path, web)
        elif path.suffix == ".css":
            for value in css_references(text):
                validate_reference(resources, path.parent, value, path, web)

    parser = html_parsers[index]
    assert parser.h1_count == 1, f"ожидался один h1, найдено: {parser.h1_count}"
    assert parser.interface != parser.slides, "не удалось однозначно определить поверхность Craft"
    if parser.slides:
        check_staged_reveals(index.read_text(encoding="utf-8"))
    return "interface" if parser.interface else "slides"


def browser_probe_script(surface: str) -> str:
    action = (
        "const toggle=document.querySelector('[data-theme-toggle]');"
        "const before=document.documentElement.dataset.theme;toggle?.click();const changed=before!==document.documentElement.dataset.theme;"
        if surface == "interface"
        else "const before=document.documentElement.dataset.theme;document.dispatchEvent(new KeyboardEvent('keydown',{key:'T'}));const changed=before!==document.documentElement.dataset.theme;"
    )
    return (
        action
        + "const controls=[...document.querySelectorAll('button,input,select,textarea,a[href]')];"
        + "const unnamed=controls.filter(el=>{const id=el.id;const label=el.closest('label')||(id&&document.querySelector(`label[for=\"${CSS.escape(id)}\"]`));return !(el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent.trim()||label)}).length;"
        + "const ranks=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(el=>Number(el.tagName[1]));const jumps=ranks.slice(1).filter((rank,i)=>rank>ranks[i]+1).length;"
        + "const slides=[...document.querySelectorAll('.slide')];const undeclared=slides.filter(el=>!el.dataset.slideLayout).length;const active=document.querySelectorAll('.slide[data-active]').length;"
        + "return `${document.documentElement.scrollWidth}:${innerWidth}:${unnamed}:${jumps}:${changed?1:0}:${slides.length}:${undeclared}:${active}`;"
    )


def probe_all(index: Path, surface: str) -> list[tuple[int, ...]]:
    """Проверяет все контрольные размеры за один запуск Chromium."""
    probe_path = index.with_name("__craft_check__.html")
    inspect = browser_probe_script(surface)
    initialized = (
        "const toggle=document.querySelector('[data-theme-toggle]');return !toggle||Boolean(toggle.getAttribute('aria-label'));"
        if surface == "interface"
        else "return document.querySelectorAll('.slide[data-active]').length===1;"
    )
    harness = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>craft-check:pending</title>
<style>iframe {{ position: absolute; inset: 0 auto auto 0; border: 0; }}</style></head>
<body><script>
const frames = {json.dumps(VIEWPORTS)}.map(([width, height]) => {{
  const frame = document.createElement('iframe');
  frame.width = width;
  frame.height = height;
  frame.src = {json.dumps(quote(index.name))};
  document.body.append(frame);
  return frame;
}});
const inspectWhenReady = () => {{
  const loaded = frames.every(frame => {{
    const document = frame.contentDocument;
    if (frame.contentWindow.location.href === 'about:blank' || document.readyState === 'loading') return false;
    {initialized}
  }});
  if (!loaded) {{ setTimeout(inspectWhenReady, 10); return; }}
  const results = frames.map(frame => {{
    const document = frame.contentDocument;
    const innerWidth = frame.contentWindow.innerWidth;
    {inspect}
  }});
  document.title = `craft-check:${{results.join('|')}}`;
}};
inspectWhenReady();
</script></body></html>"""
    probe_path.write_text(harness, encoding="utf-8")
    try:
        dumped = run(*chromium_args(1500, 1000), "--allow-file-access-from-files", "--dump-dom", probe_path.as_uri()).stdout
        match = re.search(r"<title>craft-check:([^<]+)</title>", dumped)
        assert match and match.group(1) != "pending", "браузерная проверка не выполнилась"
        results = [tuple(map(int, result.split(":"))) for result in match.group(1).split("|")]
        assert len(results) == len(VIEWPORTS) and all(len(result) == 8 for result in results), "Chromium вернул неполный результат проверки"
        return results
    finally:
        probe_path.unlink(missing_ok=True)


def check_browser(index: Path, surface: str) -> None:
    for (width, _), result in zip(VIEWPORTS, probe_all(index, surface)):
        scroll, viewport, unnamed, jumps, theme_changed, slides, undeclared, active = result
        assert viewport == width, f"Chromium открыл контрольный экран {width}px с шириной {viewport}px"
        assert scroll <= viewport, f"горизонтальное переполнение при ширине {width}px: {scroll}px > {viewport}px"
        assert unnamed == 0, f"элементы управления без доступного имени: {unnamed}"
        assert jumps == 0, f"найдены пропуски уровней заголовков: {jumps}"
        assert theme_changed == 1, "переключение темы не работает"
        if surface == "slides":
            assert slides > 0 and undeclared == 0 and active == 1, "нарушен контракт слайдовой колоды"

    with tempfile.TemporaryDirectory(prefix="craft-project-pdf-") as directory:
        pdf = Path(directory) / "project.pdf"
        run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", index.as_uri())
        assert pdf.is_file() and pdf.stat().st_size > 5_000, "печать PDF не выполнена"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Папка проекта или путь к index.html")
    parser.add_argument("--static-only", action="store_true", help="Не запускать Chromium и печать PDF")
    parser.add_argument("--resource-root", type=Path, help="Корень автономного пакета, если каталог вложен глубже ресурсов")
    args = parser.parse_args()

    index = project_index(args.project)
    surface = check_static(index, args.resource_root)
    print(f"✓ статические контракты: {surface}")
    if args.static_only:
        print(f"Готово: статическая проверка завершена, Chromium и PDF не запускались — {index}")
    else:
        check_browser(index, surface)
        print("✓ Chromium: 1440, 390 и 320 px, тема, доступность и PDF")
        print(f"Готово: проект Craft корректен — {index}")


if __name__ == "__main__":
    main()
