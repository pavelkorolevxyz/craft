#!/usr/bin/env node
// One Chromium for a whole test run. Reads JSON requests line by line on
// stdin and answers each with one JSON line on stdout:
//
//   {"op": "dump", "url": "file:///…", "width": 1440, "height": 900, "title": "original title"}
//     → {"html": "<html>…"} once the page has set a new document.title (or after 5 s)
//   {"op": "pdf", "url": "file:///…", "width": 1280, "height": 720, "path": "/tmp/out.pdf"}
//     → {"bytes": 12345}
//   {"op": "shot", "url": "file:///…", "width": 1440, "height": 900, "path": "/tmp/out.png"}
//     → {"bytes": 12345} once fonts, images and two frames have settled
//
// It replaces a cold `chromium --dump-dom` or `--print-to-pdf` start per call.
import { writeFile } from 'node:fs/promises';
import { createInterface } from 'node:readline';
import { launch, sleep } from './cdp.mjs';

const page = await launch();
let visit = 0;

async function open(url, width, height) {
  await page.viewport(width, height);
  visit += 1;
  // A unique query makes the browser load the file again.
  const [address, anchor] = url.split('#');
  const fresh = `${address}${address.includes('?') ? '&' : '?'}session=${visit}${anchor !== undefined ? `#${anchor}` : ''}`;
  await page.navigate(fresh);
}

async function handle(request) {
  if (request.op === 'dump') {
    await open(request.url, request.width, request.height);
    const original = JSON.stringify(request.title ?? '');
    for (let attempt = 0; attempt < 200; attempt += 1) {
      if (await page.evaluate(`document.title !== ${original}`)) break;
      await sleep(25);
    }
    return { html: await page.evaluate('document.documentElement.outerHTML') };
  }
  if (request.op === 'pdf') {
    await open(request.url, request.width, request.height);
    const pdf = await page.send('Page.printToPDF', {}, 180000);
    const data = Buffer.from(pdf.data, 'base64');
    await writeFile(request.path, data);
    return { bytes: data.length };
  }
  if (request.op === 'shot') {
    await open(request.url, request.width, request.height);
    await page.evaluate(`Promise.all([...document.images].map((image) => image.decode().catch(() => null)))
      .then(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 150)))))
      .then(() => true)`);
    const shot = await page.send('Page.captureScreenshot', { format: 'png' });
    const data = Buffer.from(shot.data, 'base64');
    await writeFile(request.path, data);
    return { bytes: data.length };
  }
  throw Error(`unknown op ${request.op}`);
}

const lines = createInterface({ input: process.stdin });
for await (const line of lines) {
  if (!line.trim()) continue;
  try {
    process.stdout.write(JSON.stringify(await handle(JSON.parse(line))) + '\n');
  } catch (failure) {
    process.stdout.write(JSON.stringify({ error: failure.message }) + '\n');
  }
}
await page.close();
