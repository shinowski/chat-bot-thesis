// Run with an isolated headless browser on port 9371; never use a personal profile.
import assert from 'node:assert/strict';

const target = await fetch('http://127.0.0.1:9371/json/new?about:blank', { method: 'PUT' }).then(r => r.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let nextId = 0, chatId;
const pending = new Map(), exceptions = [], held = [];
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
  if (message.method === 'Fetch.requestPaused') {
    held.push(message.params.requestId);
    if (message.params.responseStatusCode) command('Runtime.evaluate', {
      expression: "if (window.__simulateReplyTimeout === 'afterResponse') window.__fireReplyTimeout?.();",
    }).catch(() => {});
  }
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
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(message);
}
const ready = "!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'";
async function send(text) {
  await evaluate("document.querySelector('textarea').focus()");
  await command('Input.insertText', { text });
  await waitUntil("!document.querySelector('.send-btn').disabled", 'Send stayed disabled');
  await evaluate("document.querySelector('.send-btn').click()");
}

try {
  await command('Page.enable'); await command('Runtime.enable');
  await command('Page.addScriptToEvaluateOnNewDocument', { source: `
    window.__simulateReplyTimeout = false;
    const originalTimer = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay, ...args) => {
      if (window.__simulateReplyTimeout === 'afterResponse' && delay === 60000) {
        const timer = originalTimer(callback, delay, ...args);
        window.__fireReplyTimeout = () => { clearTimeout(timer); callback(...args); };
        return timer;
      }
      return originalTimer(callback, window.__simulateReplyTimeout === true && delay === 60000 ? 80 : delay, ...args);
    };
  ` });
  await command('Page.navigate', { url: process.env.BROWSER_APP_URL || 'http://127.0.0.1:5000/' });
  await waitUntil(ready, 'Chat did not load');
  await evaluate("document.querySelector('.new-chat').click()");
  await waitUntil("document.querySelectorAll('.row.user').length === 0", 'New chat did not open');
  chatId = await evaluate("localStorage.getItem('flamma.activeChat')");
  await send('hello');
  await waitUntil("document.querySelectorAll('.row.bot .bubble').length === 1 && !document.querySelector('.caret') && !document.querySelector('.typing')", 'Normal reply stayed loading');
  assert.equal(await evaluate(ready), true);
  assert.ok((await evaluate("document.querySelector('.row.bot .bubble').textContent")).trim().length > 0);
  console.log('Ordinary chat: reply appears and loading animation ends');

  await command('Fetch.enable', { patterns: [{ urlPattern: '*/predict', requestStage: 'Request' }] });
  await evaluate('window.__simulateReplyTimeout = true');
  await send('my skin is itchy');
  await waitUntil("document.querySelector('.history-notice')?.textContent.includes('This reply is taking too long')", 'Timeout did not show an actionable error');
  assert.equal(held.length, 1);
  assert.equal(await evaluate("!!document.querySelector('.typing')"), false);
  assert.equal(await evaluate(ready), true);
  assert.equal(await evaluate("document.querySelector('textarea').value"), 'my skin is itchy');
  const timedOutRequestId = await evaluate(`JSON.parse(sessionStorage.getItem('flamma.pendingRequest.${chatId}')).requestId`);
  const saved = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(saved.messages.length, 2, 'Stalled request duplicated the saved exchange');
  console.log('Stalled request: animation stops, draft returns, and error explains checking history');

  for (const id of held) await command('Fetch.failRequest', { requestId: id, errorReason: 'Aborted' }).catch(() => {});
  await command('Fetch.disable');
  await evaluate('window.__simulateReplyTimeout = false');
  await evaluate("document.querySelector('.history-notice button').click()");
  await waitUntil("!document.querySelector('.history-notice') && " + ready, 'Conversation could not be reloaded after timeout');
  await evaluate("document.querySelector('.send-btn').click()");
  await waitUntil("document.querySelectorAll('.row.bot .bubble').length === 2 && !document.querySelector('.caret') && !document.querySelector('.typing')", 'Chat did not recover after timeout');
  const recovered = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(recovered.messages.length, 4);
  assert.equal(recovered.messages[3].intent, 'symptom');
  assert.equal(recovered.messages[2].requestId, timedOutRequestId, 'Retry changed its request ID');
  assert.deepEqual(exceptions, []);
  console.log('Recovery: one successful exchange after reloading; no browser exceptions');

  for (const [text, intent] of [
    ['wen shud i see a docter?', 'knowledge_question'],
    ['myskin is ithcy on my elbwo', 'location'],
    ['sicne 3dasy', 'duration'],
    ['I have been using oinment for 2dasy', 'medication'],
    ['whta is psorisis?', 'knowledge_question'],
  ]) {
    const previousCount = await evaluate("document.querySelectorAll('.row.bot .bubble').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot .bubble').length === ${previousCount + 1} && !document.querySelector('.caret') && !document.querySelector('.typing')`, 'Typo reply did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, intent, text);
    assert.equal(await evaluate("[...document.querySelectorAll('.row.bot .bubble')].at(-1).textContent"), detail.messages.at(-1).text, 'Reply was partially revealed');
    if (text.includes('docter')) assert.ok(detail.messages.at(-1).text.includes('Seek medical care promptly if'));
  }
  await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(button => { if (button.textContent === 'When should I see a doctor?') button.click(); })");
  await waitUntil("document.querySelectorAll('.row.bot .bubble').length === 8 && !document.querySelector('.caret') && !document.querySelector('.typing')", 'Suggested doctor question did not finish');
  const careReply = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(careReply.messages.at(-1).intent, 'knowledge_question');
  assert.ok(careReply.messages.at(-1).text.includes('For Psoriasis:'));
  assert.deepEqual(exceptions, []);
  console.log('Typo conversation and suggested doctor question: understood; no false emergency or browser exceptions');

  for (const [text, intent] of [
    ['I have a new rash on my leg', 'new_concern'],
    ['I have no rash or itching', 'symptom_denial'],
    ['summarize our conversation', 'conversation_summary'],
  ]) {
    const count = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && !document.querySelector('.caret') && !document.querySelector('.typing')`, 'Concern or denial reply did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, intent);
  }
  await command('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await command('Page.reload');
  await waitUntil(ready, 'Conversation did not reload');
  const count = await evaluate("document.querySelectorAll('.row.bot').length");
  await send('What is contact dermatitis?');
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && ${ready}`, 'Reduced-motion reply did not arrive');
  assert.equal(await evaluate("!!document.querySelector('.caret') || !!document.querySelector('.show-full-reply')"), false);
  const fullReply = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(await evaluate("[...document.querySelectorAll('.row.bot .bubble')].at(-1).textContent"), fullReply.messages.at(-1).text);
  assert.deepEqual(exceptions, []);
  console.log('New concern, symptom denial, complete replies, and reduced-motion rendering passed');

  // Lose a response after the server commits it, then resend the restored draft.
  held.length = 0;
  const beforeLoss = await evaluate("document.querySelectorAll('.row.bot').length");
  await command('Fetch.enable', { patterns: [{ urlPattern: '*/predict', requestStage: 'Response' }] });
  await evaluate("window.__simulateReplyTimeout = 'afterResponse'");
  await send('my left wrist');
  await waitUntil("document.querySelector('.history-notice')?.textContent.includes('This reply is taking too long')", 'Lost response did not settle');
  assert.equal(held.length, 1, 'Response was not intercepted after saving');
  const lostId = await evaluate(`JSON.parse(sessionStorage.getItem('flamma.pendingRequest.${chatId}')).requestId`);
  const committed = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(committed.messages.at(-1).requestId, lostId);
  for (const id of held) await command('Fetch.failRequest', { requestId: id, errorReason: 'Aborted' }).catch(() => {});
  await command('Fetch.disable');
  await evaluate('window.__simulateReplyTimeout = false');
  await evaluate("document.querySelector('.send-btn').click()");
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${beforeLoss + 1} && ${ready}`, 'Saved-response retry did not finish');
  const replayed = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
  assert.equal(replayed.messages.length, committed.messages.length, 'Retry duplicated a committed exchange');
  assert.equal(replayed.messages.at(-1).id, committed.messages.at(-1).id);
  assert.equal(await evaluate(`sessionStorage.getItem('flamma.pendingRequest.${chatId}')`), null);
  console.log('Response lost after saving: restored draft retries with the original ID; one exchange in browser and history');

  for (const [text, intent] of [
    ['Could it be eczema or psoriasis? How do I treat it?', 'condition_clarification'],
    ['second one', 'knowledge_question'],
    ['Can I use that?', 'product_clarification'],
    ['hydrocortisone', 'product_information'],
  ]) {
    const previous = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Clarification did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, intent);
  }
  assert.deepEqual(exceptions, []);
  console.log('Ambiguous conditions and unnamed products receive clarification; choosing a condition resumes the requested topic');

  for (const [text, intent] of [
    ['I have a new rash on my arm for four days', 'new_concern'],
    ['Can I apply hydrocortisone on my face?', 'product_information'],
    ["I don't remember which cream I used", 'uncertain_answer'],
    ['What causes dermatitis, psoriasis, or rosacea?', 'condition_clarification'],
    ['the third one', 'knowledge_question'],
    ['What is triggering it?', 'knowledge_question'],
    ['Can I use that cream?', 'product_clarification'],
    ['thanks a lot', 'thanks'],
    ['I forgot its name', 'uncertain_answer'],
    ['CeraVe', 'product_information'],
    ['Can hydrocortisone cause trouble breathing?', 'safety_information'],
  ]) {
    const previous = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'English follow-up did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, intent, text);
    if (text === 'the third one') assert.ok(detail.messages.at(-1).text.includes('Rosacea'));
    if (text.includes('apply hydrocortisone')) assert.ok(detail.messages.at(-1).text.includes('cannot confirm'));
  }
  assert.deepEqual(exceptions, []);
  console.log('English medicine questions, forgotten names, courtesy, third condition choices, and educational warning questions passed');

  for (const [text, intent] of [
    ['new skin concern', 'new_concern'],
    ['My rash is on my arm for two weeks and I used a cream for three days', 'medication'],
    ['Text only', 'image_declined'],
    ['summarize our conversation', 'conversation_summary'],
    ['new skin concern', 'new_concern'],
    ['My skin is itchy', 'symptom'],
    ['My arm or leg', 'location_clarification'],
    ['both', 'location'],
    ['two days or two weeks', 'duration_clarification'],
    ['the second one', 'duration'],
    ['I used it yesterday', 'medication_clarification'],
    ['a moisturizer', 'medication'],
    ['Can I use it?', 'product_information'],
  ]) {
    const previous = await evaluate("document.querySelectorAll('.row.bot').length");
    if (text === 'Text only') {
      await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(button => { if (button.textContent === 'Text only') button.click(); })");
    } else {
      await send(text);
    }
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Contextual short answer did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, intent, text);
    if (text.startsWith('My rash is on my arm for two weeks and')) {
      assert.ok(detail.messages.at(-1).text.includes('Rash area and timeframe (your words): My rash is on my arm for two weeks'));
      assert.ok(detail.messages.at(-1).text.includes('Treatment use (your words): I used a cream for three days'));
      assert.equal(await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelector('.bubble').textContent"), detail.messages.at(-1).text);
      assert.ok(await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).textContent.includes('Choose photo')"));
    }
    if (text === 'Text only') assert.equal(detail.messages.at(-1).action, null);
    if (text === 'summarize our conversation') {
      assert.ok(detail.messages.at(-1).text.includes('How long: My rash is on my arm for two weeks\n'));
      assert.ok(detail.messages.at(-1).text.includes('Medication used: I used a cream for three days'));
    }
  }
  assert.deepEqual(exceptions, []);
  console.log('Combined rash/treatment reports, both areas, duration choices, and unknown-product usage clarification passed');

  for (const [text, intent] of [
    ['new skin concern', 'new_concern'],
    ['hello', 'greeting'],
    ['I have a rashes I think this is dermatitis', 'knowledge_question'],
    ['is it treatable?', 'knowledge_question'],
    ['is it treatable', 'knowledge_question'],
    ['What can I do next?', 'knowledge_question'],
    ['My arm', 'location'],
    ['Two weeks', 'duration'],
  ]) {
    const previous = await evaluate("document.querySelectorAll('.row.bot').length");
    if (text === 'What can I do next?') {
      await evaluate("[...document.querySelectorAll('.row.bot')].at(-1).querySelectorAll('.follow-up').forEach(button=>{if(button.textContent==='What can I do next?')button.click()})");
    } else {
      await send(text);
    }
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Concise care follow-up did not finish');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    const last = detail.messages.at(-1);
    assert.equal(last.intent, intent, text);
    if (text.startsWith('is it treatable')) {
      assert.ok(last.text.includes('Dermatitis has treatment options'));
      assert.ok(last.text.split(/\s+/).length < 55);
      assert.ok(!last.text.includes('Treatment options to discuss with a clinician:'));
    }
    if (text === 'What can I do next?') {
      assert.ok(last.text.includes('1.'));
      assert.ok(last.text.includes('Where is the affected area located?'));
      assert.ok(!last.text.includes('Dermatitis has treatment options'));
    }
  }
  assert.deepEqual(exceptions, []);
  console.log('Dermatitis conversation: brief treatability answers, distinct next-step button, and screening follow-ups passed');

  // Replay the misspelled subject change reported by the user.
  let previous = await evaluate("document.querySelectorAll('.row.bot').length");
  await send('Is it treatable');
  await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Treatability reply did not settle');
  for (const [text, intent] of [
    ['how about roscea', 'knowledge_question'],
    ['I have roscea', 'knowledge_question'],
    ['in my butt', 'location'],
    ['is it treatable?', 'knowledge_question'],
  ]) {
    previous = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${previous + 1} && ${ready}`, 'Rosacea subject switch did not settle');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    const last = detail.messages.at(-1);
    assert.equal(last.intent, intent, text);
    assert.ok(!last.text.includes('About Dermatitis'));
    if (text.startsWith('how about') || text.startsWith('is it')) {
      assert.equal(last.treatmentInfo.condition_key, 'rosacea');
      assert.ok(last.text.includes('Rosacea treatment'));
    }
    if (text === 'in my butt' || text === 'is it treatable?') assert.ok(last.text.includes('Rosacea mainly affects the face'));
  }
  assert.deepEqual(exceptions, []);
  console.log('Misspelled rosacea topic switch: correct condition, preserved brief question, and cautious location context passed');

  for (const [text, intent] of [
    ['new skin concern', 'new_concern'],
    ['My skin is itchy', 'symptom'],
    ["I don't know how long it's been there", 'uncertain_answer'],
    ['my elbow', 'location'],
    ['new skin concern', 'new_concern'],
    ['My rash is on my arm for two weeks', 'location'],
    ['I used a cream for three days', 'medication'],
    ['It is getting better today', 'symptom_update'],
    ['The itching has stopped', 'symptom_update'],
    ['summarize our conversation', 'conversation_summary'],
    ["I haven't treated my swollen lips", 'emergency'],
  ]) {
    const count = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && ${ready}`, 'Progress or uncertainty reply did not settle');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    const last = detail.messages.at(-1);
    assert.equal(last.intent, intent, text);
    if (intent === 'uncertain_answer') assert.ok(last.text.includes('Where is the affected area located?'));
    if (intent === 'conversation_summary') {
      assert.ok(last.text.includes('How long: My rash is on my arm for two weeks'));
      assert.ok(last.text.includes("Changes you've reported (your words): It is getting better today"));
      assert.ok(last.text.includes("Changes you've reported (your words): The itching has stopped"));
    }
    if (intent === 'emergency') assert.equal(last.treatmentInfo, undefined);
  }
  assert.deepEqual(exceptions, []);
  console.log('Specific uncertainty, progress updates, original rash duration, summaries, and treatment-negation warning routing passed');

  for (const [text, intent] of [
    ['new skin concern', 'new_concern'],
    ['It stings', 'symptom'],
    ['around my bellybutton', 'location'],
    ['twenty-one days', 'duration'],
    ['It is bothersome', 'severity'],
    ['Is contactdermatitis treatable', 'knowledge_question'],
    ['and roseaca', 'knowledge_question'],
    ['same question for psoriosis', 'knowledge_question'],
    ['Could you put that in plain English', 'simple_explanation'],
    ['Please hold off on the questions', 'screening_pause'],
    ['Could we carry on with the screening', 'screening_resume'],
    ['Could you give me the gist of our conversation', 'conversation_summary'],
  ]) {
    const count = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && ${ready}`, 'Expanded vocabulary reply did not settle');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    const last = detail.messages.at(-1);
    assert.equal(last.intent, intent, text);
    if (text === 'and roseaca') assert.equal(last.treatmentInfo.condition_key, 'rosacea');
    if (text === 'same question for psoriosis') assert.equal(last.treatmentInfo.condition_key, 'psoriasis');
    if (intent === 'conversation_summary') {
      assert.ok(last.text.includes('around my bellybutton'));
      assert.ok(last.text.includes('twenty-one days'));
    }
  }
  assert.deepEqual(exceptions, []);
  console.log('Expanded English vocabulary: symptom, body area, written duration, severity, condition switches, and polite commands passed');

  for (const [text, intent] of [
    ['new skin concern', 'new_concern'],
    ['My rash is on my arm for two weeks', 'location'],
    ['Actually, twenty-one days, not two weeks', 'correction'],
    ['Actually, my upper back, not my lower back', 'correction'],
    ['The rash has cleared up today', 'symptom_update'],
    ['The rash has come back today', 'symptom_update'],
    ['Summarize our conversation', 'conversation_summary'],
    ['new skin concern', 'new_concern'],
    ['My skin is itchy', 'symptom'],
    ['my upper back or my lower back', 'location_clarification'],
    ['second one', 'location'],
    ['two nights or twenty days', 'duration_clarification'],
    ['second one', 'duration'],
    ['Summarize our conversation', 'conversation_summary'],
  ]) {
    const count = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && ${ready}`, 'Correction or progress reply did not settle');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    const last = detail.messages.at(-1);
    assert.equal(last.intent, intent, text);
    if (intent === 'location_clarification') {
      assert.ok(last.followUps.includes('upper back'));
      assert.ok(last.followUps.includes('lower back'));
    }
    if (intent === 'duration_clarification') assert.ok(last.followUps.includes('twenty days'));
    if (intent === 'conversation_summary') {
      if (last.text.includes('Changes you')) {
        assert.ok(last.text.includes('Affected area: upper back'));
        assert.ok(last.text.includes('How long: twenty-one days'));
        assert.ok(last.text.includes("Changes you've reported (your words): The rash has come back today"));
      } else {
        assert.ok(last.text.includes('Affected area: lower back'));
        assert.ok(last.text.includes('How long: twenty days'));
      }
    }
  }
  assert.deepEqual(exceptions, []);
  console.log('Complete timeframe corrections, qualified body areas, explicit choices, recurrence, and original onset passed');

  await evaluate("document.querySelector('.prototype-info').open = true");
  const disclosure = await evaluate("document.querySelector('.prototype-info').textContent");
  assert.ok(disclosure.includes('Flamma server'));
  assert.ok(disclosure.includes('does not encrypt'));
  assert.ok(disclosure.includes('not disease probabilities'));
  await evaluate("document.querySelector('.prototype-info').open = false");
  const scoreLabels = await evaluate("[...document.querySelectorAll('.confidence')].map(e=>e.textContent)");
  assert.ok(scoreLabels.some(text => text.includes('Message intent score:')));
  for (const [text, phrase] of [
    ['What does 94.6% accuracy mean?', 'does not measure diagnostic accuracy'],
    ['Who can access my photos?', 'server files'],
    ['Are my photos encrypted?', 'not encrypted by this app'],
  ]) {
    const count = await evaluate("document.querySelectorAll('.row.bot').length");
    await send(text);
    await waitUntil(`document.querySelectorAll('.row.bot').length === ${count + 1} && ${ready}`, 'Prototype explanation did not settle');
    const detail = await evaluate(`fetch('/api/conversations/${chatId}').then(r=>r.json())`);
    assert.equal(detail.messages.at(-1).intent, 'bot_identity');
    assert.ok(detail.messages.at(-1).text.includes(phrase));
  }
  assert.deepEqual(exceptions, []);
  console.log('Visible score meaning, prototype disclosure, server storage, and privacy limitations passed');
  await command('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await evaluate("document.querySelector('.prototype-info').open = true");
  assert.ok(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Prototype disclosure or scores overflow a mobile viewport');
  assert.ok(await evaluate("document.querySelector('.prototype-info summary').getBoundingClientRect().width > 0"));
  console.log('Mobile layout: prototype disclosure and score labels remain within the viewport');
} finally {
  if (chatId) await evaluate(`fetch('/api/conversations/${chatId}',{method:'DELETE'}).then(r=>r.json())`).catch(() => {});
  await command('Browser.close').catch(() => {});
  socket.close();
}
