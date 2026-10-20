import assert from 'node:assert/strict';
import test from 'node:test';
import { formatChatExport } from '../frontend/src/chat-export.js';

test('export keeps the reply, photo marker, medical sources, and source date together', () => {
  const text = formatChatExport({ title: 'Skin concern', messages: [
    { who: 'user', text: 'My skin concern', image: '/private/local-photo' },
    { who: 'bot', text: 'General care; a screening result is not a diagnosis.', treatmentInfo: {
      source_checked_on: '2026-10-14', sources: [{title:'AAD: Treatment', url:'https://www.aad.org/treatment'}],
    } },
  ] });
  assert.ok(text.includes('You\nMy skin concern\n[Attached photo]'));
  assert.ok(text.includes('Flamma\nGeneral care; a screening result is not a diagnosis.'));
  assert.ok(text.includes('AAD: Treatment: https://www.aad.org/treatment'));
  assert.ok(text.includes('Sources checked: 2026-10-14'));
  assert.ok(!text.includes('/private/local-photo'));
});

test('older saved chats without treatment metadata still export normally', () => {
  assert.equal(formatChatExport({title:'Chat',messages:[{who:'user',text:'hello'},{who:'bot',text:'Hello.'}]}),
    'Chat\n\nYou\nhello\n\nFlamma\nHello.');
});

test('combined course and care references retain each source check date', () => {
  const text = formatChatExport({ title: 'Course and care', messages: [{
    who: 'bot', text: 'General course and care information.', treatmentInfo: {
      source_checked_on: null, sources: [
        {title:'Course',url:'https://example.org/course',source_checked_on:'2026-10-16'},
        {title:'Care',url:'https://example.org/care',source_checked_on:'2026-10-14'},
      ],
    },
  }] });
  assert.ok(text.includes('https://example.org/course (checked 2026-10-16)'));
  assert.ok(text.includes('https://example.org/care (checked 2026-10-14)'));
  assert.ok(!text.includes('Sources checked: null'));
});
