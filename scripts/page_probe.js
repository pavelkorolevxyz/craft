// In-browser page check. The runner in check_project.py calls craftProbe
// for each test viewport and passes the result back to Python as JSON.
// The visual checks look for what a reader would see: overlapping and overflowing text,
// low contrast, small type and small tap targets.

function craftProbe(frame, surface) {
  const win = frame.contentWindow;
  const document = frame.contentDocument;
  const root = document.documentElement;
  const styleOf = win.getComputedStyle.bind(win);
  const innerWidth = win.innerWidth;
  const sample = (list) => list.slice(0, 3).map(describe);

  function describe(el) {
    let name = el.tagName.toLowerCase();
    if (el.id) name += `#${el.id}`;
    if (typeof el.className === "string" && el.className.trim()) name += "." + el.className.trim().split(/\s+/).slice(0, 2).join(".");
    const text = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 32);
    return text ? `${name} "${text}"` : name;
  }

  function toggleTheme() {
    const before = root.dataset.theme;
    const button = document.querySelector("[data-theme-toggle]");
    if (surface === "slides") document.dispatchEvent(new win.KeyboardEvent("keydown", { key: "T" }));
    else if (button) button.click();
    return before !== root.dataset.theme;
  }

  // Color transitions would still return the old value right after a theme switch.
  const still = document.createElement("style");
  still.textContent = "*,*::before,*::after{transition:none!important;animation:none!important}";
  document.head.append(still);
  const changed = toggleTheme();
  const controls = [...document.querySelectorAll("button,input,select,textarea,a[href]")];
  const unnamed = controls.filter((el) => {
    const label = el.closest("label") || (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`));
    return !(el.getAttribute("aria-label") || el.getAttribute("title") || el.textContent.trim() || label);
  }).length;
  const ranks = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((el) => Number(el.tagName[1]));
  const jumps = ranks.slice(1).filter((rank, i) => rank > ranks[i] + 1).length;
  const slides = [...document.querySelectorAll(".slide")];
  const panel = document.querySelector(".help-panel");
  let spill = 0;
  if (panel) {
    const hidden = panel.hidden;
    panel.hidden = false;
    spill = Math.max(0, ...[...panel.querySelectorAll("button,label")].map((el) => Math.ceil(el.getBoundingClientRect().right - innerWidth)));
    panel.hidden = hidden;
  }

  const result = {
    scroll: root.scrollWidth,
    viewport: innerWidth,
    unnamed,
    jumps,
    themeChanged: changed,
    slides: slides.length,
    undeclared: slides.filter((el) => !el.dataset.slideLayout).length,
    active: document.querySelectorAll(".slide[data-active]").length,
    spill,
    shell: Boolean(document.querySelector("[data-craft-shell]")),
  };
  if (surface !== "interface") return result;

  const visible = (el) => el.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true })
    && el.getBoundingClientRect().width > 0 && !el.closest(".sr-only,.icon-sprite,svg");
  const elements = [...document.body.querySelectorAll("*")].filter(visible);

  const bordered = elements.filter((el) => el.getBoundingClientRect().width > 8 && !el.closest("table"));
  const owns = (el, side) => parseFloat(styleOf(el)[`border${side}Width`]) > 0 && styleOf(el)[`border${side}Style`] !== "none";
  const tops = bordered.filter((el) => owns(el, "Top"));
  const doubleBorders = bordered.filter((el) => owns(el, "Bottom")).filter((a) => tops.some((b) => {
    if (a === b) return false;
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    if (Math.abs(ar.bottom - br.top) > 0.75) return false;
    const overlap = Math.min(ar.right, br.right) - Math.max(ar.left, br.left);
    return overlap > 8 && overlap >= Math.min(ar.width, br.width) * 0.8;
  }));
  const pageTabs = [
    ...document.querySelectorAll(".workspace-head + .tabs:not(.tabs--page)"),
    // The section bar spans the full width of the header above it. Without
    // a header in front of it, the window width is the measure.
    ...[...document.querySelectorAll(".tabs--page > .tablist")].filter((el) => {
      const r = el.getBoundingClientRect();
      const head = el.parentElement.previousElementSibling;
      const frame = head?.matches(".workspace-head") ? head.getBoundingClientRect() : { left: 0, right: root.clientWidth };
      return Math.abs(r.left - frame.left) > 0.5 || Math.abs(r.right - frame.right) > 0.5;
    }),
  ];

  // Text means an own text node outside code and scrollable tables.
  const textRect = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    return range.getBoundingClientRect();
  };
  const texts = elements.filter((el) => [...el.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim()));
  const prose = texts.filter((el) => !el.closest("pre,code,.table-scroll,.scroll-region,input,select,textarea"));

  const outside = prose.filter((el) => {
    const s = styleOf(el);
    if (s.overflowX !== "visible") return false;
    const t = textRect(el);
    const box = el.getBoundingClientRect();
    return t.width > 0 && (t.right > box.right + 2 || t.left < box.left - 2);
  });
  const clipped = prose.filter((el) => {
    const s = styleOf(el);
    return ["hidden", "clip"].includes(s.overflowX) && s.textOverflow !== "ellipsis" && el.scrollWidth > el.clientWidth + 1;
  });
  const tiny = texts.filter((el) => parseFloat(styleOf(el).fontSize) < 11.5);

  const pinned = (el) => { for (let p = el; p; p = p.parentElement) if (["fixed", "sticky"].includes(styleOf(p).position)) return true; return false; };
  const placed = prose.filter((el) => !pinned(el)).map((el) => [el, textRect(el)]).filter(([, r]) => r.width > 2 && r.height > 2);
  const overlaps = [];
  for (let i = 0; i < placed.length && overlaps.length < 10; i += 1) {
    for (let j = i + 1; j < placed.length; j += 1) {
      const [a, ra] = placed[i];
      const [b, rb] = placed[j];
      if (a.contains(b) || b.contains(a)) continue;
      const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (x <= 3 || y <= 3) continue;
      // Hit testing sees only the viewport, so scroll the point on screen first.
      const cy = (Math.max(ra.top, rb.top) + Math.min(ra.bottom, rb.bottom)) / 2 + win.scrollY;
      win.scrollTo(0, Math.max(0, cy - win.innerHeight / 2));
      const na = textRect(a);
      const nb = textRect(b);
      const hits = document.elementsFromPoint((Math.max(na.left, nb.left) + Math.min(na.right, nb.right)) / 2, (Math.max(na.top, nb.top) + Math.min(na.bottom, nb.bottom)) / 2);
      if (hits.some((h) => a.contains(h)) && hits.some((h) => b.contains(h))) overlaps.push(a);
    }
  }
  win.scrollTo(0, 0);

  const parse = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r, g, b, a };
  };
  const blend = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const luminance = ({ r, g, b }) => {
    const channel = (v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  // Backdrop from top to bottom. For each ancestor, solid gradients come first in
  // declaration order, then the background color. Collection stops at the first opaque color.
  const backdrop = (el) => {
    const layers = [];
    for (let p = el; p; p = p.parentElement) {
      const s = styleOf(p);
      if (s.backgroundImage.includes("url(")) return null;
      for (const m of s.backgroundImage.matchAll(/linear-gradient\((rgba?\([^)]+\)),\s*(rgba?\([^)]+\))\)/g)) {
        if (m[1] === m[2]) layers.push(parse(m[1]));
      }
      const color = parse(s.backgroundColor);
      if (color && color.a > 0) layers.push(color);
      if (color && color.a >= 1) break;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (const layer of layers.reverse()) base = blend(layer, base);
    return base;
  };
  const disabled = (el) => Boolean(el.closest(":disabled,[aria-disabled=true],fieldset:disabled")) || Boolean(el.closest("label")?.querySelector(":disabled"));
  const lowContrast = (theme) => prose.filter((el) => !disabled(el)).filter((el) => {
    const s = styleOf(el);
    const fg = parse(s.color);
    const bg = backdrop(el);
    if (!fg || !bg) return false;
    const text = blend(fg, bg);
    const l1 = luminance(text);
    const l2 = luminance(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const size = parseFloat(s.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(s.fontWeight) >= 700);
    return ratio < (large ? 3 : 4.5) - 0.01;
  }).map((el) => `${theme}: ${describe(el)}`);
  const contrast = lowContrast(root.dataset.theme);
  // Second theme: through the toggle when there is a shell, otherwise through the attribute.
  const before = root.dataset.theme;
  if (!toggleTheme()) root.dataset.theme = before === "light" ? "dark" : "light";
  contrast.push(...lowContrast(root.dataset.theme));

  const inSentence = (el) => el.matches("a") && [...el.parentElement.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim());
  const smallTargets = elements.filter((el) => el.matches("button,a[href],input:not([type=hidden]),select,textarea,summary,[role=tab]") && !inSentence(el)).filter((el) => {
    const own = el.getBoundingClientRect();
    const label = el.closest("label")?.getBoundingClientRect() || own;
    return Math.max(own.height, label.height) < 24 || Math.max(own.width, label.width) < 24;
  });

  return Object.assign(result, {
    doubleBorders: sample(doubleBorders), doubleBordersCount: doubleBorders.length,
    pageTabs: sample(pageTabs), pageTabsCount: pageTabs.length,
    overlaps: sample(overlaps), overlapsCount: overlaps.length,
    outside: sample(outside), outsideCount: outside.length,
    clipped: sample(clipped), clippedCount: clipped.length,
    tiny: sample(tiny), tinyCount: tiny.length,
    contrast: contrast.slice(0, 3), contrastCount: contrast.length,
    smallTargets: sample(smallTargets), smallTargetsCount: smallTargets.length,
  });
}
