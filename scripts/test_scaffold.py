#!/usr/bin/env python3
"""Создаёт все шаблоны Craft и проверяет их в Chromium."""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from lib import MANIFEST, ROOT, chromium_args, run, scaffold_matrix


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            self.paths.append(values["href"] or "")
        if tag in {"script", "img", "source", "video"} and values.get("src"):
            self.paths.append(values["src"] or "")


def validate_output(key: str, output: Path) -> None:
    index = output / "index.html"
    assert index.is_file(), f"{key}: отсутствует index.html"
    assert (output / "tokens.css").is_file(), f"{key}: отсутствует tokens.css"
    expected_fonts = MANIFEST["requirements"]["fontFiles"]
    assert len(list((output / "fonts").glob("*.woff2"))) == expected_fonts

    html = index.read_text(encoding="utf-8")
    assert not re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", html), f"{key}: необработанная подстановка"
    parser = LocalAssetParser()
    parser.feed(html)
    for value in parser.paths:
        assert not value.startswith(("http://", "https://", "//")), f"{key}: внешний ресурс {value}"
        target = output / value.split("?", 1)[0].split("#", 1)[0]
        assert target.is_file(), f"{key}: сломанный ресурс {value}"


def dump_probe(output: Path, script: str, width: int, height: int) -> str:
    source = output / "index.html"
    probe = output / "__probe.html"
    html = source.read_text(encoding="utf-8")
    probe.write_text(html.replace("</body>", f"<script>{script}</script></body>"), encoding="utf-8")
    return run(
        *chromium_args(width, height),
        "--dump-dom",
        probe.as_uri(),
    ).stdout


def test_interfaces(key: str, output: Path) -> None:
    for width, height in ((1440, 900), (500, 844)):
        dumped = dump_probe(
            output,
            "document.title=`probe:${document.documentElement.scrollWidth}:${innerWidth}:${document.querySelectorAll('main').length}`",
            width,
            height,
        )
        match = re.search(r"<title>probe:(\d+):(\d+):(\d+)</title>", dumped)
        assert match, f"{key}: браузерная проверка не выполнена"
        scroll_width, viewport, mains = map(int, match.groups())
        assert scroll_width <= viewport, f"{key}: горизонтальное переполнение при {width}px ({scroll_width}>{viewport})"
        assert mains == 1, f"{key}: ожидалась одна основная область main"


def test_observability() -> None:
    example = ROOT / "examples/observability"
    try:
        dumped = dump_probe(
            example,
            "const bars=[...document.querySelectorAll('.cell-bar__fill')];"
            "const visibleBars=bars.filter((bar)=>bar.getBoundingClientRect().width>0).length;"
            "const errors=[...document.querySelectorAll('.log-list li[data-level=error]')];"
            "const tinted=errors.filter((row)=>!['transparent','rgba(0, 0, 0, 0)'].includes(getComputedStyle(row).backgroundColor));"
            "const snapshot=(element)=>{const rect=element.getBoundingClientRect();return [rect.left,rect.top,rect.width,rect.height].map(Math.round).join(',')};"
            "const pause=document.querySelector('#pause');const live=document.querySelector('#live');"
            "const before=snapshot(pause)+';'+snapshot(live);pause.click();"
            "const stable=before===snapshot(pause)+';'+snapshot(live)&&live.dataset.state==='paused'&&pause.getAttribute('aria-label')==='Продолжить обновление';"
            "const theme=document.querySelector('#theme');const themeBefore=snapshot(theme);const strokeBefore=document.querySelector('#chart-rps .series-line').getAttribute('stroke');"
            "theme.click();const themeStable=themeBefore===snapshot(theme)&&document.documentElement.dataset.theme==='light';"
            "const themeRepaint=strokeBefore!==document.querySelector('#chart-rps .series-line').getAttribute('stroke');theme.click();"
            "const table=document.querySelector('#endpoints');const panel=table.closest('.panel');"
            "const seam=Math.abs(table.getBoundingClientRect().bottom-panel.getBoundingClientRect().bottom)<=1;"
            "const terminal=[...table.querySelectorAll('tbody tr:last-child td')].every((cell)=>getComputedStyle(cell).borderBottomWidth==='0px');"
            "const chart=document.querySelector('#chart-rps');chart.focus();chart.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true}));"
            "const chartKeyboard=document.querySelector('#chart-readout').textContent.includes(':');"
            "const metricBefore=document.querySelector('#stat-rps .metric__value').textContent;const chartRect=chart.getBoundingClientRect();"
            "chart.dispatchEvent(new PointerEvent('pointerdown',{clientX:chartRect.left+180,clientY:chartRect.top+80,button:0,pointerId:1,bubbles:true}));"
            "chart.dispatchEvent(new PointerEvent('pointerup',{clientX:chartRect.left+360,clientY:chartRect.top+80,button:0,pointerId:1,bubbles:true}));"
            "const zoomSemantics=document.querySelector('#zoom-chip').dataset.active==='true'&&document.querySelector('#stat-rps .metric__value').textContent===metricBefore&&document.querySelector('#desc-rps').textContent.startsWith('В конце интервала');"
            "document.querySelector('#zoom-reset').click();"
            "const heat=document.querySelector('#chart-heat');heat.focus();heat.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true}));"
            "const heatKeyboard=document.querySelector('#chart-readout').textContent.includes('p99:');"
            "const legend=document.querySelector('#legend-rps button');legend.click();const legendToggle=legend.getAttribute('aria-pressed')==='false';legend.click();"
            "document.querySelector('#endpoints th[data-key=rps] button').click();const sorting=document.querySelector('#endpoints th[data-key=rps]').getAttribute('aria-sort')==='ascending';"
            "const range=document.querySelector('#range');range.value='900000';range.dispatchEvent(new Event('change',{bubbles:true}));"
            "const eventEmpty=document.querySelector('#event-summary').dataset.empty==='true'&&document.querySelector('#events').textContent.includes('событий не было');"
            "const originalLogs=Telemetry.logs;Telemetry.logs=()=>[];"
            "const errorFilter=document.querySelector('#log-level input[value=error]');errorFilter.checked=true;errorFilter.dispatchEvent(new Event('change',{bubbles:true}));"
            "const logEmpty=Boolean(document.querySelector('#log .log-empty'));Telemetry.logs=originalLogs;"
            "const logStyle=getComputedStyle(document.querySelector('#log'));const pageScroll=logStyle.overflowY==='visible'&&logStyle.maxHeight==='none';"
            "document.title=`probe:${bars.length}:${visibleBars}:${errors.length}:${tinted.length}:${stable}:${themeStable}:${themeRepaint}:${seam}:${terminal}:${chartKeyboard}:${zoomSemantics}:${heatKeyboard}:${legendToggle}:${sorting}:${eventEmpty}:${logEmpty}:${pageScroll}`",
            1440,
            1000,
        )
    finally:
        example.joinpath("__probe.html").unlink(missing_ok=True)
    match = re.search(r"<title>probe:(\d+):(\d+):(\d+):(\d+):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false):(true|false)</title>", dumped)
    assert match, "observability: браузерная проверка данных не выполнена"
    total, visible, errors, tinted = map(int, match.groups()[:4])
    stable, theme_stable, theme_repaint, seam, terminal, chart_keyboard, zoom_semantics, heat_keyboard, legend_toggle, sorting, event_empty, log_empty, page_scroll = (value == "true" for value in match.groups()[4:])
    assert total > 0 and visible == total, f"observability: видимых полос {visible} из {total}"
    assert errors > 0 and tinted == errors, f"observability: фоном выделены ошибки {tinted} из {errors}"
    assert stable, "observability: пауза сдвигает кнопку или статус обновления"
    assert theme_stable and theme_repaint, "observability: смена темы сдвигает управление или не перерисовывает графики"
    assert seam, "observability: таблица не доходит до разделителя строки панелей"
    assert terminal, "observability: конечная рамка таблицы дублирует разделитель сетки"
    assert chart_keyboard and heat_keyboard, "observability: клавиатурный курсор графика не озвучивает значения"
    assert zoom_semantics, "observability: зум подменяет текущее состояние историческим срезом"
    assert legend_toggle, "observability: легенда не сообщает состояние скрытого ряда"
    assert sorting, "observability: сортировка таблицы не обновляет aria-sort"
    assert event_empty and log_empty, "observability: пустые состояния событий или журнала не объясняют результат фильтра"
    assert page_scroll, "observability: журнал создаёт вложенную вертикальную прокрутку"

    with tempfile.TemporaryDirectory(prefix="craft-observability-print-") as directory:
        pdf = Path(directory) / "observability.pdf"
        run(
            *chromium_args(1440, 1000),
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf}",
            example.joinpath("index.html").as_uri(),
        )
        assert pdf.is_file() and pdf.stat().st_size > 100_000, "observability: экспорт PDF не выполнен"
        pdfinfo = shutil.which("pdfinfo")
        if pdfinfo:
            info = run(pdfinfo, pdf).stdout
            pages = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
            assert pages and int(pages.group(1)) <= 6, "observability: печатная версия раздулась больше шести страниц"


def test_merge_reviews() -> None:
    example = ROOT / "examples/merge-reviews"
    try:
        dumped = dump_probe(
            example,
            "const transparent=(value)=>['transparent','rgba(0, 0, 0, 0)'].includes(value);"
            "const snapshot=(element)=>{const rect=element.getBoundingClientRect();return [rect.left,rect.top,rect.width,rect.height].map(Math.round).join(',')};"
            "const rows=[...document.querySelectorAll('.mr-row')];const first=rows[0];"
            "const plain=transparent(getComputedStyle(first).backgroundColor)&&transparent(getComputedStyle(rows[1]).backgroundColor);"
            "const rail=getComputedStyle(first.closest('.mr-entry').querySelector('.selection-rail')).backgroundColor;"
            "const railed=!transparent(rail)&&transparent(getComputedStyle(rows[1].closest('.mr-entry').querySelector('.selection-rail')).backgroundColor);"
            "const titled=getComputedStyle(first.querySelector('.mr-row__title')).color!==getComputedStyle(rows[1].querySelector('.mr-row__title')).color;"
            "const next=document.querySelector('#next-mr');const before=snapshot(next);const focusBefore=document.activeElement;"
            "document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyJ',bubbles:true}));"
            "const moved=document.querySelector('.mr-row[aria-selected=true]')!==first;"
            "const focusKept=document.activeElement===focusBefore;"
            "next.click();const buttonStable=before===snapshot(next);"
            "const dots=[...document.querySelectorAll('.state-dot')].map((dot)=>getComputedStyle(dot,'::before').width);"
            "const oneDotSize=dots.length>0&&new Set(dots).size===1;"
            "const tails=[...document.querySelectorAll('.check-list,.reviewers,.threads')].map((list)=>list.lastElementChild);"
            "const closed=tails.every((row)=>getComputedStyle(row).borderBottomWidth==='0px');"
            "const nested=[...document.querySelectorAll('.queue,.queue-list,.review-detail')].every((area)=>getComputedStyle(area).overflowY==='visible');"
            "const theme=document.querySelector('#theme');const themeBefore=snapshot(theme);theme.click();"
            "const themeStable=themeBefore===snapshot(theme)&&document.documentElement.dataset.theme==='light';theme.click();"
            "document.title=`probe:${plain}:${railed}:${titled}:${moved}:${focusKept}:${buttonStable}:${oneDotSize}:${closed}:${nested}:${themeStable}`",
            1440,
            1000,
        )
    finally:
        example.joinpath("__probe.html").unlink(missing_ok=True)
    match = re.search(r"<title>probe:" + ":".join([r"(true|false)"] * 10) + r"</title>", dumped)
    assert match, "merge-reviews: браузерная проверка не выполнена"
    plain, railed, titled, moved, focus_kept, button_stable, one_dot_size, closed, nested, theme_stable = (
        value == "true" for value in match.groups()
    )
    assert plain, "merge-reviews: выбранная строка залита плоскостью и не отличается от наведения"
    assert railed and titled, "merge-reviews: выбор не показан маркером и акцентным заголовком"
    assert moved, "merge-reviews: клавиша J не переводит выбор"
    assert focus_kept, "merge-reviews: смена выбора переносит фокус и добавляет второй уровень выделения"
    assert button_stable, "merge-reviews: переход к следующей строке сдвигает кнопку из-под курсора"
    assert one_dot_size, "merge-reviews: точки состояний разного размера"
    assert closed, "merge-reviews: последняя строка списка дублирует границу секции"
    assert nested, "merge-reviews: рабочая область создаёт вложенную вертикальную прокрутку"
    assert theme_stable, "merge-reviews: смена темы сдвигает управление"

    try:
        test_interfaces("merge-reviews", example)
    finally:
        example.joinpath("__probe.html").unlink(missing_ok=True)


def test_slides(key: str, output: Path, work: Path) -> None:
    dumped = dump_probe(
        output,
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));"
        "const afterArrow=document.querySelector('.slide[data-active]')?.dataset.index;"
        "const pageInput=document.querySelector('.help-page-input');"
        "pageInput.value='0';"
        "pageInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));"
        "const afterClamp=document.querySelector('.slide[data-active]')?.dataset.index;"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:String(document.querySelectorAll('.slide').length),bubbles:true}));"
        "pageInput.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));"
        "const deck=document.querySelector('.deck');"
        "const centerError=()=>{const a=document.querySelector('.slide[data-active]').getBoundingClientRect();const d=deck.getBoundingClientRect();return Math.round(Math.max(Math.abs(a.left+a.width/2-(d.left+deck.clientWidth/2)),Math.abs(a.top+a.height/2-(d.top+deck.clientHeight/2))))};"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const stripVerticalError=centerError();"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const stripHorizontalError=centerError();"
        "document.dispatchEvent(new KeyboardEvent('keydown',{key:'L'}));"
        "const stripReturnError=centerError();"
        "document.title=`probe:${document.querySelectorAll('.slide').length}:${document.querySelectorAll('.slide[data-active]').length}:${afterArrow}:${afterClamp}:`+"
        "`${document.querySelector('.slide[data-active]')?.dataset.index}:${document.querySelector('.help-panel').hidden}:${stripVerticalError}:${stripHorizontalError}:${stripReturnError}:${deck.dataset.stripDirection}`",
        1280,
        720,
    )
    match = re.search(r"<title>probe:(\d+):(\d+):(\d+):(\d+):(\d+):(true|false):(\d+):(\d+):(\d+):(\w+)</title>", dumped)
    assert match, f"{key}: проверка механики колоды не выполнена"
    pages, active, after_arrow, after_clamp, current = map(int, match.groups()[:5])
    panel_hidden = match.group(6) == "true"
    strip_vertical_error, strip_horizontal_error, strip_return_error = map(int, match.groups()[6:9])
    strip_direction = match.group(10)
    assert pages >= 6 and active == 1 and after_arrow == 2 and after_clamp == 1 and current == pages and panel_hidden, f"{key}: недопустимое состояние колоды {match.groups()}"
    assert strip_direction == "vertical" and max(strip_vertical_error, strip_horizontal_error, strip_return_error) <= 1, f"{key}: активный слайд ленты не по центру {match.groups()}"

    pdf = work / f"{key}.pdf"
    run(*chromium_args(1280, 720), f"--print-to-pdf={pdf}", output.joinpath("index.html").as_uri())
    assert pdf.is_file() and pdf.stat().st_size > 30_000, f"{key}: экспорт PDF не выполнен"
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        info = run(pdfinfo, pdf).stdout
        count = re.search(r"^Pages:\s+(\d+)", info, re.M)
        assert count and int(count.group(1)) == pages, f"{key}: количество страниц PDF отличается от механики колоды"

    for view in ("grid", "strip"):
        overview_pdf = work / f"{key}-{view}.pdf"
        source = output.joinpath("index.html").as_uri() + f"?view={view}"
        run(*chromium_args(1280, 720), f"--print-to-pdf={overview_pdf}", source)
        assert overview_pdf.is_file() and overview_pdf.stat().st_size > 30_000, f"{key}: печать из режима {view} не выполнена"
        if pdfinfo:
            info = run(pdfinfo, overview_pdf).stdout
            count = re.search(r"^Pages:\s+(\d+)", info, re.M)
            assert count and int(count.group(1)) == pages, f"{key}: режим {view} изменил количество страниц PDF"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=Path, help="Сохранить созданные проекты в этой папке")
    args = parser.parse_args()

    context = None if args.keep else tempfile.TemporaryDirectory(prefix="craft-test-")
    root = args.keep.resolve() if args.keep else Path(context.name)
    root.mkdir(parents=True, exist_ok=True)
    try:
        outputs = scaffold_matrix(root / "projects")
        for key, output in outputs.items():
            validate_output(key, output)
            if key.startswith("interface-"):
                test_interfaces(key, output)
            else:
                test_slides(key, output, root)
            print(f"✓ {key}")
        test_observability()
        print("✓ observability")
        test_merge_reviews()
        print("✓ merge-reviews")
        print("Готово: создание проектов, поведение браузера, переполнение и экспорт PDF проверены")
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    main()
