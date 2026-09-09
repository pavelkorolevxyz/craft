// Независимая проверка результатов агентов через Chromium, без пакетов npm.
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const directory = path.resolve(process.argv[2]);
const evidence = path.join(directory, 'review');
await mkdir(evidence, { recursive: true });
const profile = await mkdtemp(path.join(tmpdir(), 'craft-browser-eval-'));
const browser = spawn(process.env.CHROMIUM || 'chromium', [
  '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
], { stdio: 'ignore' });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
try {
  let port;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { port = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break; }
    catch { await sleep(100); }
  }
  if (!port) throw Error('Chromium не открыл порт');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let nextId = 0;
  const waiting = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    const pending = waiting.get(message.id);
    if (pending) {
      clearTimeout(pending.timer);
      waiting.delete(message.id);
      message.error ? pending.reject(Error(JSON.stringify(message.error))) : pending.resolve(message.result);
    }
  };
  const cdp = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { waiting.delete(id); reject(Error(`Таймаут ${method}`)); }, 20000);
    waiting.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const navigate = async (surface, width, height, suffix = '') => {
    await cdp('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    const url = pathToFileURL(path.join(directory, 'output', surface, 'index.html')).href + suffix;
    await cdp('Page.navigate', { url });
    for (let i = 0; i < 100; i++) {
      if (await evaluate(`location.href === ${JSON.stringify(url)} && document.readyState === 'complete'`)) break;
      await sleep(50);
    }
    await sleep(150);
  };
  const screenshot = async name => {
    const result = await cdp('Page.captureScreenshot', { format: 'png' });
    await writeFile(path.join(evidence, `${name}.png`), Buffer.from(result.data, 'base64'));
  };
  const key = async (key, code, windowsVirtualKeyCode) => {
    await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key, code, windowsVirtualKeyCode });
    if(key==='Enter') await cdp('Input.dispatchKeyEvent', { type:'char', text:'\r', unmodifiedText:'\r', key, code, windowsVirtualKeyCode });
    await cdp('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode });
    await sleep(80);
  };
  const pdf = async name => {
    const result = await cdp('Page.printToPDF', { printBackground: true, preferCSSPageSize: true });
    await writeFile(path.join(evidence, `${name}.pdf`), Buffer.from(result.data, 'base64'));
  };
  const report = { slides: [], interface: [], interactions: {} };
  const capture = async label => {
    report.interactions[label] = await evaluate(`({text: document.body.innerText, focus: document.activeElement?.outerHTML, selected: [...document.querySelectorAll('[aria-selected="true"], [aria-current]')].map(e=>e.outerHTML), scrollY})`);
  };
  await cdp('Page.enable');
  await navigate('slides', 1280, 720, '?theme=dark#1');
  const count = await evaluate(`document.querySelectorAll('.slide[data-source]').length`);
  if (!count) throw Error('Колода не создала экранные состояния');
  for (let page = 1; page <= count; page++) {
    if (page > 1) await key('ArrowRight', 'ArrowRight', 39);
    await sleep(1400); // Дождаться конечного значения счётчиков, не сравнивать промежуточное число.
    report.slides.push(await evaluate(`(() => {
      const slide = document.querySelector('.slide[data-active]');
      const rect = slide.getBoundingClientRect();
      const overflow = [...slide.querySelectorAll('*')].filter(el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return r.width && r.height && s.visibility !== 'hidden' && s.display !== 'none' &&
          (r.right > rect.right + 2 || r.bottom > rect.bottom + 2 || r.left < rect.left - 2 || r.top < rect.top - 2);
      }).map(el => ({tag:el.tagName, class:el.className, text:el.innerText?.slice(0,100)}));
      const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
      const visible = [];
      while(walker.nextNode()) {
        let hidden = false;
        for(let el=walker.currentNode.parentElement;el;el=el.parentElement) {
          const style=getComputedStyle(el);
          if(style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0) {hidden=true;break;}
        }
        if(!hidden && walker.currentNode.textContent.trim()) visible.push(walker.currentNode.textContent.trim());
      }
      return {page:slide.dataset.index, source:slide.dataset.source, step:slide.dataset.step, layout:slide.dataset.slideLayout,
        text:visible.join(' | '), allText:slide.textContent, html:slide.outerHTML, overflow};
    })()`));
    await screenshot(`slide-${String(page).padStart(2,'0')}`);
  }
  await pdf('slides');
  await key('ArrowLeft', 'ArrowLeft', 37);
  report.previousSlide = await evaluate(`document.querySelector('.slide[data-active]')?.dataset.index`);
  await navigate('slides', 390, 844, '?theme=light#1');
  await screenshot('slides-mobile-light');

  for (const [width, height] of [[1440,900], [390,844], [320,844]]) {
    for (const theme of ['dark','light']) {
      await navigate('interface', width, height, `?theme=${theme}`);
      report.interface.push(await evaluate(`({width:innerWidth, scrollWidth:document.documentElement.scrollWidth, theme:document.documentElement.dataset.theme, text:document.body.innerText, controls:[...document.querySelectorAll('button,input,select,[tabindex]')].map(e=>({tag:e.tagName,id:e.id,role:e.getAttribute('role'),type:e.type,text:e.innerText,label:e.getAttribute('aria-label'),tabindex:e.tabIndex}))})`));
      await screenshot(`interface-${width}-${theme}`);
    }
  }
  await navigate('interface', 390, 844, '?theme=light');
  await capture('initial');
  // Настоящие нажатия Tab выявляют отсутствие клавиатурного пути без подстановки фокуса в нужную строку.
  report.tabOrder = [];
  for (let i = 0; i < 12; i++) {
    await key('Tab','Tab',9);
    report.tabOrder.push(await evaluate(`({tag:document.activeElement.tagName,id:document.activeElement.id,role:document.activeElement.getAttribute('role'),text:document.activeElement.innerText?.slice(0,120)})`));
  }
  const searchFound = await evaluate(`(() => {
    const search = document.querySelector('input[type="search"]') || document.querySelector('input[type="text"]');
    if (!search) return false;
    search.focus(); search.value = 'оплаты'; search.dispatchEvent(new Event('input',{bubbles:true})); return true;
  })()`);
  if (!searchFound) throw Error('Не найден поиск');
  await sleep(300); await capture('search-payment'); await screenshot('search-payment'); await pdf('interface-filtered');
  const filterFound = await evaluate(`(() => {
    const select = [...document.querySelectorAll('select')].find(e=>[...e.options].some(o=>o.text.includes('Готово')));
    if (select) { select.value=[...select.options].find(o=>o.text.includes('Готово')).value; select.dispatchEvent(new Event('change',{bubbles:true})); return true; }
    const radio = [...document.querySelectorAll('input[type="radio"]')].find(e=>e.closest('label')?.innerText.includes('Готово'));
    if (radio) {radio.click();return true;} return false;
  })()`);
  report.filterFound = filterFound;
  await sleep(300); await capture('empty-result'); await screenshot('empty-result'); await pdf('interface-empty');
  const resetFound = await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(e=>/сброс/i.test(e.innerText) && e.getBoundingClientRect().width);
    if (!button) return false; button.click(); return true;
  })()`);
  report.resetFound = resetFound;
  await sleep(300); await capture('reset');
  // Выбор оплаты через доступный элемент списка, затем проверка Enter и ArrowDown.
  const recordFound = await evaluate(`(() => {
    const listbox=document.querySelector('[role="listbox"][tabindex]');
    if(listbox) {listbox.focus();return 'listbox';}
    const record = [...document.querySelectorAll('button,[role="option"][tabindex],tr[tabindex],[role="row"][tabindex]')].find(e=>/Проверка оплаты/.test(e.innerText) && e.getBoundingClientRect().width);
    if(!record)return false; record.focus(); return 'record';
  })()`);
  report.recordFound = recordFound;
  if (recordFound) {
    if(recordFound==='listbox') {await key('Home','Home',36);await key('ArrowDown','ArrowDown',40);}
    await key('Enter','Enter',13); await capture('keyboard-payment'); await screenshot('keyboard-payment');
    if(recordFound==='listbox') await evaluate(`document.querySelector('[role="listbox"]').focus()`);
    await key('ArrowDown','ArrowDown',40); await capture('keyboard-next');
  }
  const point = await evaluate(`(() => {
    const record=[...document.querySelectorAll('button,[role="option"],tr[tabindex],[role="row"][tabindex]')].find(e=>/Проверка профиля/.test(e.innerText)&&e.getBoundingClientRect().width);
    if(!record)return null;
    record.scrollIntoView({block:'center',behavior:'instant'});
    const r=record.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
  })()`);
  if(point) {
    await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...point});
    await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...point});
    await sleep(300);await capture('mouse-profile');await screenshot('mouse-profile');
  }
  await pdf('interface-current');
  await writeFile(path.join(evidence,'browser.json'), JSON.stringify(report,null,2));
  console.log(JSON.stringify({directory, pages:count, filterFound, resetFound, recordFound}));
} finally {
  socket?.close();
  browser.kill('SIGTERM');
  await new Promise(resolve => { browser.once('exit',resolve); setTimeout(resolve,3000); });
  await rm(profile,{recursive:true,force:true,maxRetries:3});
}
