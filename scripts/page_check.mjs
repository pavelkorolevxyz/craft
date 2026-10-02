#!/usr/bin/env node
// Browser check of standalone Craft pages in one Chromium session.
//
//   node scripts/page_check.mjs page/index.html [more/index.html] [--surface interface|slides] [--viewports 1440x900,390x844] [--pdf]
//
// For each page it loads the three test viewports at once in iframes, runs
// page_probe.js in each (layout, theme, accessibility and visual checks),
// and with --pdf prints the page to measure the PDF. Prints a JSON array:
// [{ index, viewports: [...], pdfBytes }]. deck_probe.mjs reuses
// probeViewports for its own viewports pass.
import { readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './cdp.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
export const VIEWPORTS = [[1440, 900], [390, 844], [320, 720]];

function harness(probe, name, surface, viewports) {
  const initialized = surface === 'interface'
    ? "const toggle=document.querySelector('[data-theme-toggle]');return !toggle||Boolean(toggle.getAttribute('aria-label'));"
    : "return document.querySelectorAll('.slide[data-active]').length===1;";
  return `<!doctype html>
<html><head><meta charset="utf-8"><title>craft-check:pending</title>
<style>iframe { position: absolute; inset: 0 auto auto 0; border: 0; }</style></head>
<body><script>
${probe}
const frames = ${JSON.stringify(viewports)}.map(([width, height]) => {
  const frame = document.createElement('iframe');
  frame.width = width;
  frame.height = height;
  frame.src = ${JSON.stringify(encodeURIComponent(name))};
  document.body.append(frame);
  return frame;
});
const inspectWhenReady = () => {
  const loaded = frames.every(frame => {
    const document = frame.contentDocument;
    if (!document || frame.contentWindow.location.href === 'about:blank' || document.readyState !== 'complete') return false;
    ${initialized}
  });
  if (!loaded) { setTimeout(inspectWhenReady, 10); return; }
  Promise.all(frames.map(frame => frame.contentDocument.fonts.ready)).then(() => {
    window.craftCheck = frames.map(frame => craftProbe(frame, ${JSON.stringify(surface)}));
  });
};
inspectWhenReady();
</script></body></html>`;
}

// Loads the page in every viewport at once and returns the page_probe results.
export async function probeViewports(page, index, surface, viewports = VIEWPORTS) {
  const probe = await readFile(path.join(here, 'page_probe.js'), 'utf8');
  const file = path.join(path.dirname(index), '__craft_check__.html');
  await writeFile(file, harness(probe, path.basename(index), surface, viewports));
  try {
    await page.viewport(1500, 1000);
    await page.navigate(`${pathToFileURL(file).href}?visit=${Date.now()}`);
    // A slow runner may need a while for three iframes of a long page.
    for (let attempt = 0; attempt < 2400; attempt += 1) {
      const results = await page.evaluate('window.craftCheck || null');
      if (results) return results;
      await sleep(25);
    }
    throw Error('the page check did not finish in 60 s');
  } finally {
    await rm(file, { force: true });
  }
}

export async function printBytes(page, index) {
  await page.viewport(1280, 720);
  await page.navigate(`${pathToFileURL(index).href}?print=${Date.now()}`);
  const pdf = await page.send('Page.printToPDF', { printBackground: true }, 120000);
  return Buffer.from(pdf.data, 'base64').length;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const option = (name) => {
    const at = args.indexOf(name);
    return at >= 0 ? args[at + 1] : null;
  };
  const surface = option('--surface') || 'interface';
  const viewports = option('--viewports') ? option('--viewports').split(',').map((item) => item.split('x').map(Number)) : VIEWPORTS;
  const valued = new Set(['--surface', '--viewports']);
  const indexes = args.filter((value, position) => !value.startsWith('--') && !valued.has(args[position - 1])).map((value) => path.resolve(value));
  const page = await launch();
  const output = [];
  try {
    for (const index of indexes) {
      const viewportsResult = await probeViewports(page, index, surface, viewports);
      const pdfBytes = args.includes('--pdf') ? await printBytes(page, index) : null;
      output.push({ index, viewports: viewportsResult, pdfBytes });
    }
  } finally {
    await page.close();
  }
  process.stdout.write(JSON.stringify(output) + '\n');
}
