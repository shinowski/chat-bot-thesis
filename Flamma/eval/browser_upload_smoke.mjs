// Run against the local app and a headless Chromium browser on port 9371:
// node eval/browser_upload_smoke.mjs
import assert from 'node:assert/strict';

const appUrl = process.env.BROWSER_APP_URL || 'http://127.0.0.1:5000/';
const uploadMessage = process.env.UPLOAD_TEST_MESSAGE || 'I want to send an image';
const target = await fetch(`http://127.0.0.1:9371/json/new?${encodeURIComponent(appUrl)}`, { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0;
const pending = new Map();
const choosers = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Page.fileChooserOpened') choosers.push(message.params);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject, timer } = pending.get(message.id);
    pending.delete(message.id);
    clearTimeout(timer);
    if (message.error) reject(new Error(JSON.stringify(message.error)));
    else resolve(message.result);
  }
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`${method} timed out`));
    }, 10000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true });
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
  await waitUntil(() => evaluate(`(() => {
    const element = (${expression}); if (!element) return false;
    element.scrollIntoView({block:'nearest'});
    const bounds = element.getBoundingClientRect();
    return bounds.width > 0 && element.contains(document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2));
  })()`), 'Click target was obscured', 10000);
  const point = await evaluate(`(() => { const bounds = (${expression}).getBoundingClientRect(); return {x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2}; })()`);
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
}

try {
  await command('Page.enable');
  await command('Page.setInterceptFileChooserDialog', { enabled: true });
  await waitUntil(() => evaluate("!!document.querySelector('textarea')"), 'Chat did not render');
  await evaluate(`(() => {
    const input = document.querySelector('textarea');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(input, ${JSON.stringify(uploadMessage)});
    input.dispatchEvent(new Event('input', {bubbles: true}));
  })()`);
  await waitUntil(() => evaluate("!document.querySelector('.send-btn').disabled"), 'Send button stayed disabled');
  await click("document.querySelector('.send-btn')");

  const chooseButton = "[...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'Choose photo')";
  await waitUntil(() => evaluate(`!!(${chooseButton}) && !(${chooseButton}).disabled`), 'Choose photo button did not appear');
  assert.equal(choosers.length, 0, 'Typing an upload request opened the picker automatically');
  console.log('Photo request waits for an explicit button click: verified');
  const buttonLabels = await evaluate("[...document.querySelectorAll('button')].map(button => button.textContent.trim())");
  assert.equal(buttonLabels.some(label => ['Mild', 'Moderate', 'Severe'].includes(label)), false);
  await click(chooseButton);
  await waitUntil(() => choosers.length > 0, 'Choose photo button did not open the picker', 10000);
  console.log('Choose photo button: verified');
  console.log('Severity choices: absent');
  await command('DOM.setFileInputFiles', { files: [], backendNodeId: choosers[0].backendNodeId });
} finally {
  await command('Browser.close').catch(() => {});
  socket.close();
}
