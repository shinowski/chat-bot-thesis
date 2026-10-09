// Use an isolated headless-browser profile on port 9371.
// Run: node eval/browser_typing_smoke.mjs
import assert from 'node:assert/strict';

const target = await fetch(`http://127.0.0.1:9371/json/new?${encodeURIComponent(process.env.BROWSER_APP_URL || 'http://127.0.0.1:5000/')}`, { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0;
let testChatId;
const createdChats = new Set();
const pending = new Map();
const predicts = [];
const exceptions = [];
const warnings = [];
let holdPredict = false;
const paused = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Network.requestWillBeSent' && new URL(message.params.request.url).pathname === '/predict') predicts.push(message.params);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (message.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(message.params.type)) warnings.push(message.params.args.map(arg=>arg.value || arg.description));
  if (message.method === 'Fetch.requestPaused') {
    if (holdPredict) paused.push(message.params.requestId);
    else command('Fetch.continueRequest', { requestId: message.params.requestId }).catch(() => {});
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
async function waitUntil(check, message) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(message);
}
async function type(text, focus = true) {
  if (focus) await evaluate("document.querySelector('textarea').focus()");
  for (const character of text) {
    await command('Input.insertText', { text: character });
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
  }
}
async function enter(modifiers = 0) {
  await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', modifiers });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, modifiers });
}
async function clickSend() {
  const point = await evaluate("(() => {const e=document.querySelector('.send-btn'); e.scrollIntoView({block:'nearest'}); const r=e.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};})()");
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...point });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...point });
}
async function clearDraft() {
  await evaluate("(() => {const e=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,'');e.dispatchEvent(new Event('input',{bubbles:true}));})()");
}
const ready = () => waitUntil(() => evaluate("!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'"), 'Chat did not become ready');
async function snapshot() {
  return evaluate(`({chats:[...document.querySelectorAll('.history-select')].map(e=>e.title),
    messages:[...document.querySelectorAll('.bubble')].map(e=>e.textContent),title:document.querySelector('.chat-title').textContent,
    panels:document.querySelectorAll('.messages').length,composers:document.querySelectorAll('textarea').length})`);
}

try {
  await command('Page.enable'); await command('Runtime.enable'); await command('Network.enable'); await ready();
  const originalId = await evaluate("localStorage.getItem('flamma.activeChat')");
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil(() => evaluate("document.querySelectorAll('.row.user').length === 0"), 'New chat did not open');
  const firstNewId = await evaluate("localStorage.getItem('flamma.activeChat')");
  assert.notEqual(firstNewId, originalId, 'New conversation reused an existing conversation');
  await type('This draft has not been sent');
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil(() => evaluate("document.querySelector('textarea').value === ''"), 'New chat did not clear the composer');
  assert.notEqual(await evaluate("localStorage.getItem('flamma.activeChat')"), firstNewId, 'Repeated New conversation reused the empty chat');
  console.log('New conversation: each click creates a distinct empty chat');
  const before = await snapshot();
  assert.equal(before.panels, 1);
  assert.equal(before.composers, 1);
  testChatId = await evaluate("localStorage.getItem('flamma.activeChat')");
  createdChats.add(testChatId);
  await type('hello');
  assert.deepEqual(await snapshot(), before);
  assert.equal(predicts.length, 0);
  console.log('Typing in an empty conversation: no extra chats, messages, or requests');
  holdPredict = true;
  await command('Fetch.enable', { patterns: [{ urlPattern: '*/predict' }] });
  await enter();
  await waitUntil(() => paused.length === 1, 'Enter did not send the message');
  assert.equal(await evaluate("document.activeElement === document.querySelector('textarea')"), true);
  assert.equal(await evaluate("document.querySelector('textarea').disabled"), false);
  await type('Draft while waiting', false);
  await enter();
  assert.equal(paused.length, 1, 'Enter submitted a second message while a reply was pending');
  assert.equal(await evaluate("document.querySelector('textarea').value"), 'Draft while waiting');
  holdPredict = false;
  await command('Fetch.continueRequest', { requestId: paused[0] });
  await command('Fetch.disable');
  await ready();
  assert.equal(await evaluate("document.activeElement === document.querySelector('textarea')"), true);
  assert.equal(await evaluate("document.querySelector('textarea').value"), 'Draft while waiting');
  console.log('Enter: focus retained and next draft preserved while waiting for the reply');
  await clearDraft();
  await type('first line', false); await enter(8); await type('second line', false);
  assert.equal(await evaluate("document.querySelector('textarea').value"), 'first line\nsecond line');
  assert.equal(predicts.length, 1, 'Shift+Enter sent the draft');
  await clearDraft();
  await waitUntil(() => evaluate("!document.querySelector('.caret')"), 'Reply did not finish');
  assert.equal(predicts.length, 1);
  const sent = await snapshot();
  await type('my skin is itchy and it started two weeks ago', false);
  assert.deepEqual(await snapshot(), sent);
  assert.equal(predicts.length, 1);
  console.log('Typing after a reply: conversation and messages unchanged');
  await clickSend(); await ready();
  assert.equal(await evaluate("document.activeElement === document.querySelector('textarea')"), true, 'Clicking Send did not restore the text cursor');
  await waitUntil(() => evaluate("!document.querySelector('.caret')"), 'Reply did not finish');
  assert.equal(predicts.length, 2);
  assert.equal(await evaluate("document.querySelectorAll('.row.user').length"), 2);
  assert.equal(await evaluate("document.querySelectorAll('.row.bot').length"), 2);
  console.log('Send: one exchange, focus restored; Shift+Enter inserts a new line');

  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil(() => evaluate("document.querySelectorAll('.row.user').length === 0"), 'Saved messages appeared in a new chat');
  assert.notEqual(await evaluate("localStorage.getItem('flamma.activeChat')"), testChatId);
  await command('Page.reload'); await ready();
  assert.equal(await evaluate("document.querySelectorAll('.row.user').length"), 0, 'Refreshing a blank chat reopened an older conversation');
  assert.equal(await evaluate("document.querySelector('.chat-title').textContent"), 'New conversation');
  const freshId = await evaluate("localStorage.getItem('flamma.activeChat')");
  createdChats.add(freshId);
  await type('my skin is itchy');
  await evaluate("document.querySelector('.send-btn').click()"); await ready();
  const fresh = await evaluate(`fetch('/api/conversations/${freshId}').then(r=>r.json())`);
  assert.equal(fresh.messages.length, 2);
  assert.equal(fresh.messages[1].intent, 'symptom');
  assert.match(fresh.messages[1].text, /where/i, 'New chat inherited the earlier screening state');
  const old = await evaluate(`fetch('/api/conversations/${testChatId}').then(r=>r.json())`);
  assert.equal(old.messages.length, 4, 'New messages were appended to the old chat');
  await evaluate(`document.querySelector('[data-conversation-id="${testChatId}"]').click()`); await ready();
  assert.equal(await evaluate("document.querySelectorAll('.row.user').length"), 2);
  console.log('New chat after a saved chat: blank after refresh, independent memory, and old chat retained');
  assert.deepEqual(exceptions, []);
  assert.deepEqual(warnings, [], 'React emitted a rendering warning');
} catch (error) {
  console.log('React diagnostics:', warnings);
  console.log('Chat diagnostics:', await snapshot());
  throw error;
} finally {
  for (const id of createdChats) await evaluate(`fetch('/api/conversations/${id}',{method:'DELETE'}).then(r=>r.json())`).catch(() => {});
  await command('Browser.close').catch(() => {}); socket.close();
}
