// Use a dedicated headless-browser profile on port 9371, never your normal browser.
// Run: node eval/browser_history_smoke.mjs
import assert from 'node:assert/strict';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const logs = fileURLToPath(new URL('../../.logs/', import.meta.url));
const downloads = fileURLToPath(new URL('../../.logs/history-downloads/', import.meta.url));
await mkdir(downloads, { recursive: true });
const target = await fetch('http://127.0.0.1:9371/json/new?http://127.0.0.1:5000/', { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0;
const pending = new Map();
const exceptions = [];
const choosers = [];
const downloadEvents = [];
let blockHistory = false;
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (message.method === 'Page.fileChooserOpened') choosers.push(message.params);
  if (message.method === 'Browser.downloadWillBegin') downloadEvents.push(message.params);
  if (message.method === 'Fetch.requestPaused') {
    command(blockHistory ? 'Fetch.failRequest' : 'Fetch.continueRequest', {
      requestId: message.params.requestId, ...(blockHistory ? { errorReason: 'InternetDisconnected' } : {}),
    }).catch(() => {});
  }
  if (message.id && pending.has(message.id)) {
    const { resolve, reject, timer } = pending.get(message.id);
    pending.delete(message.id); clearTimeout(timer);
    if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
  }
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`${method} timed out`)); }, 60000);
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitUntil(check, message, timeout = 60000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(message);
}
async function click(expression) {
  // Wait for drawer/dialog transitions so another layer does not receive the click.
  await waitUntil(() => evaluate(`(() => {
    const e=(${expression}); if(!e)return false; e.scrollIntoView({block:'nearest'});
    const r=e.getBoundingClientRect(); return r.width>0 && e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));
  })()`), 'Click target is obscured', 10000);
  const point = await evaluate(`(() => { const element = (${expression}); element.scrollIntoView({block:'nearest'}); const r = element.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
}
async function fill(selector, text) {
  await evaluate(`(() => { const input = document.querySelector(${JSON.stringify(selector)});
    const prototype = input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype,'value').set.call(input,${JSON.stringify(text)});
    input.dispatchEvent(new Event('input',{bubbles:true})); })()`);
}
const button = text => `[...document.querySelectorAll('button')].filter(b=>b.textContent.trim()===${JSON.stringify(text)}).at(-1)`;
const ready = () => waitUntil(() => evaluate("!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'"), 'Chat did not become ready');
async function send(text) {
  await ready(); await fill('textarea', text);
  await waitUntil(() => evaluate("!document.querySelector('.send-btn').disabled"), 'Send stayed disabled');
  await click("document.querySelector('.send-btn')"); await ready();
}
async function menuAction(text) {
  await click("document.querySelector('.history-item.active .history-menu-toggle')");
  await click(button(text));
}
async function screenshot(name) {
  const shot = await command('Page.captureScreenshot', { format: 'png' });
  await writeFile(`${logs}${name}.png`, Buffer.from(shot.data, 'base64'));
}

try {
  await command('Page.enable'); await command('Runtime.enable');
  await command('Network.enable');
  await command('Page.setInterceptFileChooserDialog', { enabled: true });
  await command('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: downloads, eventsEnabled: true });
  await command('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await ready();
  // Remove only this dedicated test browser's previous test conversations.
  await evaluate("fetch('/api/conversations',{method:'DELETE'}).then(r=>r.json())");
  await command('Page.reload'); await ready();
  await send('my skin is itchy on my arms');
  const chatId = await evaluate("fetch('/api/conversations').then(r=>r.json()).then(d=>d.conversations[0].id)");
  await menuAction('Rename');
  await fill('dialog input', 'Arm check'); await click(button('Save name'));
  await waitUntil(() => evaluate("document.querySelector('.chat-title').textContent === 'Arm check'"), 'Rename failed');
  console.log('Send, automatic saving, and rename: passed');

  await click(button('New conversation')); await send('hello');
  await fill('.history-search input', 'ITCHY');
  await waitUntil(() => evaluate("document.querySelectorAll('.history-item').length === 1 && !!document.querySelector('mark')"), 'Message search failed');
  assert.equal(await evaluate("document.querySelector('.history-select .t').textContent"), 'Arm check');
  await click("document.querySelector('.history-select')"); await ready();
  await fill('.history-search input', 'no-such-phrase-92857');
  await waitUntil(() => evaluate("document.querySelector('.history-empty')?.textContent.includes('No conversations')"), 'Empty-search state failed');
  await fill('.history-search input', '');
  await command('Page.reload'); await ready();
  assert.equal(await evaluate("document.querySelector('.chat-title').textContent"), 'Arm check');
  assert.equal(await evaluate("document.querySelectorAll('.row.user').length"), 1);
  await send('two weeks');
  assert.equal(await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json()).then(d=>d.messages.at(-1).intent)`), 'duration');
  console.log('Search, refresh, active conversation, and resumed bot context: passed');

  await menuAction('Export text');
  await waitUntil(() => downloadEvents.length > 0, 'Export did not download');
  await waitUntil(async () => { try { return (await readFile(`${downloads}Arm check.txt`, 'utf8')).includes('two weeks'); } catch { return false; } }, 'Export content missing');
  console.log('Text export: passed');

  await evaluate(`(async () => {
    const bytes = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='),c=>c.charCodeAt(0));
    const form = new FormData(); form.append('conversation_id',${JSON.stringify(chatId)});
    form.append('image',new Blob([bytes],{type:'image/png'}),'test.png');
    return fetch('/predict',{method:'POST',body:form}).then(r=>r.json()).then(d=>d.intent);
  })()`);
  await command('Page.reload'); await ready();
  await waitUntil(() => evaluate("[...document.querySelectorAll('.row.user img')].some(i=>i.complete&&i.naturalWidth>0&&i.src.includes('/api/conversations/'))"), 'Saved photo did not survive refresh');
  await screenshot('history-desktop');
  console.log('Photo persistence after refresh: passed');

  await command('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await waitUntil(() => evaluate("document.querySelector('.menu-btn').getBoundingClientRect().width > 0"), 'Mobile layout did not activate');
  await click("document.querySelector('.menu-btn')");
  await waitUntil(() => evaluate("document.querySelector('.sidebar').classList.contains('open')"), 'Mobile history did not open');
  await waitUntil(() => evaluate("document.querySelector('.sidebar').getBoundingClientRect().left >= -1"), 'Mobile drawer transition did not finish');
  await screenshot('history-mobile');
  await menuAction('Delete');
  await click(button('Cancel'));
  assert.equal(await evaluate("document.querySelectorAll('.history-item').length"), 2);
  await menuAction('Delete'); await click(button('Delete'));
  await waitUntil(() => evaluate("document.querySelectorAll('.history-item').length === 1 && !document.querySelector('dialog')"), 'Delete failed');
  await ready();
  await click(button('Clear history')); await click(button('Cancel'));
  assert.equal(await evaluate("document.querySelectorAll('.history-item').length"), 1);
  await click(button('Clear history')); await click(button('Clear history'));
  await waitUntil(() => evaluate("!document.querySelector('dialog') && document.querySelector('.chat-title').textContent === 'New conversation'"), 'Clear failed');
  assert.equal(await evaluate("fetch('/api/conversations').then(r=>r.json()).then(d=>d.conversations.length)"), 0);
  await command('Page.reload'); await ready();
  console.log('Mobile history, delete/clear confirmation, and empty history: passed');

  await command('Emulation.clearDeviceMetricsOverride');
  await send('can i sent pictuer');
  assert.equal(choosers.length, 0);
  await waitUntil(() => evaluate(`!!(${button('Choose photo')}) && !(${button('Choose photo')}).disabled`), 'Upload action did not appear');
  assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>['Mild','Moderate','Severe'].includes(b.textContent.trim()))"), false);
  console.log('Photo button without an automatic picker or severity gate: passed');

  blockHistory = true;
  await command('Fetch.enable', { patterns: [{ urlPattern: '*/api/conversations*' }] });
  await command('Page.reload');
  await waitUntil(() => evaluate("document.querySelector('[role=alert]')?.textContent.includes('history could not be loaded')"), 'History load error was not shown');
  assert.equal(await evaluate("document.querySelector('textarea').disabled"), true);
  blockHistory = false;
  await command('Fetch.disable');
  await click(button('Try again')); await ready();
  console.log('History connection failure and recovery: passed');
  assert.equal(exceptions.length, 0, 'Browser raised an uncaught exception');
  console.log('Browser runtime: no uncaught exceptions');
  await evaluate("fetch('/api/conversations',{method:'DELETE'}).then(r=>r.json())");
} catch (error) {
  await screenshot('history-failure').catch(() => {});
  throw error;
} finally {
  await command('Browser.close').catch(() => {}); socket.close();
}
