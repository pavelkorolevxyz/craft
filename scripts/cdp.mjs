// Minimal Chrome DevTools Protocol client with no npm packages.
// Needs Node.js with built-in WebSocket (22+) and Chromium.
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { existsSync } from 'node:fs';

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function findChromium() {
  if (process.env.CHROMIUM) return process.env.CHROMIUM;
  const dirs = (process.env.PATH || '').split(path.delimiter);
  for (const name of ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']) {
    for (const dir of dirs) {
      const candidate = path.join(dir, name);
      if (existsSync(candidate)) return candidate;
    }
  }
  throw Error('Chromium is required. If it is not on PATH, set CHROMIUM=/path/to/browser.');
}

export async function launch({ width = 1280, height = 720 } = {}) {
  const profile = await mkdtemp(path.join(tmpdir(), 'craft-cdp-'));
  const browser = spawn(findChromium(), [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    '--hide-scrollbars', '--mute-audio', '--autoplay-policy=no-user-gesture-required',
    '--allow-file-access-from-files', '--no-first-run', '--no-default-browser-check',
    `--window-size=${width},${height}`,
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: 'ignore' });

  let port;
  for (let attempt = 0; attempt < 200 && !port; attempt += 1) {
    try {
      port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]);
    } catch {
      await sleep(50);
    }
  }
  if (!port) {
    browser.kill('SIGKILL');
    throw Error('Chromium did not open the debugging port');
  }
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const socket = new WebSocket(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });

  let nextId = 0;
  const waiting = new Map();
  const listeners = new Map();
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const pending = waiting.get(message.id);
      if (!pending) return;
      clearTimeout(pending.timer);
      waiting.delete(message.id);
      if (message.error) pending.reject(Error(`${pending.method}: ${JSON.stringify(message.error)}`));
      else pending.resolve(message.result);
    } else if (message.method) {
      (listeners.get(message.method) || []).forEach((listener) => listener(message.params));
    }
  };

  const send = (method, params = {}, timeout = 60000) => new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { waiting.delete(id); reject(Error(`Timeout ${method}`)); }, timeout);
    waiting.set(id, { resolve, reject, timer, method });
    socket.send(JSON.stringify({ id, method, params }));
  });

  const on = (method, listener) => {
    if (!listeners.has(method)) listeners.set(method, []);
    listeners.get(method).push(listener);
  };

  const evaluate = async (expression, timeout) => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, timeout);
    if (result.exceptionDetails) {
      const detail = result.exceptionDetails.exception?.description || result.exceptionDetails.text;
      throw Error(`Error in page: ${detail}`);
    }
    return result.result.value;
  };

  const viewport = (width, height, mobile = false) => send('Emulation.setDeviceMetricsOverride', {
    width, height, deviceScaleFactor: 1, mobile,
  });

  const navigate = async (url, ready = "document.readyState === 'complete'") => {
    await send('Page.navigate', { url });
    for (let attempt = 0; attempt < 200; attempt += 1) {
      try {
        // The page may rewrite its own anchor, so only the part before # must match.
        if (await evaluate(`location.href.split('#')[0] === ${JSON.stringify(url.split('#')[0])} && (${ready})`)) break;
      } catch {
        // The document is still changing.
      }
      await sleep(25);
    }
    await evaluate('document.fonts.ready.then(() => true)');
  };

  const key = async (name, code, keyCode) => {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code, windowsVirtualKeyCode: keyCode });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code, windowsVirtualKeyCode: keyCode });
  };

  const click = async (x, y) => {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  };

  const close = async () => {
    try { socket.close(); } catch { /* already closed */ }
    browser.kill('SIGTERM');
    // The fallback timer is cleared on exit, or it would keep Node alive for 3 s.
    await new Promise((resolve) => {
      const fallback = setTimeout(resolve, 3000);
      browser.once('exit', () => { clearTimeout(fallback); resolve(); });
    });
    await rm(profile, { recursive: true, force: true, maxRetries: 3 });
  };

  await send('Page.enable');
  await send('Runtime.enable');
  return { send, on, evaluate, viewport, navigate, key, click, close };
}
