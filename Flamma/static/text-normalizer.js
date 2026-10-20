import language from './chat-language.json' with { type: 'json' };

export function normalizeMessage(message) {
  return message.normalize('NFKC').toLowerCase().replaceAll('’', "'").replaceAll('\u2018', "'").replaceAll('\u200b', '')
    .replace(/[a-z]+(?:'[a-z]+)?/g, word => language.word_aliases[word] ?? word)
    .replace(/\b(\d+(?:\.\d+)?|one|two|three|four|five|six|a|several|few)\s+(weaks?)\b/g,
      (_, quantity, unit) => `${quantity} ${unit.endsWith('s') ? 'weeks' : 'week'}`)
    .replace(/\b(\d+(?:\.\d+)?)\s*-?\s*(weeks?|days?|months?|hours?|years?|minutes?)\b/g, '$1 $2')
    .replace(/\bhi{2,}\b/g, 'hi').replace(/\bhe+l{2,}o+\b/g, 'hello').replace(/\bhey+\b/g, 'hey')
    .replace(/\b(can|could|may) i (sent|sending)\b/g, '$1 i send')
    .replace(/\b(want|like|need) to (sent|sending)\b/g, '$1 to send')
    .replace(/\bwhat (this|it|that) mean\b/g, 'what does $1 mean')
    .replace(/\b(cannot|could not) breath\b/g, '$1 breathe')
    .replace(/\bi i do not know\b/g, 'i do not know')
    .replace(/\b(should|could|can|must) i c (?=(?:a |the )?(?:doctor|dermatologist)\b)/g, '$1 i see ')
    .replace(/\s+/g, ' ').trim();
}

export function isPhotoUploadRequest(message) {
  const text = normalizeMessage(message);
  const photo = /\b(picture|pictures|photo|photos|image|images|pic|pics)\b/.test(text);
  const action = /\b(send|upload|attach|share|show|submit|sending|uploading|attaching)\b/.test(text);
  const declined = /\b(do not want to|will not|not going to|cannot (?:send|upload)|could not (?:send|upload))\b/.test(text);
  const urgent = /\b(breathing|breathe|throat swelling|lips are swollen|face is swelling|chest feels tight|chest is tight)\b/.test(text);
  const clean = text.replace(/[?!.,]+$/, '');
  const reference = /\b(picture|pictures|photo|photos|image|images|pic|pics|result|results|it|this|that|these|those|heatmap)\b/.test(clean);
  const question = language.photo_result_questions.includes(clean) || (reference && language.photo_question_phrases.some(phrase => clean.includes(phrase)));
  const explicitRequest = /\b(?:(?:can|could|may) i|i (?:want|would like|need) to|let me|i am going to) (?:send|upload|attach|share|show|submit)\b/.test(clean);
  return photo && action && !declined && !urgent && (!question || explicitRequest);
}
