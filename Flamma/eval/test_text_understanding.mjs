import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import cases from './language_cases.json' with { type: 'json' };
import vocabularyCases from './vocabulary_cases.json' with { type: 'json' };
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

test('new English shorthand stays consistent with the backend and preserves medicine names', () => {
  const texts = ['how abt tretment', 'my skin is flaky lately', 'the diference between ecsema and psoriassis',
    'roughly a fortnight', 'Tacrolimus 0.1% ointment'];
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c',
    'import json,sys; from model.text_understanding import normalize_message; print(json.dumps([normalize_message(x) for x in json.load(sys.stdin)]))'], {
    input: JSON.stringify(texts), encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(texts.map(normalizeMessage), JSON.parse(result.stdout));
});

test('expanded typos, shorthand and curly apostrophes normalize consistently', () => {
  const texts = ['wen shud i see a docter?', 'whn shld i c a dr?', 'myskin is ithcy on my elbwo',
    'sicne 3dasy', 'I have been using oinment for 2dasy', 'i cant brethe', 'my thorat is swolen',
    'i dnt have truble brething', 'whta is psorisis?', 'and treatmnt?',
    'I\u2019m not having truble brething', 'I\u2018m not having truble brething',
    'Nivolumab acetaminophen vitamin C armchair'];
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c',
    'import json,sys; from model.text_understanding import normalize_message; print(json.dumps([normalize_message(x) for x in json.load(sys.stdin)]))'], {
    input: JSON.stringify(texts), encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(texts.map(normalizeMessage), JSON.parse(result.stdout));
  assert.equal(normalizeMessage('wen shud i see a docter?'), 'when should i see a doctor?');
  assert.equal(normalizeMessage('i dnt have truble brething'), 'i do not have trouble breathing');
});

test('rosacea spelling corrections match the backend and preserve unlisted drug names', () => {
  const texts = ['how about roscea', 'I have roscea', 'rosecea rosace', 'Nivolumab 5 mg rosceazole'];
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c',
    'import json,sys; from model.text_understanding import normalize_message; print(json.dumps([normalize_message(x) for x in json.load(sys.stdin)]))'], {
    input: JSON.stringify(texts), encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(texts.map(normalizeMessage), JSON.parse(result.stdout));
  assert.equal(normalizeMessage('how about roscea'), 'how about rosacea');
  assert.equal(normalizeMessage('Nivolumab 5 mg rosceazole'), 'nivolumab 5 mg rosceazole');
});

test('expanded vocabulary has matching normalization and preserves weak, names, numbers and negation', () => {
  const texts = [...vocabularyCases.flatMap(item => item.turns.map(turn => turn.text)),
    "I'd rather chat without a picture", "My lips haven't swollen", 'I feel weak',
    'two weaks', 'Fortnite is a game', 'Nivolumab Xylarose rosceazole 0.05% 2.5 mg'];
  const result = spawnSync('venv/Scripts/python.exe', ['-X', 'utf8', '-B', '-c',
    'import json,sys; from model.text_understanding import normalize_message; print(json.dumps([normalize_message(x) for x in json.load(sys.stdin)]))'], {
    input: JSON.stringify(texts), encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(texts.map(normalizeMessage), JSON.parse(result.stdout));
  assert.equal(normalizeMessage('I feel weak'), 'i feel weak');
  assert.equal(normalizeMessage('two weaks'), 'two weeks');
  assert.equal(normalizeMessage("My lips haven't swollen"), 'my lips have not swollen');
  assert.equal(normalizeMessage('Nivolumab Xylarose rosceazole 0.05% 2.5 mg'),
    'nivolumab xylarose rosceazole 0.05% 2.5 mg');
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
