#!/usr/bin/env node
// Walks every screen state of a Craft deck in Chromium over CDP.
//
//   node scripts/deck_probe.mjs path/to/index.html [--shots dir] [--passes a,b] [--quick]
//
// Passes: viewports, frames, light, phone, panel, motion, navigation, video,
// print. All run by default; --quick drops motion and video. The source
// checks and the network and error log run every time.
//
// Prints a JSON report with errors and warnings. The probe knows nothing
// about the content of a given talk. It checks the contracts of the
// mechanics, layouts and delivery, not the texts and numbers.
import { execFileSync } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './cdp.mjs';
import { probeViewports } from './page_check.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : null;
};
const index = path.resolve(args.find((value, position) => !value.startsWith('--') && !['--shots', '--registry'].includes(args[position - 1])) || '');
const shots = option('--shots');
const PASSES = ['viewports', 'frames', 'light', 'phone', 'panel', 'motion', 'navigation', 'video', 'print'];
const requested = option('--passes');
// An empty --passes runs only the source checks.
const passes = new Set(requested !== null ? requested.split(',').filter(Boolean) : PASSES);
for (const name of passes) if (!PASSES.includes(name)) throw Error(`unknown pass ${name}; available: ${PASSES.join(', ')}`);
if (args.includes('--quick')) { passes.delete('motion'); passes.delete('video'); }
const quick = !passes.has('video');
// CSS animations play this many times faster in the motion pass. The pass
// checks where motion ends and what it covers, not how it looks over time.
const MOTION_RATE = 10;
const viewportList = (option('--viewports') || '1440x900,390x844,320x720').split(',').map((item) => item.split('x').map(Number));
const registryPath = option('--registry') || path.join(here, 'craft.json');
const registry = JSON.parse(await readFile(registryPath, 'utf8'));
const guidance = registry.surfaces.slides.layoutGuidance;
const signatures = Object.fromEntries(Object.entries(guidance).map(([id, item]) => [id, item.signature || []]));
const knownLayouts = Object.keys(guidance);
const base = pathToFileURL(index).href;
const html = await readFile(index, 'utf8');
const webDelivery = /<html\b[^>]*data-craft-delivery="web"/.test(html);
const allowedHosts = new Set(['fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.jsdelivr.net', 'unpkg.com']);

const report = { index, pages: [], sources: 0, errors: [], warnings: [], images: [], pdf: {}, timings: {} };
const seen = new Map();
function issue(list, kind, where, message) {
  // The same error on every reveal step of one slide is one entry.
  const signature = `${kind}|${where?.key ?? ''}|${message}`;
  if (seen.has(signature)) return;
  seen.set(signature, true);
  list.push({ kind, page: where?.page ?? null, key: where?.key ?? null, step: where?.step ?? null, message });
}
const error = (kind, where, message) => issue(report.errors, kind, where, message);
const warn = (kind, where, message) => issue(report.warnings, kind, where, message);

// Page functions. They are installed after every navigation.
const PAGE_LIB = String.raw`(() => {
  if (window.__probe) return true;
  const describe = (el) => {
    if (!el) return '';
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((c) => '.' + c).join('') : '';
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
    return el.tagName.toLowerCase() + cls + (text ? ' "' + text + '"' : '');
  };
  const active = () => document.querySelector('.slide[data-active]');
  const settle = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const hiddenBy = (el, stop) => {
    for (let node = el; node && node !== stop.parentElement; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === 'none') return 'display';
      if (style.visibility === 'hidden' || Number(style.opacity) === 0) return 'opacity';
    }
    return null;
  };
  const inUnshownFrag = (el) => Boolean(el.closest('.frag:not([data-shown])'));
  const canvasOf = (slide) => slide.querySelector(':scope > .slide-canvas') || slide;
  const clipsOf = (el, slide) => {
    const result = [];
    const canvas = canvasOf(slide);
    for (let node = el.parentElement; node && node !== canvas && node !== slide; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.overflowX !== 'visible' || style.overflowY !== 'visible') result.push(node);
    }
    return result;
  };
  const outside = (rect, box, pad = 2) => rect.left < box.left - pad || rect.right > box.right + pad || rect.top < box.top - pad || rect.bottom > box.bottom + pad;
  const fullyOutside = (rect, box) => rect.right <= box.left || rect.left >= box.right || rect.bottom <= box.top || rect.top >= box.bottom;
  const area = (r) => Math.max(0, r.width) * Math.max(0, r.height);
  const overlapArea = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));

  const stop = (slide) => slide.parentElement;
  // The visible part under an ancestor's clip-path: inset(). The curtain and
  // similar compositions stack frames and uncover them by clipping.
  function clipPathed(el, boundary, rect) {
    for (let node = el; node && node !== boundary; node = node.parentElement) {
      const value = getComputedStyle(node).clipPath;
      const match = value && value.match(/^inset\(([^)]*)\)/);
      if (!match) continue;
      const box = node.getBoundingClientRect();
      const parts = match[1].split(/\s+/).map((part) => part.endsWith('%') ? Number.parseFloat(part) / 100 : Number.parseFloat(part) || 0);
      const [top, right = top, bottom = top, left = right] = parts;
      const scale = (value, size) => (value <= 1 && value >= 0 && match[1].includes('%') ? value * size : value);
      const visible = {
        left: box.left + scale(left, box.width), right: box.right - scale(right, box.width),
        top: box.top + scale(top, box.height), bottom: box.bottom - scale(bottom, box.height),
      };
      const clipped = {
        left: Math.max(rect.left, visible.left), right: Math.min(rect.right, visible.right),
        top: Math.max(rect.top, visible.top), bottom: Math.min(rect.bottom, visible.bottom),
      };
      if (clipped.right - clipped.left < 1 || clipped.bottom - clipped.top < 1) return null;
      rect = { ...clipped, width: clipped.right - clipped.left, height: clipped.bottom - clipped.top };
    }
    return rect;
  }

  function textRects(slide) {
    const result = [];
    const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      if (!node.textContent.trim() || !node.parentElement) continue;
      const parent = node.parentElement;
      if (parent.closest('.svg-defs, script, style, [hidden]')) continue;
      if (hiddenBy(parent, slide)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      // Range returns the font box. With a tight line-height it is taller
      // than the line and touches the next block even though the glyphs
      // do not overlap, so we limit the height to the line.
      const lineHeight = Number.parseFloat(getComputedStyle(parent).lineHeight);
      for (const box of range.getClientRects()) {
        if (box.width < 1 || box.height < 1) continue;
        const inset = Number.isFinite(lineHeight) && lineHeight < box.height ? (box.height - lineHeight) / 2 : 0;
        let rect = { left: box.left, right: box.right, width: box.width, top: box.top + inset, bottom: box.bottom - inset, height: box.height - inset * 2 };
        rect = clipPathed(parent, stop(slide), rect);
        if (rect) result.push({ parent, rect });
      }
    }
    return result;
  }

  function painted(image) {
    const box = image.getBoundingClientRect();
    const style = getComputedStyle(image);
    const nw = image.naturalWidth || image.videoWidth || 0;
    const nh = image.naturalHeight || image.videoHeight || 0;
    if (!nw || !nh || style.objectFit !== 'contain') return box;
    const scale = Math.min(box.width / nw, box.height / nh);
    const width = nw * scale;
    const height = nh * scale;
    const [px, py] = style.objectPosition.split(' ').map((value) => (value.endsWith('%') ? Number.parseFloat(value) / 100 : 0.5));
    const left = box.left + (box.width - width) * px;
    const top = box.top + (box.height - height) * py;
    return { left, top, right: left + width, bottom: top + height, width, height };
  }

  function inspect(options = {}) {
    const slide = active();
    const bounds = slide.getBoundingClientRect();
    const result = { clip: [], overflow: [], overlap: [], number: [], frag: [], invisible: [], images: [], qr: [], service: {} };
    result.bentoRows = [...slide.querySelectorAll('.bento-row')].filter((row) => {
      const heights = [...row.children].map((tile) => tile.getBoundingClientRect().height);
      return heights.length > 1 && Math.max(...heights) - Math.min(...heights) > 1;
    }).length;
    const texts = textRects(slide);
    for (const { parent, rect } of texts) {
      // data-clip="intended" marks a window where text is partly hidden on
      // purpose, such as a timer strip or a ticker.
      if (parent.closest('.slide-status, [data-clip="intended"]')) continue;
      const clips = clipsOf(parent, slide);
      if (clips.some((clip) => fullyOutside(rect, clip.getBoundingClientRect()))) continue; // hidden by scrolling on purpose
      const clipped = clips.find((clip) => outside(rect, clip.getBoundingClientRect()));
      if (clipped) result.clip.push(describe(parent) + ' in ' + describe(clipped).split(' "')[0]);
      else if (outside(rect, bounds)) result.overflow.push(describe(parent));
    }
    const number = slide.querySelector('.slide-number');
    const numberRect = number?.getBoundingClientRect();
    // Count overlap on the visible part only. Text past the edge of a
    // clipping container, like a timer window or a strip, is not visible
    // and gets in nobody's way.
    const plain = texts.filter(({ parent }) => !parent.closest('.slide-status')).flatMap(({ parent, rect }) => {
      let visible = rect;
      for (const clip of clipsOf(parent, slide)) {
        const box = clip.getBoundingClientRect();
        const left = Math.max(visible.left, box.left), right = Math.min(visible.right, box.right);
        const top = Math.max(visible.top, box.top), bottom = Math.min(visible.bottom, box.bottom);
        if (right - left < 1 || bottom - top < 1) return [];
        visible = { left, right, top, bottom, width: right - left, height: bottom - top };
      }
      return [{ parent, rect: visible }];
    });
    for (let i = 0; i < plain.length; i += 1) {
      const a = plain[i];
      if (numberRect && !number.contains(a.parent) && overlapArea(a.rect, numberRect) > 4) result.number.push(describe(a.parent));
      for (let j = i + 1; j < plain.length; j += 1) {
        const b = plain[j];
        if (a.parent === b.parent || a.parent.contains(b.parent) || b.parent.contains(a.parent)) continue;
        const shared = overlapArea(a.rect, b.rect);
        if (shared > 4 && shared > 0.3 * Math.min(area(a.rect), area(b.rect))) {
          result.overlap.push(describe(a.parent) + ' and ' + describe(b.parent));
        }
      }
    }

    const step = Number(slide.dataset.step);
    [...slide.querySelectorAll('.frag')].forEach((fragment, i) => {
      const expected = Number(fragment.dataset.fragStep) <= step;
      const shown = fragment.hasAttribute('data-shown');
      const visible = !hiddenBy(fragment, slide);
      if (shown !== expected || visible !== expected) result.frag.push(i + 1);
    });

    if (options.invisible) {
      const candidates = new Set();
      const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
      for (let node; (node = walker.nextNode());) if (node.textContent.trim() && node.parentElement) candidates.add(node.parentElement);
      slide.querySelectorAll('img, video, canvas, svg:not([aria-hidden="true"])').forEach((el) => candidates.add(el));
      for (const el of candidates) {
        // An invisible aria-hidden element is a deliberate layout spacer.
        if (el.closest('.svg-defs, script, style, [hidden], .sr-only, [data-exit="intended"], [aria-hidden="true"]') || inUnshownFrag(el)) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1) continue;
        if (hiddenBy(el, slide) === 'opacity') result.invisible.push(describe(el));
      }
    }

    for (const image of slide.querySelectorAll('img')) {
      // Images of future steps are not visible yet and hold their place.
      if (hiddenBy(image, slide) === 'display' || inUnshownFrag(image)) continue;
      const box = image.getBoundingClientRect();
      const broken = image.complete && image.naturalWidth === 0;
      const clip = clipsOf(image, slide).find((node) => !image.closest('[data-crop]') && outside(box, node.getBoundingClientRect()));
      // Empty space between the outline and the image. The outline is the
      // frame's border, or the image itself if that border is transparent.
      const frame = image.parentElement?.closest('.frame');
      let frameGap = 0;
      if (frame && getComputedStyle(image).objectFit === 'contain' && image.naturalWidth) {
        const content = painted(image);
        const outline = /rgba\(.*,\s*0\)$|transparent/.test(getComputedStyle(frame).borderTopColor) ? image : frame;
        const outlineBox = outline.getBoundingClientRect();
        frameGap = Math.max(outlineBox.width - content.width, outlineBox.height - content.height) / bounds.width;
      }
      result.images.push({
        src: image.getAttribute('src') || image.currentSrc,
        broken,
        natural: [image.naturalWidth, image.naturalHeight],
        // Size on a 1920 px wide stage, to compare with the source file.
        at1920: [Math.round(box.width * 1920 / bounds.width), Math.round(box.height * 1920 / bounds.width)],
        clipped: clip ? describe(clip).split(' "')[0] : null,
        outside: !clip && outside(box, bounds) && !image.closest('[data-crop]'),
        frameGap: Math.round(frameGap * 1000) / 1000,
      });
    }

    for (const qr of slide.querySelectorAll('.qr')) {
      const svg = qr.querySelector('svg');
      const img = qr.querySelector('img');
      const holder = qr.closest('.qr-link') || slide;
      const link = [...holder.querySelectorAll('a[href]')].find((a) => !hiddenBy(a, slide) && a.textContent.trim());
      const qrStyle = getComputedStyle(qr);
      const svgColor = svg ? getComputedStyle(svg).color : null;
      // Module paint is the shape's explicit fill or stroke. For <use> we read
      // the source shape, where currentColor takes the color of the use site.
      const paintOf = (shape) => {
        const target = shape.tagName.toLowerCase() === 'use'
          ? document.querySelector(shape.getAttribute('href') || shape.getAttribute('xlink:href'))
          : shape;
        if (!target) return ['no shape'];
        const declared = ['fill', 'stroke'].map((name) => target.getAttribute(name) || target.style[name]).filter((value) => value && value !== 'none');
        if (shape !== target) return declared.map((value) => (value === 'currentColor' ? svgColor : value));
        const style = getComputedStyle(shape);
        return declared.length ? declared.map((value, i) => (i === 0 && target.getAttribute('fill') && target.getAttribute('fill') !== 'none' ? style.fill : style.stroke)) : [style.fill];
      };
      const paints = svg ? [...svg.querySelectorAll('path, rect, use, polygon')].flatMap(paintOf) : [];
      const address = link?.textContent.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
      const mentions = address ? (slide.innerText.split(address).length - 1) : 0;
      const box = qr.getBoundingClientRect();
      result.qr.push({
        inline: Boolean(svg) && !img,
        colorMatches: Boolean(svg) && svgColor === qrStyle.borderTopColor && paints.every((paint) => paint === svgColor),
        link: link ? link.getAttribute('href') : null,
        linkText: address || null,
        value: qr.dataset.qr || svg?.dataset.qr || null,
        repeated: mentions > 1,
        rect: { x: box.left, y: box.top, width: box.width, height: box.height },
      });
    }

    if (number) {
      const style = getComputedStyle(number);
      result.service.number = [Math.round(bounds.right - numberRect.right), Math.round(bounds.bottom - numberRect.bottom), style.fontSize, style.fontFamily];
    }
    const title = slide.querySelector('.slide-title');
    if (title && !hiddenBy(title, slide)) {
      const rect = title.getBoundingClientRect();
      // A centered title (the tab over full-slide media) moves its left edge
      // with the text length, so it is compared by its center instead.
      const centered = Math.abs((rect.left + rect.right) / 2 - (bounds.left + bounds.right) / 2) < 2;
      const x = centered ? 'center' : Math.round(rect.left - bounds.left);
      result.service.title = [x, Math.round(rect.top - bounds.top), getComputedStyle(title).fontSize];
    }
    return result;
  }

  // Geometry of every element on the page in document order. Copies of one
  // source slide share the same structure, so the indexes match.
  function geometry() {
    const slide = active();
    const bounds = slide.getBoundingClientRect();
    return [...canvasOf(slide).querySelectorAll('*')].map((el) => {
      const rect = el.getBoundingClientRect();
      const frag = el.closest('.frag');
      return [
        Math.round(rect.left - bounds.left), Math.round(rect.top - bounds.top),
        Math.round(rect.width), Math.round(rect.height),
        frag ? Number(frag.dataset.fragStep) - 1 : -1,
        // data-shift="intended" marks a deliberate layout change between
        // steps, such as swapped text. Everything else must stay in place.
        rect.width > 0 && rect.height > 0 && !el.closest('svg, .slide-status, [data-shift="intended"]') ? describe(el).slice(0, 90) : '',
      ];
    });
  }

  function sourceChecks() {
    // Source checks on the final frame of every slide.
    return [...document.querySelectorAll('.slide')].filter((slide) => Number(slide.dataset.step) === Number(slide.dataset.steps)).map((slide) => {
      const frags = [...slide.querySelectorAll('.frag')];
      const media = [...slide.querySelectorAll('figure')].flatMap((figure) => {
        const caption = figure.querySelector(':scope > figcaption');
        const content = figure.querySelector('img, video, svg, .placeholder, pre, table');
        if (!caption || !content) return [];
        const stepOf = (element) => Number(element.closest('.frag')?.dataset.fragStep || 0);
        const captionStep = stepOf(caption);
        const contentStep = stepOf(content);
        return captionStep < contentStep ? [describe(caption)] : [];
      });
      return {
        page: Number(slide.dataset.index),
        key: slide.dataset.key,
        source: slide.dataset.source,
        generated: slide.hasAttribute('data-key-generated'),
        layout: slide.dataset.slideLayout || null,
        local: slide.dataset.composition === 'local',
        localReason: (slide.dataset.localReason || '').trim(),
        classes: slide.className,
        // data-frag="nested" marks a deliberate next step inside a revealed
        // block, such as tree branches. Accidental nesting is an error.
        nested: slide.querySelectorAll('.frag .frag:not([data-frag="nested"])').length,
        lonelyArrow: [...slide.querySelectorAll('.flow-step.frag')].filter((step) => !step.querySelector('.flow-node') || !step.querySelector('.flow-arrow')).length,
        captionFirst: media,
        number: Boolean(slide.querySelector('.slide-number')),
        bentoSteps: slide.querySelectorAll('.bento .frag, .bento.frag').length,
        posterless: [...slide.querySelectorAll('video')].filter((video) => !video.getAttribute('poster')).length,
        matches: (selectors) => selectors,
      };
    });
  }

  function signature(page, selectors) {
    const slide = document.querySelector('.slide[data-index="' + page + '"]');
    return selectors.filter((selector) => !(slide.matches(selector) || slide.querySelector(selector)));
  }

  // In the motion pass CSS animations and the page clock both run rate
  // times faster, so animation time and performance.now() stay in step and
  // the wait is counted on the page clock. rate only scales the short tail.
  async function sample(limit, rate = 1) {
    const slide = active();
    const page = slide.dataset.index;
    const panel = document.querySelector('.help-panel:not([hidden])');
    const controls = panel ? [...panel.querySelectorAll('button, label')].filter((el) => el.getBoundingClientRect().width > 0) : [];
    const counters = [...slide.querySelectorAll('[data-count]')].filter((el) => !inUnshownFrag(el));
    const animations = () => document.getAnimations().filter((animation) => slide.contains(animation.effect?.target));
    let end = 0;
    for (const animation of animations()) {
      const timing = animation.effect.getComputedTiming();
      if (Number.isFinite(timing.endTime)) end = Math.max(end, timing.endTime);
    }
    for (const counter of counters) end = Math.max(end, Number(counter.dataset.countDuration) || 900);
    const animated = animations().length > 0 || counters.length > 0;
    const started = performance.now();
    const record = { animated, end: Math.round(end), counters: counters.map(() => ({ height: 0, width: 0 })), covered: [], left: false };
    // A page without motion needs no watching; a moving one gets a short tail.
    const deadline = animated ? Math.min(limit, end + 60 * rate) : 0;
    // Under load one slow frame can outlast the tail, so a moving page also
    // waits a few frames past the deadline for end-of-animation handlers.
    let framesAfter = animated ? 3 : 0;
    while (performance.now() - started < deadline || framesAfter-- > 0) {
      counters.forEach((counter, i) => {
        const rect = counter.getBoundingClientRect();
        record.counters[i].height = Math.max(record.counters[i].height, rect.height);
        record.counters[i].width = Math.max(record.counters[i].width, rect.width);
      });
      for (const control of controls) {
        const rect = control.getBoundingClientRect();
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        if (!control.contains(hit) && !record.covered.includes(describe(control))) record.covered.push(describe(control));
      }
      if (active()?.dataset.index !== page) record.left = true;
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    await settle();
    record.final = counters.map((counter) => {
      const rect = counter.getBoundingClientRect();
      const lineHeight = Number.parseFloat(getComputedStyle(counter).lineHeight) || Number.parseFloat(getComputedStyle(counter).fontSize) * 1.2;
      return { height: rect.height, width: rect.width, lines: Math.round(rect.height / lineHeight), text: counter.textContent, label: counter.getAttribute('aria-label'), describe: describe(counter) };
    });
    record.unfinished = animations().filter((animation) => {
      const timing = animation.effect.getComputedTiming();
      return Number.isFinite(timing.endTime) && animation.playState === 'running';
    }).map((animation) => describe(animation.effect.target));
    record.stillActive = active()?.dataset.index === page;
    return record;
  }

  function panelHits() {
    const panel = document.querySelector('.help-panel');
    if (!panel || panel.hidden) return { missing: true };
    const issues = [];
    for (const control of panel.querySelectorAll('button, label')) {
      const rect = control.getBoundingClientRect();
      if (!rect.width || getComputedStyle(control).display === 'none') continue;
      if (rect.left < 0 || rect.top < 0 || rect.right > innerWidth || rect.bottom > innerHeight) {
        issues.push(describe(control) + ' is off screen');
        continue;
      }
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      if (!control.contains(hit)) issues.push(describe(control) + ' is covered by: ' + describe(hit));
    }
    return { issues };
  }

  window.__probe = { active, settle, inspect, geometry, sourceChecks, signature, sample, panelHits, describe };
  return true;
})()`;

let page;
let visit = 0;
async function open(query, hash = '1', size = [1280, 720]) {
  await page.viewport(...size);
  // A unique parameter makes the browser load the document again instead
  // of following an anchor inside the deck that is already open.
  visit += 1;
  await page.navigate(`${base}?${query}&probe=${visit}#${hash}`, "document.readyState === 'complete' && Boolean(window.craftDeck)");
  await page.evaluate(PAGE_LIB);
}
const go = (n) => page.evaluate(`(async () => { craftDeck.go(${n}); await __probe.settle(); return craftDeck.current; })()`);
const where = (n) => report.pages[n - 1] || { page: n };

async function countPdfPages(data) {
  const directory = await mkdtemp(path.join(tmpdir(), 'craft-pdf-'));
  const file = path.join(directory, 'deck.pdf');
  await writeFile(file, data);
  try {
    const info = execFileSync('pdfinfo', [file], { encoding: 'utf8' });
    return Number(info.match(/^Pages:\s+(\d+)/m)?.[1]);
  } catch {
    return (data.toString('latin1').match(/\/Type\s*\/Page(?![s\w])/g) || []).length;
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

let zbar = true;
// Returns the decoded value, '' if the code does not scan, null if there
// is no scanner. In the dark theme the modules are lighter than the
// background. Phone cameras read such an inverted code but zbar does not,
// so we read the frame a second time inverted and report that separately.
async function decodeQr(rect, inverted = false) {
  if (!zbar) return null;
  if (inverted) await page.evaluate("document.documentElement.style.filter = 'invert(1)'");
  const shot = await page.send('Page.captureScreenshot', {
    format: 'png',
    clip: { x: rect.x - 8, y: rect.y - 8, width: rect.width + 16, height: rect.height + 16, scale: 4 },
  });
  const directory = await mkdtemp(path.join(tmpdir(), 'craft-qr-'));
  const file = path.join(directory, 'qr.png');
  await writeFile(file, Buffer.from(shot.data, 'base64'));
  try {
    return execFileSync('zbarimg', ['--raw', '-q', file], { encoding: 'utf8' }).trim();
  } catch (failure) {
    if (failure.code === 'ENOENT') {
      zbar = false;
      warn('qr', null, 'zbarimg not found: QR scanning was not checked');
      return null;
    }
    return '';
  } finally {
    if (inverted) await page.evaluate("document.documentElement.style.filter = ''");
    await rm(directory, { recursive: true, force: true });
  }
}

async function readQr(rect, at, theme) {
  let decoded = await decodeQr(rect);
  if (decoded === '') {
    decoded = await decodeQr(rect, true);
    if (decoded) warn('qr', at, `in the ${theme} theme the QR is inverted: phone cameras usually read such a code, test it on your phone`);
  }
  if (decoded === '') error('qr', at, `the scanner cannot read the QR in the ${theme} theme`);
  return decoded;
}

// Runs a pass when it is selected and records how long it took.
async function pass(name, body) {
  if (!passes.has(name)) return;
  const begun = Date.now();
  await body();
  report.timings[name] = Date.now() - begun;
}

const normalize = (value) => (value || '').trim().replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');

try {
  page = await launch();
  const started = Date.now();
  const requests = [];
  const exceptions = [];
  await page.send('Network.enable');
  page.on('Network.requestWillBeSent', ({ request }) => requests.push(request.url));
  page.on('Runtime.exceptionThrown', ({ exceptionDetails }) => exceptions.push(exceptionDetails.exception?.description || exceptionDetails.text));

  // ---------- viewports: three widths at once, theme, accessibility ----------
  await pass('viewports', async () => {
    report.viewports = await probeViewports(page, index, 'slides', viewportList);
  });

  // ---------- static pass: every state in its final frame ----------
  await open('reveal=steps&motion=static&theme=dark');
  report.pages = await page.evaluate('craftDeck.pages()');
  const total = report.pages.length;
  if (!total) throw Error('the deck created no pages');

  const sources = await page.evaluate('__probe.sourceChecks().map(({ matches, ...rest }) => rest)');
  report.sources = sources.length;
  const keyOwners = new Map();
  for (const source of sources) {
    const at = where(source.page);
    if (source.generated) error('key', at, 'source slide has no data-key: add a stable key, page numbers change when slides move');
    if (keyOwners.has(source.key) && keyOwners.get(source.key) !== source.source) error('key', at, `key ${source.key} is used by more than one slide`);
    keyOwners.set(source.key, source.source);
    if (!source.number) error('service', at, 'no service .slide-number: the mechanics fill in the number');
    if (source.nested) error('reveal', at, 'a nested .frag creates an extra step');
    if (source.bentoSteps) error('reveal', at, 'bento shows as one page: tiles appear in sequence on entry, without .frag');
    if (source.posterless) error('video', at, 'video has no poster: without autoplay and in PDF the viewer sees an empty frame');
    if (source.lonelyArrow) error('reveal', at, 'a .flow-step link is revealed without its node: the arrow and the node appear together');
    for (const caption of source.captionFirst) error('reveal', at, `caption appears before its content: ${caption}`);
    if (!source.layout) {
      error('layout', at, 'no data-slide-layout');
    } else if (!knownLayouts.includes(source.layout)) {
      error('layout', at, `unknown layout ${source.layout}; available: ${knownLayouts.join(', ')}`);
    } else if (source.local) {
      if (!source.localReason) error('layout', at, 'local composition without data-local-reason: explain why no ready layout fits');
    } else {
      const missing = await page.evaluate(`__probe.signature(${source.page}, ${JSON.stringify(signatures[source.layout])})`);
      if (missing.length) {
        error('layout', at, `layout ${source.layout} is declared but ${missing.join(', ')} is missing: build the slide with compose.py or mark it data-composition="local" with data-local-reason`);
      }
    }
  }

  await pass('frames', async () => {
    const service = { number: new Map(), title: new Map() };
    let previousGeometry = null;
    if (shots) await mkdir(shots, { recursive: true });
    for (let n = 1; n <= total; n += 1) {
      await go(n);
      const at = where(n);
      const result = await page.evaluate('__probe.inspect({ invisible: true })');
      result.clip.forEach((item) => error('clip', at, `text clipped by container: ${item}`));
      result.overflow.forEach((item) => error('overflow', at, `text runs off the slide: ${item}`));
      result.number.forEach((item) => error('service', at, `text runs into the slide number: ${item}`));
      result.overlap.forEach((item) => error('overlap', at, `texts overlap: ${item}`));
      if (result.frag.length) error('reveal', at, `reveals ${result.frag.join(', ')} do not match step ${at.step}`);
      if (result.bentoRows) error('layout', at, 'bento tiles in one row have different heights');
      result.invisible.forEach((item) => error('static', at, `content is invisible in the static frame: ${item}. An animation must set only the starting frame (from), not the final state`));
      for (const image of result.images) {
        report.images.push({ page: n, key: at.key, ...image });
        if (image.broken) error('image', at, `image failed to load: ${image.src}`);
        if (image.clipped) error('image', at, `image clipped by container ${image.clipped}: if this is a crop, add data-crop or use media-cover`);
        if (image.outside) error('image', at, `image runs off the slide: ${image.src}`);
        if (image.frameGap > 0.04) error('image', at, `frame is wider than image ${image.src}: fit the .frame proportions or use media-cover`);
        if (image.natural[0] && !/\.svg(\?|$)/i.test(image.src) && image.natural[0] < image.at1920[0] * 0.8) warn('image', at, `image ${image.src} is smaller than its space on a 1920 px screen: ${image.natural[0]} px instead of ${image.at1920[0]}`);
      }
      for (const qr of result.qr) {
        if (!qr.inline) error('qr', at, 'the QR inside .qr must be an inline svg with currentColor');
        else if (!qr.colorMatches) error('qr', at, 'QR modules do not match the border color: paint them with currentColor');
        if (!qr.link) error('qr', at, 'no visible clickable link next to the QR in the same .qr-link');
        if (qr.repeated) error('qr', at, `address ${qr.linkText} appears on the slide more than once`);
        const expected = normalize(qr.value || qr.link);
        if (qr.value && qr.link && normalize(qr.value) !== normalize(qr.link)) error('qr', at, `QR encodes ${qr.value} but the link points to ${qr.link}`);
        const decoded = await readQr(qr.rect, at, 'dark');
        if (decoded && expected && normalize(decoded) !== expected) error('qr', at, `QR reads as ${decoded}, expected ${expected}`);
      }
      if (result.service.number) {
        const signature = `${at.layout}|${result.service.number.join('|')}`;
        service.number.set(signature, [...(service.number.get(signature) || []), n]);
      }
      if (result.service.title && !sources.find((source) => source.key === at.key)?.local) {
        const signature = `${at.layout}|${result.service.title.join('|')}`;
        service.title.set(signature, [...(service.title.get(signature) || []), n]);
      }

      const geometry = await page.evaluate('__probe.geometry()');
      const previous = report.pages[n - 2];
      if (previousGeometry && previous && previous.key === at.key && previous.step + 1 === at.step && previousGeometry.length === geometry.length) {
        // The new reveal and parts still hidden may take their own place.
        // Whatever is already shown stays where it was.
        const revealed = at.step - 1;
        const moved = geometry.filter((item, i) => {
          const before = previousGeometry[i];
          if (!item[5] || (item[4] !== -1 && item[4] >= revealed)) return false;
          return Math.abs(item[0] - before[0]) > 1 || Math.abs(item[1] - before[1]) > 1 || Math.abs(item[2] - before[2]) > 1;
        });
        if (moved.length) error('shift', at, `reveal shifts content already shown: ${moved.slice(0, 3).map((item) => item[5]).join('; ')}`);
      }
      previousGeometry = geometry;
      if (shots) {
        const shot = await page.send('Page.captureScreenshot', { format: 'png' });
        await writeFile(path.join(shots, `dark-${String(n).padStart(3, '0')}.png`), Buffer.from(shot.data, 'base64'));
      }
    }

    // Service elements match on every page. Titles match within one layout.
    for (const [name, map] of [['slide number', service.number], ['title', service.title]]) {
      const byLayout = new Map();
      for (const [signature, pages] of map) {
        // A centered title is a declared variant of its layout (the tab over
        // full-slide media), so it is compared with other centered titles.
        const [kind, x] = signature.split('|');
        const layout = x === 'center' ? `${kind} (centered title)` : kind;
        byLayout.set(layout, [...(byLayout.get(layout) || []), pages]);
      }
      for (const [layout, groups] of byLayout) {
        if (groups.length < 2) continue;
        groups.sort((a, b) => b.length - a.length).slice(1).forEach((pages) => error('service', where(pages[0]), `${name} in layout ${layout} sits differently than on other pages of this layout (pages ${pages.slice(0, 6).join(', ')}): do not move service elements locally`));
      }
    }
  });

  // ---------- light theme and phone ----------
  await pass('light', async () => {
    await page.evaluate("document.documentElement.dataset.theme = 'light'");
    for (let n = 1; n <= total; n += 1) {
      const has = await page.evaluate(`(async () => { craftDeck.go(${n}); await __probe.settle(); return Boolean(__probe.active().querySelector('.qr')); })()`);
      if (!has) continue;
      const result = await page.evaluate('__probe.inspect()');
      for (const qr of result.qr) {
        if (qr.inline && !qr.colorMatches) error('qr', where(n), 'in the light theme QR modules do not match the border color');
        await readQr(qr.rect, where(n), 'light');
      }
    }
  });

  await pass('phone', async () => {
    await open('reveal=steps&motion=static&theme=dark', '1', [390, 844]);
    await page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'h' }))");
    for (let n = 1; n <= total; n += 1) {
      await go(n);
      const at = where(n);
      const result = await page.evaluate('__probe.inspect()');
      result.clip.forEach((item) => error('clip', at, `on phone, text clipped by container: ${item}`));
      result.overflow.forEach((item) => error('overflow', at, `on phone, text runs off the slide: ${item}`));
      const hits = await page.evaluate('__probe.panelHits()');
      (hits.issues || []).forEach((item) => error('panel', at, `at 390 px a panel button is unreachable: ${item}`));
    }
  });

  // ---------- panel on reference screens and the keyboard after it ----------
  await pass('panel', async () => {
    for (const [width, height] of [[1440, 900], [390, 844], [320, 720], [844, 390]]) {
      await open('reveal=steps&motion=static&theme=dark', '1', [width, height]);
      await page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'h' }))");
      await sleep(50);
      const hits = await page.evaluate('__probe.panelHits()');
      if (hits.missing) {
        error('panel', null, `at ${width}×${height} the H key does not open the control panel`);
        continue;
      }
      hits.issues.forEach((item) => error('panel', null, `at ${width}×${height} a panel button is unreachable: ${item}`));
      const target = await page.evaluate(`(() => {
        const button = document.querySelector('.help-panel [data-deck-go="1"]');
        const rect = button?.getBoundingClientRect();
        return rect && rect.width ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
      })()`);
      if (target && total > 2) {
        await page.click(target.x, target.y);
        await sleep(50);
        await page.key('ArrowRight', 'ArrowRight', 39);
        await sleep(50);
        const current = await page.evaluate('craftDeck.current');
        if (current !== 3) error('keyboard', null, `at ${width}×${height} arrow keys stop paging after a panel button click (page ${current} instead of 3)`);
      }
    }
  });

  // ---------- motion: step forward onto every page ----------
  await pass('motion', async () => {
    await open('reveal=steps&motion=show&theme=dark');
    await page.send('Animation.enable');
    await page.send('Animation.setPlaybackRate', { playbackRate: MOTION_RATE });
    // Counters and other script motion read performance.now() and the frame
    // timestamp. Both speed up together with CSS.
    await page.evaluate(`(() => {
      const realNow = performance.now.bind(performance);
      const origin = realNow();
      const scaled = () => origin + (realNow() - origin) * ${MOTION_RATE};
      performance.now = scaled;
      const frame = window.requestAnimationFrame.bind(window);
      window.requestAnimationFrame = (callback) => frame(() => callback(scaled()));
      return true;
    })()`);
    await page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'h' }))");
    for (let n = 2; n <= total; n += 1) {
      const at = where(n);
      await go(n - 1);
      // Paging and the start of sampling run in one task, so a sped-up
      // animation cannot end and page the deck before the probe is watching.
      const record = await page.evaluate(`(() => { craftDeck.go(${n}); return __probe.sample(12000, ${MOTION_RATE}); })()`, 30000);
      if (!record.animated) continue;
      if (!record.stillActive || record.left) error('motion', at, 'animation switched the page: motion inside a page must not page the deck');
      record.covered.forEach((item) => error('panel', at, `content covers the panel during animation: ${item}`));
      if (record.unfinished.length) warn('motion', at, `animation did not finish within 12 s: ${record.unfinished.slice(0, 2).join('; ')}`);
      record.final.forEach((counter, i) => {
        const peak = record.counters[i];
        if (peak.height > counter.height + 1) error('counter', at, `counter wraps an intermediate value: ${counter.describe}`);
        if (counter.lines > 1) error('counter', at, `counter number takes ${counter.lines} lines: ${counter.describe}`);
        if (peak.width > counter.width + 1) error('counter', at, `counter is wider than its final value: ${counter.describe}`);
        if (counter.label && counter.text.trim() !== counter.label.trim()) error('counter', at, `counter did not reach its final value: ${counter.text} instead of ${counter.label}`);
      });
      const final = await page.evaluate('__probe.inspect({ invisible: true })');
      final.invisible.forEach((item) => error('motion', at, `content stayed invisible after animation: ${item}`));
    }

    // Fast paging leaves no leftovers from previous pages.
    await go(1);
    for (let i = 0; i < Math.min(8, total - 1); i += 1) { await page.key('ArrowRight', 'ArrowRight', 39); await sleep(15); }
    for (let i = 0; i < Math.min(8, total - 1); i += 1) { await page.key('ArrowLeft', 'ArrowLeft', 37); await sleep(15); }
    await sleep(250);
    const tails = await page.evaluate(`(() => ({
      active: document.querySelectorAll('.slide[data-active]').length,
      reveal: [...document.querySelectorAll('[data-reveal]')].filter((el) => !el.closest('.slide[data-active]')).length,
      counters: [...document.querySelectorAll('.slide:not([data-active]) [data-count][aria-label]')].filter((el) => el.textContent.trim() !== el.getAttribute('aria-label').trim()).length,
      videos: [...document.querySelectorAll('.slide:not([data-active]) video')].filter((video) => !video.paused).length,
    }))()`);
    if (tails.active !== 1) error('navigation', null, 'after fast paging more or less than one page is active');
    if (tails.reveal) error('navigation', null, 'after fast paging the data-reveal mark stayed on a hidden page');
    if (tails.counters) error('counter', null, 'after fast paging a counter on a hidden page stayed at an intermediate value');
    if (tails.videos) error('video', null, 'after fast paging a video on a hidden page is playing');
    await page.send('Animation.setPlaybackRate', { playbackRate: 1 });
  });

  // ---------- deep link to the middle and back ----------
  await pass('navigation', async () => {
    const middle = report.pages.find((item) => item.step > 0 && item.step < item.steps);
    if (middle) {
      await open('reveal=steps&motion=show&theme=dark', `${encodeURIComponent(middle.key)}/${middle.step}`);
      await page.send('Page.reload');
      await sleep(300);
      await page.evaluate("document.fonts.ready.then(() => Boolean(window.craftDeck))");
      await page.evaluate(PAGE_LIB);
      const state = await page.evaluate(`({ current: craftDeck.current, shown: __probe.active().querySelectorAll('.frag[data-shown]').length })`);
      if (state.current !== middle.page || state.shown !== middle.step) error('navigation', middle, `deep link #${middle.key}/${middle.step} opened page ${state.current} with ${state.shown} reveals after reload`);
      const states = report.pages.filter((item) => item.key === middle.key);
      await go(states[0].page);
      for (const item of states.slice(1)) {
        await page.key('ArrowRight', 'ArrowRight', 39);
        await sleep(30);
        if (await page.evaluate('craftDeck.current') !== item.page) error('navigation', item, 'the forward arrow does not land on the next reveal');
      }
      for (const item of states.slice(0, -1).reverse()) {
        await page.key('ArrowLeft', 'ArrowLeft', 37);
        await sleep(30);
        if (await page.evaluate('craftDeck.current') !== item.page) error('navigation', item, 'the back arrow does not return to the previous reveal');
      }
    }
  });

  // ---------- video ----------
  await pass('video', async () => {
    await open('reveal=steps&motion=show&theme=dark');
    const media = await page.evaluate('window.craftMedia ? craftMedia.state() : null');
    const hasVideo = await page.evaluate("document.querySelectorAll('.slide video').length");
    if (hasVideo && !media) error('video', null, 'the deck has video but media.js is not loaded after deck.js');
    if (media && media.length) {
      const videoPages = [...new Set(media.map((item) => item.page))];
      const identities = new Map(media.map((item) => [item.page + '|' + item.identity, item]));
      for (const n of videoPages) {
        const at = where(n);
        if (n > 1) await go(n - 1);
        await go(n);
        await sleep(700);
        const first = await page.evaluate('craftMedia.state()');
        await sleep(700);
        const second = await page.evaluate('craftMedia.state()');
        const errorsOnPage = await page.evaluate(`[...__probe.active().querySelectorAll('video')].map((video) => video.error ? video.error.code : 0)`);
        second.forEach((item, i) => {
          if (!item.active && !item.paused) error('video', where(item.page), 'video on a hidden page is playing');
          if (!item.active || item.role === 'manual') return;
          if (item.expectedRate !== item.playbackRate) error('video', at, `video speed is ${item.playbackRate} instead of ${item.expectedRate}`);
          // A loop may restart between two samples.
          let moved = item.currentTime - first[i].currentTime;
          if (moved < 0 && item.loop && item.duration) moved += item.duration;
          if (item.paused || moved < 0.2) {
            if (errorsOnPage.includes(4)) warn('video', at, 'the probe browser cannot decode this video format: check the clip by hand and in the target browser');
            else if (item.readyState === 0) error('video', at, 'video failed to load');
            else error('video', at, `video on the open page is not playing: time moved by ${moved.toFixed(2)} s`);
          }
        });
        // A hidden tab pauses video, coming back starts it again.
        await page.evaluate("Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange'))");
        await sleep(120);
        if ((await page.evaluate('craftMedia.state()')).some((item) => !item.paused)) error('video', at, 'video plays while the tab is hidden');
        await page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))");
        await sleep(600);
        const back = await page.evaluate('craftMedia.state()');
        if (back.some((item) => item.active && item.role !== 'manual' && item.paused && item.readyState > 0 && !errorsOnPage.includes(4))) error('video', at, 'video did not resume after returning to the tab');
        // A shared scene and copies of one slide keep the playback position.
        const next = report.pages[n];
        if (next) {
          const current = back.filter((item) => item.active && item.role !== 'manual' && item.currentTime > 0.5);
          const continued = current.filter((item) => identities.has(`${n + 1}|${item.identity}`));
          if (continued.length) {
            await go(n + 1);
            await sleep(150);
            const after = await page.evaluate('craftMedia.state()');
            for (const item of continued) {
              const successor = after.find((candidate) => candidate.page === n + 1 && candidate.identity === item.identity);
              if (successor && successor.currentTime + 0.3 < item.currentTime) error('video', where(n + 1), 'clip restarted instead of continuing the shared scene');
            }
          }
        }
      }
      const loaded = (await page.evaluate('craftMedia.state()')).filter((item) => item.readyState >= 2 && !item.released);
      const limit = await page.evaluate('craftMedia.radius.release');
      const current = await page.evaluate('craftDeck.current');
      const far = loaded.filter((item) => Math.abs(item.page - current) > limit);
      if (far.length) warn('video', null, `${far.length} distant clips stayed loaded after the pass`);

      await open('reveal=steps&motion=static&theme=dark', String(videoPages[0]));
      await sleep(300);
      if ((await page.evaluate('craftMedia.state()')).some((item) => !item.paused)) error('video', where(videoPages[0]), 'video plays in static mode');
    }
  });

  // ---------- print ----------
  await pass('print', async () => {
    await open('reveal=steps&motion=static&theme=dark');
    const steps = await page.send('Page.printToPDF', { printBackground: true, preferCSSPageSize: true }, 180000);
    report.pdf.steps = await countPdfPages(Buffer.from(steps.data, 'base64'));
    if (report.pdf.steps !== total) error('print', null, `PDF with all reveals has ${report.pdf.steps} pages instead of ${total}`);
    await open('reveal=final&motion=static&theme=dark');
    const finalPages = await page.evaluate('craftDeck.total');
    const final = await page.send('Page.printToPDF', { printBackground: true, preferCSSPageSize: true }, 180000);
    report.pdf.final = await countPdfPages(Buffer.from(final.data, 'base64'));
    if (finalPages !== report.sources) error('reveal', null, `final mode produced ${finalPages} pages for ${report.sources} slides`);
    if (report.pdf.final !== report.sources) error('print', null, `PDF of final frames has ${report.pdf.final} pages instead of ${report.sources}`);
  });

  // ---------- network and errors ----------
  for (const url of new Set(requests)) {
    if (!/^https?:/.test(url)) continue;
    const host = new URL(url).hostname;
    if (!webDelivery || !allowedHosts.has(host)) error('network', null, `the deck makes a network request: ${url}`);
  }
  [...new Set(exceptions)].forEach((item) => error('javascript', null, `JavaScript error: ${item.split('\n')[0]}`));
  report.timings.total = Date.now() - started;
} catch (failure) {
  error('probe', null, `probe did not run: ${failure.message}`);
} finally {
  await page?.close();
}

process.stdout.write(JSON.stringify(report, null, 2) + '\n');
