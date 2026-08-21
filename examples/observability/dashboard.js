/* Дашборд наблюдаемости: отрисовка графиков, синхронный курсор,
   выделение интервала, живое обновление и панели данных. */
(() => {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const MIN = 60000;
  const HOUR = 60 * MIN;
  const DAY = 24 * HOUR;

  const css = getComputedStyle(document.documentElement);
  const tone = (name) => css.getPropertyValue(name).trim();
  const TONES = {
    primary: tone("--series-1"),
    neutral: tone("--series-2"),
    cool: tone("--series-3"),
    warm: tone("--series-4"),
    good: tone("--series-5"),
  };

  function refreshTones() {
    TONES.primary = tone("--series-1");
    TONES.neutral = tone("--series-2");
    TONES.cool = tone("--series-3");
    TONES.warm = tone("--series-4");
    TONES.good = tone("--series-5");
  }

  const state = {
    range: 6 * HOUR,
    refresh: 5000,
    paused: false,
    zoom: null,
    frozenNow: null,
    cursor: null,
    logLevel: "all",
    sort: { key: "rps", dir: -1 },
  };

  const numbers = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
  const decimals = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const short = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

  function formatValue(value, unit) {
    if (unit === "%") return decimals.format(value) + " %";
    if (unit === "мс") return numbers.format(value) + " мс";
    if (value >= 1000) return numbers.format(value);
    return short.format(value);
  }

  function axisValue(value, unit) {
    if (unit === "%") return short.format(value) + " %";
    if (unit === "мс") return numbers.format(value) + " мс";
    return numbers.format(value);
  }

  function clockFormat(span) {
    if (span > 2 * DAY) return { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
    if (span > 12 * HOUR) return { hour: "2-digit", minute: "2-digit" };
    if (span > 30 * MIN) return { hour: "2-digit", minute: "2-digit" };
    return { hour: "2-digit", minute: "2-digit", second: "2-digit" };
  }

  function formatTime(t, span) {
    return new Intl.DateTimeFormat("ru-RU", clockFormat(span)).format(new Date(t));
  }

  function now() {
    return state.paused && state.frozenNow !== null ? state.frozenNow : Date.now();
  }

  function windowRange() {
    if (state.zoom) return { from: state.zoom.from, to: state.zoom.to };
    const to = now();
    return { from: to - state.range, to };
  }

  function niceTicks(max, count) {
    if (max <= 0) return [0, 1];
    const raw = max / count;
    const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) || 10 * magnitude;
    const steps = Math.max(1, Math.ceil(max / step - 0.001));
    const ticks = [];
    for (let i = 0; i <= steps; i += 1) ticks.push(i * step);
    return ticks;
  }

  const TIME_STEPS = [MIN, 2 * MIN, 5 * MIN, 15 * MIN, 30 * MIN, HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 2 * DAY];

  function timeTicks(from, to, count) {
    const span = to - from;
    const step = TIME_STEPS.find((s) => span / s <= count) || DAY * 7;
    const offset = new Date(from).getTimezoneOffset() * MIN;
    const ticks = [];
    let t = Math.ceil((from - offset) / step) * step + offset;
    for (; t <= to; t += step) ticks.push(t);
    return ticks;
  }

  function node(name, attrs, text) {
    const element = document.createElementNS(SVG_NS, name);
    for (const key in attrs) element.setAttribute(key, attrs[key]);
    if (text !== undefined) element.textContent = text;
    return element;
  }

  /* Общий график по оси времени: линии, накопительные области, порог,
     аннотации, синхронный курсор и выделение интервала. */
  class TimeChart {
    constructor(svg, options) {
      this.svg = svg;
      this.options = options;
      this.height = options.height || 196;
      this.margin = { left: 54, right: 14, top: 12, bottom: 24 };
      this.hidden = new Set();
      this.frame = null;
      this.drag = null;
      this.svg.style.height = this.height + "px";
      this.bindEvents();
      if (options.legend) this.buildLegend(document.getElementById(options.legend));
    }

    refreshLegend() {
      if (!this.legendHost) return;
      const buttons = this.legendHost.querySelectorAll("button");
      this.options.series.forEach((series, index) => {
        if (buttons[index]) buttons[index].style.setProperty("--swatch", TONES[series.tone]);
      });
    }

    buildLegend(host) {
      this.legendHost = host;
      host.replaceChildren();
      this.options.series.forEach((series) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "series-key";
        button.setAttribute("aria-pressed", "true");
        button.style.setProperty("--swatch", TONES[series.tone]);
        button.textContent = series.label;
        button.addEventListener("click", () => {
          if (this.hidden.has(series.key)) this.hidden.delete(series.key);
          else if (this.hidden.size < this.options.series.length - 1) this.hidden.add(series.key);
          button.setAttribute("aria-pressed", String(!this.hidden.has(series.key)));
          this.render();
        });
        host.append(button);
      });
    }

    bindEvents() {
      this.svg.addEventListener("pointermove", (event) => this.onPointerMove(event));
      this.svg.addEventListener("pointerleave", () => setCursor(null));
      this.svg.addEventListener("pointerdown", (event) => this.onPointerDown(event));
      this.svg.addEventListener("keydown", (event) => this.onKeyDown(event));
      this.svg.addEventListener("blur", () => setCursor(null));
    }

    plot() {
      const width = this.svg.clientWidth || this.svg.parentNode.clientWidth;
      return {
        width,
        left: this.margin.left,
        right: width - this.margin.right,
        top: this.margin.top,
        bottom: this.height - this.margin.bottom,
      };
    }

    timeAt(clientX) {
      const rect = this.svg.getBoundingClientRect();
      const p = this.plot();
      const ratio = (clientX - rect.left - p.left) / Math.max(1, p.right - p.left);
      const win = this.last ? this.last : windowRange();
      return win.from + Math.min(1, Math.max(0, ratio)) * (win.to - win.from);
    }

    onPointerMove(event) {
      if (this.drag) {
        this.drag.current = event.clientX;
        this.drawSelection();
        return;
      }
      setCursor(this.timeAt(event.clientX), this, event);
    }

    onPointerDown(event) {
      if (event.button !== 0) return;
      const p = this.plot();
      const rect = this.svg.getBoundingClientRect();
      if (event.clientX - rect.left < p.left) return;
      this.drag = { start: event.clientX, current: event.clientX };
      try { this.svg.setPointerCapture(event.pointerId); } catch (error) { /* курсор без захвата */ }
      const finish = (upEvent) => {
        if (!this.drag) return;
        this.svg.removeEventListener("pointerup", finish);
        this.svg.removeEventListener("pointercancel", finish);
        const from = this.timeAt(Math.min(this.drag.start, upEvent.clientX));
        const to = this.timeAt(Math.max(this.drag.start, upEvent.clientX));
        const enough = Math.abs(upEvent.clientX - this.drag.start) > 8;
        this.drag = null;
        this.selection.replaceChildren();
        if (enough && to - from > 5000) applyZoom(from, to);
      };
      this.svg.addEventListener("pointerup", finish);
      this.svg.addEventListener("pointercancel", finish);
    }

    onKeyDown(event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const win = this.last || windowRange();
      const step = (win.to - win.from) / 60;
      const base = state.cursor === null ? win.to : state.cursor;
      const next = Math.min(win.to, Math.max(win.from, base + (event.key === "ArrowRight" ? step : -step)));
      event.preventDefault();
      setCursor(next, this, null);
    }

    drawSelection() {
      if (!this.drag) return;
      const rect = this.svg.getBoundingClientRect();
      const p = this.plot();
      const a = Math.max(p.left, Math.min(this.drag.start, this.drag.current) - rect.left);
      const b = Math.min(p.right, Math.max(this.drag.start, this.drag.current) - rect.left);
      this.selection.replaceChildren(
        node("rect", { class: "select-rect", x: a, y: p.top, width: Math.max(0, b - a), height: p.bottom - p.top })
      );
    }

    visibleSeries() {
      return this.options.series.filter((series) => !this.hidden.has(series.key));
    }

    render() {
      const win = windowRange();
      const p = this.plot();
      if (p.width < 40) return;
      this.svg.setAttribute("width", p.width);
      this.svg.setAttribute("height", this.height);
      this.svg.setAttribute("viewBox", `0 0 ${p.width} ${this.height}`);

      const points = Math.min(420, Math.max(40, Math.round((p.right - p.left) / 3)));
      const visible = this.visibleSeries();
      const data = visible.map((series) => ({
        series,
        ...Telemetry.query(series.metric, win.from, win.to, points),
      }));

      let max = 0;
      if (this.options.stacked) {
        for (let i = 0; i < points; i += 1) {
          let sum = 0;
          data.forEach((item) => { sum += item.v[i]; });
          if (sum > max) max = sum;
        }
      } else {
        data.forEach((item) => item.v.forEach((value) => { if (value > max) max = value; }));
      }
      if (this.options.threshold) max = Math.max(max, this.options.threshold * 1.1);
      const ticks = this.options.fixedMax ? niceTicks(this.options.fixedMax, 4) : niceTicks(max * 1.08 || 1, 4);
      const top = ticks[ticks.length - 1];

      const x = (t) => p.left + ((t - win.from) / (win.to - win.from)) * (p.right - p.left);
      const y = (v) => p.bottom - (v / top) * (p.bottom - p.top);

      const layer = document.createDocumentFragment();

      ticks.forEach((value) => {
        layer.append(node("line", { class: "grid-line", x1: p.left, x2: p.right, y1: y(value), y2: y(value) }));
        layer.append(node("text", { x: p.left - 8, y: y(value) + 4, "text-anchor": "end" }, axisValue(value, this.options.unit)));
      });

      const span = win.to - win.from;
      timeTicks(win.from, win.to, 6).forEach((t) => {
        layer.append(node("text", { x: x(t), y: p.bottom + 16, "text-anchor": "middle" }, formatTime(t, span)));
      });
      layer.append(node("line", { class: "axis-line", x1: p.left, x2: p.right, y1: p.bottom, y2: p.bottom }));

      const stackTop = new Float64Array(points);
      const rendered = [];
      data.forEach((item) => {
        const line = [];
        const area = [];
        const tops = new Float64Array(points);
        for (let i = 0; i < points; i += 1) {
          const base = this.options.stacked ? stackTop[i] : 0;
          const value = base + item.v[i];
          tops[i] = value;
          line.push(`${i === 0 ? "M" : "L"}${x(item.t[i]).toFixed(1)},${y(value).toFixed(1)}`);
          area.push(`${i === 0 ? "M" : "L"}${x(item.t[i]).toFixed(1)},${y(value).toFixed(1)}`);
        }
        if (this.options.stacked || this.options.area) {
          for (let i = points - 1; i >= 0; i -= 1) {
            const base = this.options.stacked ? stackTop[i] : 0;
            area.push(`L${x(item.t[i]).toFixed(1)},${y(base).toFixed(1)}`);
          }
          layer.append(node("path", { class: "series-area", d: area.join("") + "Z", fill: TONES[item.series.tone] }));
        }
        layer.append(node("path", { class: "series-line", d: line.join(""), stroke: TONES[item.series.tone] }));
        if (this.options.stacked) for (let i = 0; i < points; i += 1) stackTop[i] = tops[i];
        rendered.push({ series: item.series, t: item.t, v: item.v, top: tops });
      });

      if (this.options.threshold) {
        const ty = y(this.options.threshold);
        layer.append(node("line", { class: "threshold", x1: p.left, x2: p.right, y1: ty, y2: ty }));
        layer.append(node("text", { class: "threshold-label", x: p.right, y: ty - 6, "text-anchor": "end" }, this.options.thresholdLabel || ""));
      }

      if (this.options.annotations) {
        Telemetry.annotations(win.from, win.to).forEach((item) => {
          const ax = x(item.at);
          const color = item.kind === "resolve" ? TONES.good : item.kind === "alert" ? TONES.primary : TONES.cool;
          layer.append(node("line", { class: "annotation-line", x1: ax, x2: ax, y1: p.top, y2: p.bottom, stroke: color }));
          const flag = node("g", { class: "annotation-flag" });
          flag.append(node("rect", { x: ax - 3, y: p.top, width: 6, height: 6, fill: color }));
          flag.append(node("title", {}, `${formatTime(item.at, span)} · ${item.label}`));
          layer.append(flag);
        });
      }

      this.selection = node("g", {});
      this.cursorLayer = node("g", {});
      const capture = node("rect", {
        class: "capture",
        x: p.left,
        y: p.top,
        width: Math.max(0, p.right - p.left),
        height: p.bottom - p.top,
      });
      layer.append(capture, this.selection, this.cursorLayer);

      this.svg.replaceChildren(layer);
      this.last = { from: win.from, to: win.to, x, y, p, data: rendered, span };
      this.describe(rendered, win);
      if (state.cursor !== null) this.drawCursor(state.cursor);
    }

    describe(rendered, win) {
      const target = this.options.note && document.getElementById(this.options.note);
      if (!target) return;
      const parts = rendered.map((item) => {
        let peak = 0;
        let peakAt = win.from;
        for (let i = 0; i < item.v.length; i += 1) {
          if (item.v[i] > peak) { peak = item.v[i]; peakAt = item.t[i]; }
        }
        const current = item.v[item.v.length - 1];
        return `${item.series.label}: сейчас ${formatValue(current, this.options.unit)}, пик ${formatValue(peak, this.options.unit)} в ${formatTime(peakAt, win.to - win.from)}`;
      });
      target.textContent = parts.join(". ") + ".";
    }

    drawCursor(t) {
      if (!this.last || !this.cursorLayer) return;
      const { x, y, p, data } = this.last;
      if (t < this.last.from || t > this.last.to || !data.length) {
        this.cursorLayer.replaceChildren();
        return;
      }
      const cx = x(t);
      const group = document.createDocumentFragment();
      group.append(node("line", { class: "cursor-line", x1: cx, x2: cx, y1: p.top, y2: p.bottom }));
      data.forEach((item) => {
        const index = nearestIndex(item.t, t);
        group.append(node("circle", {
          class: "cursor-dot",
          cx: x(item.t[index]),
          cy: y(item.top[index]),
          r: 3,
          fill: TONES[item.series.tone],
        }));
      });
      this.cursorLayer.replaceChildren(group);
    }

    clearCursor() {
      if (this.cursorLayer) this.cursorLayer.replaceChildren();
    }

    readAt(t) {
      if (!this.last) return [];
      return this.last.data.map((item) => {
        const index = nearestIndex(item.t, t);
        return { label: item.series.label, tone: TONES[item.series.tone], value: formatValue(item.v[index], this.options.unit) };
      });
    }
  }

  function nearestIndex(times, t) {
    let low = 0;
    let high = times.length - 1;
    while (high - low > 1) {
      const mid = (low + high) >> 1;
      if (times[mid] < t) low = mid; else high = mid;
    }
    return Math.abs(times[low] - t) <= Math.abs(times[high] - t) ? low : high;
  }

  /* Тепловая карта распределения задержки: время по горизонтали,
     корзины времени ответа по вертикали, плотность передана прозрачностью. */
  class HeatChart {
    constructor(svg, noteId) {
      this.svg = svg;
      this.noteId = noteId;
      this.height = 196;
      this.margin = { left: 54, right: 14, top: 12, bottom: 24 };
      this.svg.style.height = this.height + "px";
      this.svg.addEventListener("pointermove", (event) => {
        const rect = this.svg.getBoundingClientRect();
        const ratio = (event.clientX - rect.left - this.margin.left) / Math.max(1, this.plotWidth);
        const win = windowRange();
        setCursor(win.from + Math.min(1, Math.max(0, ratio)) * (win.to - win.from), this, event);
      });
      this.svg.addEventListener("pointerleave", () => setCursor(null));
    }

    render() {
      const win = windowRange();
      const width = this.svg.clientWidth || this.svg.parentNode.clientWidth;
      if (width < 40) return;
      const left = this.margin.left;
      const right = width - this.margin.right;
      const topEdge = this.margin.top;
      const bottom = this.height - this.margin.bottom;
      this.plotWidth = right - left;
      this.svg.setAttribute("width", width);
      this.svg.setAttribute("height", this.height);
      this.svg.setAttribute("viewBox", `0 0 ${width} ${this.height}`);

      const columns = Math.min(160, Math.max(20, Math.round((right - left) / 7)));
      const { grid, edges } = Telemetry.histogram(win.from, win.to, columns);
      const rows = edges.length - 1;
      const cellW = (right - left) / columns;
      const cellH = (bottom - topEdge) / rows;
      const layer = document.createDocumentFragment();

      let peak = 0;
      let peakLabel = "";
      grid.forEach((column, ci) => {
        column.column.forEach((share, ri) => {
          if (share < 0.004) return;
          const yPos = bottom - (ri + 1) * cellH;
          layer.append(node("rect", {
            class: "heat-cell",
            x: left + ci * cellW,
            y: yPos,
            width: Math.ceil(cellW) + 0.5,
            height: Math.ceil(cellH) + 0.5,
            fill: TONES.neutral,
            "fill-opacity": Math.min(0.95, 0.08 + share * 1.6).toFixed(3),
          }));
          if (share > peak) {
            peak = share;
            peakLabel = edges[ri + 1] === Infinity ? "2048 мс и выше" : `${edges[ri]}–${edges[ri + 1]} мс`;
          }
        });
      });

      for (let ri = 0; ri < rows; ri += 1) {
        const label = ri === 0 ? "0" : String(edges[ri]);
        layer.append(node("text", { x: left - 8, y: bottom - ri * cellH - cellH / 2 + 4, "text-anchor": "end" }, label));
      }
      const span = win.to - win.from;
      timeTicks(win.from, win.to, 6).forEach((t) => {
        const cx = left + ((t - win.from) / span) * (right - left);
        layer.append(node("text", { x: cx, y: bottom + 16, "text-anchor": "middle" }, formatTime(t, span)));
      });
      layer.append(node("line", { class: "axis-line", x1: left, x2: right, y1: bottom, y2: bottom }));

      this.cursorLayer = node("g", {});
      layer.append(this.cursorLayer);
      this.svg.replaceChildren(layer);
      this.geometry = { left, right, topEdge, bottom, win };
      this.last = { span: win.to - win.from };

      const note = document.getElementById(this.noteId);
      if (note) note.textContent = `Основная масса запросов в корзине ${peakLabel}. Верхняя граница шкалы — 2048 мс и выше.`;
      if (state.cursor !== null) this.drawCursor(state.cursor);
    }

    drawCursor(t) {
      if (!this.geometry || !this.cursorLayer) return;
      const { left, right, topEdge, bottom, win } = this.geometry;
      if (t < win.from || t > win.to) { this.cursorLayer.replaceChildren(); return; }
      const cx = left + ((t - win.from) / (win.to - win.from)) * (right - left);
      this.cursorLayer.replaceChildren(node("line", { class: "cursor-line", x1: cx, x2: cx, y1: topEdge, y2: bottom }));
    }

    clearCursor() {
      if (this.cursorLayer) this.cursorLayer.replaceChildren();
    }

    readAt(t) {
      return [
        { label: "p50", tone: TONES.neutral, value: formatValue(Telemetry.latest("lat.p50", t), "мс") },
        { label: "p99", tone: TONES.primary, value: formatValue(Telemetry.latest("lat.p99", t), "мс") },
      ];
    }
  }

  const charts = [];
  const tooltip = document.getElementById("tooltip");

  function setCursor(t, source, event) {
    state.cursor = t;
    charts.forEach((chart) => (t === null ? chart.clearCursor() : chart.drawCursor(t)));
    if (t === null || !source || !event) {
      tooltip.dataset.open = "false";
      return;
    }
    const rows = source.readAt(t);
    const span = (source.last ? source.last.span : state.range);
    tooltip.replaceChildren();
    const time = document.createElement("span");
    time.className = "tooltip__time";
    time.textContent = formatTime(t, span);
    tooltip.append(time);
    rows.forEach((row) => {
      const line = document.createElement("span");
      line.className = "tooltip__row";
      line.style.setProperty("--swatch", row.tone);
      const mark = document.createElement("i");
      const label = document.createElement("span");
      label.textContent = row.label;
      const value = document.createElement("b");
      value.textContent = row.value;
      line.append(mark, label, value);
      tooltip.append(line);
    });
    tooltip.dataset.open = "true";
    const box = tooltip.getBoundingClientRect();
    const x = Math.min(window.innerWidth - box.width - 12, event.clientX + 16);
    const y = Math.min(window.innerHeight - box.height - 12, event.clientY + 16);
    tooltip.style.left = Math.max(12, x) + "px";
    tooltip.style.top = Math.max(12, y) + "px";
  }

  function applyZoom(from, to) {
    state.zoom = { from, to };
    const chip = document.getElementById("zoom-chip");
    chip.dataset.active = "true";
    const span = to - from;
    document.getElementById("zoom-label").textContent =
      `${formatTime(from, span)} — ${formatTime(to, span)}`;
    renderAll();
  }

  function resetZoom() {
    state.zoom = null;
    document.getElementById("zoom-chip").dataset.active = "false";
    renderAll();
  }

  /* Панели данных */
  function renderStats() {
    const win = windowRange();
    const span = win.to - win.from;
    const previous = { from: win.from - span, to: win.from };
    /* Знак окрашивается только там, где у направления есть однозначный смысл:
       рост трафика сам по себе не хорош и не плох. */
    const cards = [
      { id: "stat-rps", metric: "rps.total", unit: "", signal: false, tone: "neutral" },
      { id: "stat-errors", metric: "err.share", unit: "%", signal: true, tone: "primary" },
      { id: "stat-latency", metric: "lat.p99", unit: "мс", signal: true, tone: "warm" },
      { id: "stat-cpu", metric: "cpu.max", unit: "%", signal: true, tone: "cool" },
    ];
    cards.forEach((card) => {
      const host = document.getElementById(card.id);
      const current = Telemetry.average(card.metric, win.from, win.to, 90);
      const before = Telemetry.average(card.metric, previous.from, previous.to, 90);
      const delta = before === 0 ? 0 : ((current - before) / before) * 100;
      host.querySelector(".metric__value").textContent = formatValue(current, card.unit);
      const deltaEl = host.querySelector(".metric__delta");
      const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
      deltaEl.textContent = `${sign}${short.format(Math.abs(delta))} % к предыдущему интервалу`;
      deltaEl.dataset.trend = !card.signal || Math.abs(delta) < 1 ? "flat" : delta > 0 ? "up" : "down";
      drawSpark(host.querySelector(".metric__spark"), card.metric, win, TONES[card.tone]);
    });
  }

  function drawSpark(svg, metric, win, stroke) {
    const width = 108;
    const height = 34;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const series = Telemetry.query(metric, win.from, win.to, 48);
    let max = 0;
    let min = Infinity;
    series.v.forEach((value) => { if (value > max) max = value; if (value < min) min = value; });
    const range = Math.max(1e-6, max - min);
    const path = [];
    series.v.forEach((value, i) => {
      const x = (i / (series.v.length - 1)) * width;
      const y = height - 3 - ((value - min) / range) * (height - 6);
      path.push(`${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`);
    });
    svg.replaceChildren(node("path", { d: path.join(""), fill: "none", stroke: stroke, "stroke-width": 1.5 }));
  }

  function renderEndpoints() {
    const win = windowRange();
    const rows = Telemetry.endpoints(win.from, win.to);
    const key = state.sort.key;
    rows.sort((a, b) => {
      const left = a[key];
      const right = b[key];
      if (typeof left === "string") return left.localeCompare(right, "ru") * state.sort.dir;
      return (left - right) * state.sort.dir;
    });
    const maxRps = Math.max(...rows.map((row) => row.rps));
    const maxErrors = Math.max(...rows.map((row) => row.errors), 0.01);
    const body = document.querySelector("#endpoints tbody");
    body.replaceChildren();
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.append(cell(row.path, "path"), cell(row.service));
      tr.append(barCell(numbers.format(row.rps), row.rps / maxRps, false));
      tr.append(cell(numbers.format(row.p95), "num"));
      tr.append(barCell(decimals.format(row.errors) + " %", row.errors / maxErrors, row.errors > 1));
      body.append(tr);
    });
  }

  function cell(text, className) {
    const td = document.createElement("td");
    td.textContent = text;
    if (className) td.className = className;
    return td;
  }

  function barCell(text, ratio, risky) {
    const td = document.createElement("td");
    const wrap = document.createElement("span");
    wrap.className = "cell-bar" + (risky ? " cell-bar--risk" : "");
    const track = document.createElement("span");
    track.className = "cell-bar__track";
    const fill = document.createElement("span");
    fill.className = "cell-bar__fill";
    fill.style.setProperty("--value", Math.max(2, Math.min(100, ratio * 100)).toFixed(1) + "%");
    track.append(fill);
    const value = document.createElement("span");
    value.textContent = text;
    wrap.append(track, value);
    td.append(wrap);
    return td;
  }

  const LEVELS = { info: "информация", warn: "внимание", error: "ошибка" };

  function renderLog() {
    const win = windowRange();
    const entries = Telemetry.logs(win.from, win.to, 220)
      .filter((entry) => state.logLevel === "all" || entry.level === state.logLevel);
    const list = document.getElementById("log");
    list.replaceChildren();
    document.getElementById("log-meta").textContent =
      `${numbers.format(entries.length)} записей за выбранный диапазон`;
    if (!entries.length) {
      const empty = document.createElement("li");
      empty.className = "log-empty";
      empty.textContent = "Записей выбранного уровня в диапазоне нет.";
      list.append(empty);
      return;
    }
    entries.slice(0, 120).forEach((entry) => {
      const li = document.createElement("li");
      li.dataset.level = entry.level;
      const time = document.createElement("time");
      time.dateTime = new Date(entry.at).toISOString();
      time.textContent = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(entry.at);
      const level = document.createElement("span");
      level.className = "level";
      const status = document.createElement("span");
      status.className = "status status--" + (entry.level === "info" ? "ok" : entry.level);
      status.textContent = LEVELS[entry.level];
      level.append(status);
      const text = document.createElement("p");
      text.textContent = entry.text + " ";
      const detail = document.createElement("span");
      detail.className = "detail";
      detail.textContent = entry.detail;
      text.append(detail);
      li.append(time, level, text);
      list.append(li);
    });
  }

  function renderEvents() {
    const win = windowRange();
    const items = Telemetry.annotations(win.from, win.to);
    const host = document.getElementById("events");
    host.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("li");
      empty.textContent = "В выбранном диапазоне событий не было.";
      empty.className = "muted";
      host.append(empty);
      return;
    }
    items.slice().reverse().forEach((item) => {
      const li = document.createElement("li");
      const time = document.createElement("time");
      time.dateTime = new Date(item.at).toISOString();
      time.textContent = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(item.at);
      const body = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.label;
      const note = document.createElement("span");
      note.textContent = item.note;
      body.append(title, note);
      li.append(time, body);
      host.append(li);
    });
  }

  function renderAll() {
    charts.forEach((chart) => chart.render());
    renderStats();
    renderEndpoints();
    renderLog();
    renderEvents();
    const live = document.getElementById("live");
    const timeFormat = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    live.dataset.state = state.paused ? "paused" : "live";
    document.getElementById("live-time-running").textContent = timeFormat.format(Date.now());
    document.getElementById("live-time-paused").textContent = timeFormat.format(now());
  }

  /* Сборка панелей */
  charts.push(new TimeChart(document.getElementById("chart-rps"), {
    series: Telemetry.SERVICES.map((service) => ({
      key: service.key,
      metric: "rps." + service.key,
      label: service.label,
      tone: service.tone,
    })),
    unit: "",
    legend: "legend-rps",
    note: "desc-rps",
    annotations: true,
    height: 232,
  }));

  charts.push(new TimeChart(document.getElementById("chart-err"), {
    series: [
      { key: "5xx", metric: "err.5xx", label: "5xx", tone: "primary" },
      { key: "timeout", metric: "err.timeout", label: "таймауты", tone: "warm" },
      { key: "4xx", metric: "err.4xx", label: "4xx", tone: "cool" },
    ],
    unit: "",
    stacked: true,
    legend: "legend-err",
    note: "desc-err",
    height: 232,
  }));

  charts.push(new TimeChart(document.getElementById("chart-lat"), {
    series: [
      { key: "p99", metric: "lat.p99", label: "p99", tone: "primary" },
      { key: "p95", metric: "lat.p95", label: "p95", tone: "warm" },
      { key: "p50", metric: "lat.p50", label: "p50", tone: "neutral" },
    ],
    unit: "мс",
    legend: "legend-lat",
    note: "desc-lat",
    threshold: 500,
    thresholdLabel: "порог 500 мс",
    annotations: true,
  }));

  charts.push(new HeatChart(document.getElementById("chart-heat"), "desc-heat"));

  charts.push(new TimeChart(document.getElementById("chart-cpu"), {
    series: Telemetry.NODES.map((node_, index) => ({
      key: node_.key,
      metric: "cpu." + node_.key,
      label: node_.label,
      tone: ["neutral", "primary", "cool"][index],
    })),
    unit: "%",
    legend: "legend-cpu",
    note: "desc-cpu",
    height: 296,
    threshold: 90,
    thresholdLabel: "порог 90 %",
    fixedMax: 100,
  }));

  /* Управление */
  document.getElementById("range").addEventListener("change", (event) => {
    state.range = Number(event.target.value);
    resetZoom();
  });

  document.getElementById("refresh").addEventListener("change", (event) => {
    state.refresh = Number(event.target.value);
    schedule();
  });

  document.getElementById("zoom-reset").addEventListener("click", resetZoom);

  const pauseButton = document.getElementById("pause");
  function togglePause() {
    state.paused = !state.paused;
    state.frozenNow = state.paused ? Date.now() : null;
    pauseButton.setAttribute("aria-pressed", String(state.paused));
    schedule();
    renderAll();
  }
  pauseButton.addEventListener("click", togglePause);

  document.querySelectorAll('#log-level input').forEach((input) => {
    input.addEventListener("change", () => {
      state.logLevel = input.value;
      renderLog();
    });
  });

  document.querySelectorAll("#endpoints th").forEach((th) => {
    th.querySelector("button").addEventListener("click", () => {
      const key = th.dataset.key;
      state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : -1 };
      document.querySelectorAll("#endpoints th").forEach((other) => {
        other.setAttribute("aria-sort", other === th ? (state.sort.dir === 1 ? "ascending" : "descending") : "none");
      });
      renderEndpoints();
    });
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (target && target.matches("input, select, textarea")) return;
    if (event.code === "Space") {
      if (target && target.closest("button")) return;
      event.preventDefault();
      togglePause();
      return;
    }
    if (event.key === "r" || event.key === "R" || event.key === "к" || event.key === "К") { renderAll(); return; }
    if (event.key === "Escape") { resetZoom(); return; }
    if (event.key === "[" || event.key === "]") {
      const select = document.getElementById("range");
      const next = select.selectedIndex + (event.key === "]" ? 1 : -1);
      if (next < 0 || next >= select.options.length) return;
      select.selectedIndex = next;
      state.range = Number(select.value);
      resetZoom();
    }
  });

  let timer = null;
  function schedule() {
    if (timer) clearInterval(timer);
    timer = null;
    if (state.refresh > 0 && !state.paused) timer = setInterval(renderAll, state.refresh);
  }

  let resizeFrame = null;
  new ResizeObserver(() => {
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => charts.forEach((chart) => chart.render()));
  }).observe(document.querySelector(".board"));

  function setPrintMode(active) {
    document.documentElement.dataset.print = String(active);
    refreshTones();
    charts.forEach((chart) => {
      if (chart.refreshLegend) chart.refreshLegend();
      chart.render();
    });
  }
  window.addEventListener("beforeprint", () => setPrintMode(true));
  window.addEventListener("afterprint", () => setPrintMode(false));

  /* Начальное состояние берётся из разметки, чтобы значения не расходились. */
  state.range = Number(document.getElementById("range").value);
  state.refresh = Number(document.getElementById("refresh").value);
  state.logLevel = document.querySelector("#log-level input:checked").value;
  renderAll();
  schedule();
})();
