// Requires photo_treatment_browser_server.py on 5010 and an isolated Chrome on 9371.
// Photo labels are simulated; the chat model, HTTP routes, and browser UI are real.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const fixtureFolder = resolve('../.logs/photo-treatment-fixtures');
await mkdir(fixtureFolder, { recursive: true });
const target = await fetch('http://127.0.0.1:9371/json/new?about:blank', { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0;
const pending = new Map(), exceptions = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (!pending.has(message.id)) return;
  const { resolve, reject, timer } = pending.get(message.id);
  pending.delete(message.id); clearTimeout(timer);
  if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`${method} timed out`)); }, 15000);
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitUntil(expression, message) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 75));
  }
  throw new Error(message);
}
const ready = "!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && !document.querySelector('.caret') && !document.querySelector('.typing')";
async function saved() {
  return evaluate("fetch('/api/conversations/'+localStorage.getItem('flamma.activeChat')).then(r=>r.json())");
}
async function upload(label) {
  const file = resolve(fixtureFolder, `${label}.png`);
  await writeFile(file, Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64'));
  const previous = await evaluate("document.querySelectorAll('.row.bot').length");
  const doc = await command('DOM.getDocument');
  const input = await command('DOM.querySelector', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
  await command('DOM.setFileInputFiles', { nodeId: input.nodeId, files: [file] });
  await waitUntil("!document.querySelector('.send-btn').disabled", 'Upload did not enable Send');
  await evaluate("document.querySelector('.send-btn').click()");
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Photo reply did not finish');
}
async function send(text) {
  const previous = await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate("document.querySelector('textarea').focus()");
  await command('Input.insertText', { text });
  await waitUntil("!document.querySelector('.send-btn').disabled", 'Send did not enable');
  await evaluate("document.querySelector('.send-btn').click()");
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Text reply did not finish');
  return (await saved()).messages.at(-1);
}

try {
  await command('Page.enable'); await command('Runtime.enable');
  await command('Page.navigate', { url: 'http://127.0.0.1:5010/' });
  await waitUntil(ready, 'Chat did not load');
  for (const label of ['atopic_dermatitis', 'contact_dermatitis', 'lichen_planus', 'psoriasis', 'rosacea', 'normal_skin']) {
    await evaluate("document.querySelector('.new-chat').click()");
    await waitUntil("document.querySelectorAll('.row.user').length === 0 && " + ready, 'New chat did not open');
    await upload(label);
    let detail = await saved();
    const result = detail.messages.at(-1);
    assert.equal(result.treatmentInfo.condition_key, label);
    assert.ok(result.text.includes('General care:'));
    assert.ok(await evaluate("document.querySelector('.care-sources a')?.href.startsWith('https://')"));
    await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(button=>{if(button.textContent==='Treatment options for this photo')button.click()})");
    await waitUntil("document.querySelectorAll('.row.bot').length === 2 && " + ready, 'Treatment follow-up did not finish');
    detail = await saved();
    assert.equal(detail.messages.at(-1).treatmentInfo.condition_key, label);
    assert.equal(detail.messages.at(-1).sourceImageId, detail.messages[0].id);
    if (label === 'normal_skin') {
      assert.deepEqual(detail.messages.at(-1).treatmentInfo.clinician_options, []);
      assert.ok(detail.messages.at(-1).text.includes('No disease-specific medication'));
    }
    assert.ok(await evaluate("[...document.querySelectorAll('.confidence')].some(e=>e.textContent.includes('Photo model score:'))"));
    assert.ok(await evaluate("document.querySelector('.score-note')?.textContent.includes('not disease probabilities')"));
    assert.ok(await evaluate("document.querySelector('.care-sources')?.textContent.includes('Source links checked:')"));
    await command('Page.reload');
    await waitUntil("document.querySelectorAll('.row.bot').length === 2 && " + ready, 'Saved treatment did not restore');
    assert.equal(await evaluate("document.querySelectorAll('.care-sources').length"), 2);
    console.log(`${label}: care, treatment follow-up, source links, and reload passed`);
    if (label === 'contact_dermatitis') {
      assert.ok(await evaluate("[...document.querySelectorAll('.confidence')].some(e=>e.textContent.includes('99.7%'))"));
      assert.ok(!await evaluate("[...document.querySelectorAll('.confidence')].some(e=>e.textContent.includes('100%'))"));
      const course = await send('how long this usually last?');
      assert.equal(course.intent, 'knowledge_question');
      assert.ok(course.text.includes('days to weeks'));
      assert.ok(course.text.includes('not a personal recovery deadline'));
      assert.equal(course.treatmentInfo.topic, 'course');
      assert.ok(course.treatmentInfo.sources.some(source => source.url.includes('111.wales.nhs.uk')));
      await command('Page.reload');
      await waitUntil(ready, 'Course answer did not restore');
      assert.ok((await send('Explain simply')).text.includes('days to weeks'));
      console.log('Contact dermatitis: expected-course question, source links, history reload, and accurate 99.7% display passed');
    }
  }
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil("document.querySelectorAll('.row.user').length === 0 && " + ready, 'Photo-topic test chat did not open');
  await upload('atopic_dermatitis');
  const photoSource = (await saved()).messages[0].id;
  await send('Tell me about rosacea');
  const pluralPhoto = await send('Treatment for my pictures');
  assert.equal(pluralPhoto.treatmentInfo.condition_key, 'atopic_dermatitis');
  assert.equal(pluralPhoto.sourceImageId, photoSource);
  const namedSame = await send('Treatment options for atopic dermatitis');
  assert.equal(namedSame.sourceImageId, undefined);
  await command('Page.reload');
  await waitUntil(ready, 'Named-condition origin did not restore');
  assert.equal((await send('Is it treatable?')).sourceImageId, undefined);
  await send('Tell me about rosacea');
  await send('What do you think about my photos?');
  const barePhoto = await send('Is it treatable?');
  assert.equal(barePhoto.treatmentInfo.condition_key, 'atopic_dermatitis');
  assert.equal(barePhoto.sourceImageId, photoSource);
  const different = await send('Treatment for rosacea in my photo');
  assert.ok(different.text.includes("latest photo's screening match was Atopic Dermatitis"));
  assert.equal(different.treatmentInfo.condition_key, 'rosacea');
  assert.equal(different.sourceImageId, undefined);
  console.log('Photo and named-condition context: plural references, explicit origin, reload, explanation follow-up, and disagreement passed');
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil("document.querySelectorAll('.row.user').length === 0 && " + ready, 'Rejected-photo test chat did not open');
  await upload('rejected');
  const rejectedBotCount = await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate("document.querySelector('textarea').focus()");
  await command('Input.insertText', { text: 'Treatment options for this photo' });
  await evaluate("document.querySelector('.send-btn').click()");
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${rejectedBotCount + 1} && ${ready}`, 'Rejected-photo follow-up did not finish');
  const rejected = (await saved()).messages.at(-1);
  assert.equal(rejected.treatmentInfo, undefined);
  assert.ok(rejected.text.includes("couldn't reliably classify"));
  assert.deepEqual(exceptions, []);
  console.log('Rejected photo: no old treatment; no browser exceptions. Image results were simulated.');
  const overview = await send('I think this is rosacea');
  assert.equal(overview.intent, 'knowledge_question');
  assert.ok(!overview.text.includes('Treatment options to discuss with a clinician:'));
  const diagnosis = await send('is this my skin conditon?');
  assert.equal(diagnosis.intent, 'diagnosis_question');
  assert.ok(diagnosis.text.includes('cannot confirm'));
  assert.ok(diagnosis.text.includes('not classified reliably'));
  assert.ok(diagnosis.text.includes('Rosacea'));
  await command('Page.reload');
  await waitUntil(ready, 'Diagnosis follow-up did not restore');
  const previous = await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(button=>{if(button.textContent==='Is it treatable?')button.click()})");
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Treatability button did not finish');
  const care = (await saved()).messages.at(-1);
  assert.equal(care.intent, 'knowledge_question');
  assert.equal(care.treatmentInfo.condition_key, 'rosacea');
  assert.equal(care.sourceImageId, undefined);
  assert.ok(care.text.includes('treatment can help control symptoms'));
  assert.equal(care.text.split('General care:').length - 1, 0);
  assert.ok(care.text.split(/\s+/).length < 55);
  assert.equal(await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelector('.bubble').textContent"), care.text);
  assert.ok(await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelector('.care-sources a')?.href.startsWith('https://')"));
  assert.deepEqual(exceptions, []);
  console.log('Rejected-photo rosacea discussion: diagnosis remains unconfirmed; treatability uses management and sources after reload.');
  const full = await send('Treatment options for Rosacea');
  assert.equal(full.text.split('General care:').length - 1, 1);
  assert.ok(full.text.includes('Treatment options to discuss with a clinician:'));
} finally {
  await evaluate("fetch('/api/conversations',{method:'DELETE'}).then(r=>r.json())").catch(() => {});
  await command('Browser.close').catch(() => {});
  socket.close();
}
