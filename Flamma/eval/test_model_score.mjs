import assert from 'node:assert/strict';
import test from 'node:test';
import { modelScore, formatModelPercent } from '../frontend/src/model-score.js';

test('text matching and photo scores have distinct visible meanings', () => {
  assert.equal(modelScore(.97, 'intent_model').label, 'Message intent score');
  assert.equal(modelScore(.88, 'image_model').label, 'Photo model score');
  assert.ok(modelScore(.97, 'intent_model').explanation.includes('not medical accuracy'));
  assert.ok(modelScore(.88, 'image_model').explanation.includes('not a diagnosis'));
  assert.equal(modelScore(0, 'intent_model').percent, '0%');
  assert.equal(modelScore(1, 'image_model').percent, '100%');
});

test('invalid and historical unsourced scores cannot appear as meaningful percentages', () => {
  for (const value of [null, undefined, NaN, Infinity, -0.1, 1.1, '0.97']) {
    assert.equal(modelScore(value, 'intent_model'), null);
  }
  assert.equal(modelScore(.97, undefined), null);
  assert.equal(modelScore(.97, 'unknown'), null);
});

test('scores preserve decimals and do not round non-extreme values into certainty', () => {
  assert.equal(modelScore(.997, 'image_model').percent, '99.7%');
  assert.equal(formatModelPercent(.999999), '>99.9%');
  assert.equal(formatModelPercent(.000001), '<0.1%');
  assert.equal(formatModelPercent(.88), '88%');
  assert.equal(formatModelPercent(0), '0%');
  assert.equal(formatModelPercent(1), '100%');
});
