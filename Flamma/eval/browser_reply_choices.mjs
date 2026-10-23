// Run with reply_choices_browser_server.py and an isolated headless Edge on 9371.
import assert from 'node:assert/strict';
import { getReplyChoices } from '../static/reply-choices.js';

const browserPort = process.env.FLAMMA_BROWSER_PORT || '9371';
const target = await fetch(`http://127.0.0.1:${browserPort}/json/new?http://127.0.0.1:5017/`, { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let sequence = 0, chatId;
const requests = new Map(), exceptions = [], choosers = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (message.method === 'Page.fileChooserOpened') choosers.push(message.params);
  const pending = requests.get(message.id);
  if (!pending) return;
  requests.delete(message.id); clearTimeout(pending.timer);
  if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
  else pending.resolve(message.result);
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { requests.delete(id); reject(new Error(`${method} timed out`)); }, 60000);
    requests.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitUntil(expression, label) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw new Error(label);
}
const ready = () => waitUntil("!!document.querySelector('textarea') && document.querySelector('.composer')?.getAttribute('aria-busy') !== 'true' && !document.querySelector('textarea').disabled", 'Composer not ready');
async function waitReply(previous) {
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'`, 'Reply did not arrive');
  const messages = await evaluate("[...document.querySelectorAll('.row.bot')].map(row => [...row.querySelectorAll('.follow-ups button')].map(button => button.textContent))");
  assert.ok(messages.every(choices => choices.length >= 3), JSON.stringify(messages));
  assert.ok(messages.every(choices => new Set(choices).size === choices.length));
  const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r => r.json())`);
  assert.deepEqual(messages.at(-1), getReplyChoices(detail.messages.at(-1)));
  return detail.messages.at(-1);
}
async function send(text) {
  await ready();
  const count = await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate("document.querySelector('textarea').focus()");
  await command('Input.insertText', { text });
  await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
  await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  return waitReply(count);
}
async function clickChoice(text) {
  await ready();
  const count = await evaluate("document.querySelectorAll('.row.bot').length");
  const point = await evaluate(`(() => {
    const button = [...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-ups button');
    const target = [...button].find(item => item.textContent === ${JSON.stringify(text)});
    if (!target || target.disabled) throw new Error('Choice is missing or disabled');
    target.scrollIntoView({ block: 'center' });
    const bounds = target.getBoundingClientRect();
    return { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 };
  })()`);
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
  return text === 'Choose photo' ? null : waitReply(count);
}
try {
  await command('Runtime.enable'); await command('Page.enable');
  await command('Page.setInterceptFileChooserDialog', { enabled: true });
  await ready();
  await evaluate("document.querySelector('.new-chat').click()");
  chatId = await evaluate("localStorage.getItem('flamma.activeChat')");
  await send('hello');
  let result = await clickChoice('I have a rash');
  assert.ok(result.followUps.includes('My arm'));
  result = await clickChoice('My arm');
  assert.ok(result.followUps.includes('Two weeks'));
  result = await clickChoice('Two weeks');
  assert.ok(result.followUps.includes('None'));
  result = await clickChoice('None');
  assert.ok(result.followUps.includes('Choose photo'));
  assert.equal(choosers.length, 0, 'A reply opened the picker automatically');
  await clickChoice('Choose photo');
  await waitUntil('true', 'Picker did not open');
  await new Promise(resolve => setTimeout(resolve, 150));
  assert.equal(choosers.length, 1);

  const previous = await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate(`(async () => {
    const png = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='), c => c.charCodeAt(0));
    const transfer = new DataTransfer();
    transfer.items.add(new File([png], 'psoriasis.png', { type: 'image/png' }));
    const input = document.querySelector('input[type=file]');
    input.files = transfer.files; input.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    document.querySelector('.send-btn').click();
  })()`);
  result = await waitReply(previous);
  assert.equal(result.intent, 'image_classification');
  result = await clickChoice('Treatment options for this photo');
  assert.equal(result.treatmentInfo.condition_key, 'psoriasis');
  assert.ok(result.followUps.some(choice => choice.includes('Psoriasis')));
  result = await clickChoice('Explain simply');
  assert.ok(result.text.length > 0);

  const beforeReload = await evaluate("[...document.querySelectorAll('.row.bot')].map(row => [...row.querySelectorAll('.follow-ups button')].map(button => button.textContent))");
  await command('Page.reload');
  await waitUntil("document.querySelectorAll('.row.bot').length > 0 && !document.querySelector('textarea')?.disabled", 'History did not reload');
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.row.bot')].map(row => [...row.querySelectorAll('.follow-ups button')].map(button => button.textContent))"), beforeReload);

  await command('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true, 'Mobile layout overflowed');
  assert.equal(choosers.length, 1, 'A history reload reopened the picker');
  assert.deepEqual(exceptions, []);
  console.log('PASS: every visible bot reply has 3+ choices; actual clicks advance screening, picker is explicit, photo care stays contextual, history reload matches, and mobile layout fits.');
} finally {
  if (chatId) await evaluate(`fetch('/api/conversations/${chatId}', { method: 'DELETE' })`).catch(() => {});
  await command('Page.close').catch(() => {});
  socket.close();
}
