import assert from 'node:assert/strict';
import test from 'node:test';
import { fetchJson, RequestTimeoutError } from '../frontend/src/request.js';

test('a stuck request stops waiting and aborts the transport', async (t) => {
  let signal;
  t.mock.method(globalThis, 'fetch', (_, options) => {
    signal = options.signal;
    return new Promise(() => {});
  });
  await assert.rejects(fetchJson('/predict', {}, 10), RequestTimeoutError);
  assert.equal(signal.aborted, true);
});

test('a stuck JSON body is also bounded by the timeout', async (t) => {
  let signal;
  t.mock.method(globalThis, 'fetch', async (_, options) => {
    signal = options.signal;
    return { json: () => new Promise(() => {}) };
  });
  await assert.rejects(fetchJson('/predict', {}, 10), RequestTimeoutError);
  assert.equal(signal.aborted, true);
});

test('successful replies preserve the request and cancel the timer', async (t) => {
  let signal;
  const body = new FormData();
  body.append('message', 'hello');
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    assert.equal(path, '/predict');
    assert.equal(options.method, 'POST');
    assert.equal(options.body, body);
    signal = options.signal;
    return new Response(JSON.stringify({ reply: 'Hello' }), { status: 200 });
  });
  const result = await fetchJson('/predict', { method: 'POST', body }, 10);
  assert.deepEqual(result.data, { reply: 'Hello' });
  await new Promise(resolve => setTimeout(resolve, 20));
  assert.equal(signal.aborted, false);
});

test('a saved error reply remains available for the chat interface', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ reply: 'Image unavailable', conversation: { id: 'one' } }), { status: 503 }));
  const result = await fetchJson('/predict');
  assert.equal(result.response.status, 503);
  assert.equal(result.data.conversation.id, 'one');
});

test('malformed JSON and connection failures settle immediately', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('invalid JSON'));
  await assert.rejects(fetchJson('/predict'), SyntaxError);
  globalThis.fetch.mock.mockImplementation(async () => { throw new TypeError('Network error'); });
  await assert.rejects(fetchJson('/predict'), TypeError);
});
