// Run with an isolated headless Edge profile listening on port 9371.
import assert from 'node:assert/strict';

const target = await fetch('http://127.0.0.1:9371/json/new?http://127.0.0.1:5000/', { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0, chatId;
const requests = new Map(), exceptions = [], choosers = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (message.method === 'Page.fileChooserOpened') choosers.push(message.params);
  if (!requests.has(message.id)) return;
  const { resolve, reject, timer } = requests.get(message.id);
  requests.delete(message.id); clearTimeout(timer);
  if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => reject(new Error(`${method} timed out`)), 60000);
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
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(label);
}
const ready = () => waitUntil("!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'", 'Composer not ready');
async function send(message) {
  await ready();
  const oldCount = await evaluate("document.querySelectorAll('.row.user').length");
  await evaluate("document.querySelector('textarea').focus()");
  await command('Input.insertText', { text: message });
  await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
  await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await waitUntil(`document.querySelectorAll('.row.user').length === ${oldCount + 1} && document.querySelector('.composer').getAttribute('aria-busy') !== 'true' && !![...document.querySelectorAll('.row.bot')].at(-1).querySelector('.intent-tag')`, 'Reply did not finish');
  const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r => r.json())`);
  return detail.messages.at(-1);
}

try {
  await command('Page.enable'); await command('Runtime.enable');
  await command('Page.setInterceptFileChooserDialog', { enabled: true });
  await ready();
  const originalId = await evaluate("localStorage.getItem('flamma.activeChat')");
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil(`document.querySelectorAll('.row.user').length === 0 && localStorage.getItem('flamma.activeChat') !== ${JSON.stringify(originalId)}`, 'New chat was not empty');
  chatId = await evaluate("localStorage.getItem('flamma.activeChat')");
  await send('hello');
  await send('can you help me');
  for (const message of ['banana', 'lala mo', 'o my god']) {
    const result = await send(message);
    assert.ok(['clarification', 'unknown'].includes(result.intent));
    assert.ok(!result.text.includes("I've noted"));
    assert.equal(result.confidence, null);
  }
  const cleanSummary = await send('summarize our conversation');
  for (const field of ['Skin symptoms', 'Affected area', 'How long', 'Medication used']) {
    assert.ok(cleanSummary.text.includes(`${field}: not provided`));
  }
  console.log('Reported random-text conversation: no invented location, duration, or symptoms');
  const report = 'my rash is itchy on my arm for two weeks';
  assert.match((await send(report)).text, /medication/i);
  const care = await send('what causes psoriasis and how can I treat it?');
  assert.equal(care.intent, 'knowledge_question');
  assert.match(care.text, /Causes:/); assert.match(care.text, /General care:/);
  assert.match((await send('idk')).text, /shorter explanation/);
  const simple = await send('explain simply');
  assert.equal(simple.intent, 'simple_explanation');
  assert.match(simple.text, /Short version/);
  console.log('Multi-part questions and context-aware uncertainty: passed');

  await command('Page.reload'); await ready();
  const followup = await send('and contagious?');
  assert.match(followup.text, /Psoriasis is not contagious/);
  const summary = await send('summarize our conversation');
  assert.equal(summary.intent, 'conversation_summary');
  assert.match(summary.text, /Medication used: not provided/);
  assert.ok(summary.text.includes(report));
  assert.ok(!summary.text.includes('Last classified photo:'));
  console.log('Topic memory after refresh and truthful conversation summary: passed');

  await send('skip the questions');
  const correction = await send('actually my left leg, not my arm, for three weeks');
  assert.equal(correction.intent, 'correction');
  assert.ok(!correction.text.includes('Have you applied'));
  const correctedSummary = await send('summarize our conversation');
  assert.match(correctedSummary.text, /Affected area: left leg/);
  assert.match(correctedSummary.text, /How long: three weeks/);
  assert.match((await send('continue screening')).text, /Have you applied any medication/);
  console.log('Pause, multiple corrections, and resume at the unanswered field: passed');

  const definition = await send('what is this disease?');
  assert.match(definition.text, /General information about Psoriasis/);
  assert.match(definition.text, /Overview:/);
  assert.match(definition.text, /Symptoms:/);
  assert.match(definition.text, /General care:/);
  const subtype = await send('what is contact dermatitis?');
  assert.match(subtype.text, /General information about Contact Dermatitis/);
  const generic = await send('what is this desease?');
  assert.match(generic.text, /General information about Contact Dermatitis/);
  const hives = await send('what is urticaria?');
  assert.match(hives.text, /General information about Hives/);
  console.log('Disease definitions, dermatitis subtypes, and hives alias: passed');

  const photoRequest = await send('can i upload image');
  assert.equal(photoRequest.action, 'upload_image');
  assert.equal(choosers.length, 0);
  assert.deepEqual(exceptions, []);
  console.log('Manual photo selection and browser runtime: passed');

  await evaluate(`fetch('/api/conversations/${chatId}', {method:'DELETE'}).then(r=>r.json())`);
  const previousId = chatId;
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil(`document.querySelectorAll('.row.user').length === 0 && localStorage.getItem('flamma.activeChat') !== ${JSON.stringify(previousId)}`, 'Fresh disease conversation did not open');
  chatId = await evaluate("localStorage.getItem('flamma.activeChat')");
  const noContext = await send('what is this disease?');
  assert.ok(noContext.text.includes("don't have a disease name"));
  assert.ok(noContext.followUps.includes('Contact Dermatitis'));
  const oldCount = await evaluate("document.querySelectorAll('.row.user').length");
  await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(b => {if (b.textContent === 'Contact Dermatitis') b.click();})");
  await waitUntil(`document.querySelectorAll('.row.user').length === ${oldCount + 1} && document.querySelector('.composer').getAttribute('aria-busy') !== 'true' && !![...document.querySelectorAll('.row.bot')].at(-1).querySelector('.intent-tag')`, 'Disease choice did not produce a reply');
  const chosen = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.match(chosen.messages.at(-1).text, /General information about Contact Dermatitis/);
  console.log('No-context clarification and disease choice buttons: passed');
} finally {
  if (chatId) await evaluate(`fetch('/api/conversations/${chatId}', {method:'DELETE'}).then(r=>r.json())`).catch(() => {});
  await command('Browser.close').catch(() => {}); socket.close();
}
