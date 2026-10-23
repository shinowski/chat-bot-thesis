import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import policy from '../static/reply-choices.json' with { type: 'json' };
import { getReplyChoices } from '../static/reply-choices.js';

const messages = [
  ...Object.keys(policy.intentContexts).map(intent => ({ who: 'bot', intent, followUps: [] })),
  ...Object.keys(policy.contexts).map(choiceContext => ({ who: 'bot', choiceContext })),
  { intent: 'image_request', action: 'upload_image', followUps: ['Choose photo', 'choose photo', 'Text only'] },
  { intent: 'symptom', text: 'Where is the affected area located?' },
  { intent: 'location', text: "I've noted that. How long have you had this problem?" },
  { intent: 'condition_clarification', followUps: ['Dermatitis', 'Psoriasis'] },
  { intent: 'greeting', followUps: [' Rash ', 'rash', null, 12, '', 'Upload a photo'] },
  { intent: 'emergency', action: 'upload_image', followUps: ['Choose photo', 'Continue screening'] },
  { intent: 'future_intent', followUps: [] },
  { intent: 'constructor', choiceContext: '__proto__' },
];

test('all reply contexts have at least three distinct usable choices', () => {
  for (const message of messages) {
    const choices = getReplyChoices(message);
    assert.ok(choices.length >= 3, JSON.stringify(message));
    assert.equal(new Set(choices.map(choice => choice.toLowerCase())).size, choices.length);
    assert.ok(choices.every(choice => typeof choice === 'string' && choice.trim() === choice && choice));
  }
});

test('browser and server produce the same choices for live, old, and malformed messages', () => {
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c',
    'import json,sys; from model.reply_choices import with_reply_choices; print(json.dumps([with_reply_choices(m)["followUps"] for m in json.load(sys.stdin)]))'],
  { input: JSON.stringify(messages), encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  assert.deepEqual(messages.map(getReplyChoices), JSON.parse(result.stdout));
});

test('picker choice appears once and old questions keep their actual answer options', () => {
  assert.deepEqual(getReplyChoices({ intent: 'image_request', action: 'upload_image' }),
    ['Choose photo', 'Text only', 'Summarize our conversation']);
  assert.deepEqual(getReplyChoices({ intent: 'symptom', text: 'Where is the affected area located?' }),
    ['My arm', 'My face', "I'm not sure"]);
  assert.deepEqual(getReplyChoices({ who: 'user', text: 'hello' }), []);
});

test('warning choices cannot suggest uploads or continuing the screening questionnaire', () => {
  const choices = getReplyChoices({ intent: 'emergency', action: 'upload_image', followUps: ['Choose photo'] });
  assert.ok(!choices.includes('Choose photo'));
  assert.ok(!choices.includes('Continue screening'));
  assert.ok(choices.includes('When should I see a doctor?'));
});
