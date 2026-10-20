import assert from 'node:assert/strict';
import test from 'node:test';
import { RetryRequests, mergeSavedExchange } from '../frontend/src/retry-requests.js';

function storage() {
  const data = new Map();
  return { get length() {return data.size;}, key: i=>[...data.keys()][i], getItem: key=>data.get(key)??null,
    setItem: (key,value)=>data.set(key,value), removeItem: key=>data.delete(key) };
}
function image(name, content) { return {name, arrayBuffer:async()=>new TextEncoder().encode(content).buffer}; }

test('identical retries retain their ID until a saved receipt confirms completion', async()=>{
  const retries = new RetryRequests(storage());
  const first = await retries.forPayload('a', 'my skin is itchy');
  assert.equal((await retries.forPayload('a','my skin is itchy')).requestId, first.requestId);
  retries.clear('a', first.requestId);
  assert.notEqual((await retries.forPayload('a','my skin is itchy')).requestId, first.requestId);
});
test('retry IDs survive reload without storing health text or photo bytes', async()=>{
  const saved = storage();
  const first = await new RetryRequests(saved).forPayload('a','private rash',image('skin.png','private photo'));
  const value = saved.getItem('flamma.pendingRequest.a');
  assert.ok(!value.includes('private'));
  assert.ok(!value.includes('skin.png'));
  assert.equal((await new RetryRequests(saved).forPayload('a','private rash',image('skin.png','private photo'))).requestId,first.requestId);
});
test('changed text, photo content, filename, or chat produces a different ID', async()=>{
  const retries = new RetryRequests(storage());
  const original = await retries.forPayload('a','hello',image('a.png','photo'));
  for (const [chat,text,file] of [['a','changed',image('a.png','photo')],['a','hello',image('a.png','changed')],['a','hello',image('b.png','photo')],['b','hello',image('a.png','photo')]]) {
    assert.notEqual((await retries.forPayload(chat,text,file)).requestId, original.requestId);
  }
});
test('history reconciliation clears only the confirmed pending request', async()=>{
  const retries = new RetryRequests(storage());
  const first = await retries.forPayload('a','hello');
  assert.equal(retries.reconcile('a',[{who:'bot',requestId:'another'}]),null);
  assert.equal(retries.reconcile('a',[{who:'bot',requestId:first.requestId}]).requestId,first.requestId);
  assert.equal(retries.get('a'),null);
});
test('an old completed request does not clear a newer pending request', async()=>{
  const retries = new RetryRequests(storage());
  const first = await retries.forPayload('a','hello');
  const second = await retries.forPayload('a','new message');
  retries.clear('a',first.requestId);
  assert.equal(retries.get('a').requestId,second.requestId);
});
test('replayed exchanges do not duplicate or reorder messages already in history', ()=>{
  const saved = [{id:'u1',who:'user'},{id:'b1',who:'bot'}];
  const existing = [...saved,{id:'u2'},{id:'b2'},{id:'optimistic'}];
  assert.deepEqual(mergeSavedExchange(existing,'optimistic',saved,true),existing.slice(0,4));
  const inserted = mergeSavedExchange([{id:'optimistic'}],'optimistic',saved,true);
  assert.deepEqual(inserted.map(message=>message.id),['u1','b1']);
});
test('clear history removes retry metadata and preserves unrelated storage',async()=>{
  const saved=storage(); saved.setItem('unrelated','value');
  const retries=new RetryRequests(saved); await retries.forPayload('a','hello'); await retries.forPayload('b','another');
  retries.clearAll(); assert.equal(saved.length,1); assert.equal(saved.getItem('unrelated'),'value');
});
test('denied session storage still supports retries within this page',async()=>{
  const denied={getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}};
  const retries=new RetryRequests(denied); const first=await retries.forPayload('a','hello');
  assert.equal((await retries.forPayload('a','hello')).requestId,first.requestId);
});
