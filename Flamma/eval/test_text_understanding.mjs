import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import cases from './language_cases.json' with { type: 'json' };
import { normalizeMessage, isPhotoUploadRequest } from '../static/text-normalizer.js';

test('browser and backend normalize the regression corpus identically', () => {
  const texts = [...cases.map(item => item.message), 'I’m not shure!!', '2.5wks', 'Tacrolimus 0.1% ointment', 'I already sent an image', 'i dunno'];
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c', 'import json,sys; from model.text_understanding import normalize_message; print(json.dumps([normalize_message(x) for x in json.load(sys.stdin)]))'], {
    input: JSON.stringify(texts), encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(texts.map(normalizeMessage), JSON.parse(result.stdout));
});

test('upload request detection recognizes common typos', () => {
  for (const text of ['can i sent pictuer', 'pls let me uplod a phto', 'I want to upload an imgae', 'let me sendpic']) {
    assert.equal(isPhotoUploadRequest(text), true, text);
  }
});

test('negation, emergencies and past uploads do not trigger the photo picker', () => {
  for (const text of ['I dont want to uplod a phto', 'I cant send pictuer', 'I wont upload an image', 'I already sent an image', 'i cant breath can i sent pictuer']) {
    assert.equal(isPhotoUploadRequest(text), false, text);
  }
});

test('questions about an existing photo do not open the picker', () => {
  for (const text of ['what do you think in that images', 'i mean what is your thoiughts about it', 'what does the photo show?', 'look at the photo i already sent', 'can you explain the image I uploaded']) {
    assert.equal(isPhotoUploadRequest(text), false, text);
  }
  assert.equal(isPhotoUploadRequest('can I send another photo and get your thoughts about it?'), true);
});
