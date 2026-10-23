import policy from './reply-choices.json' with { type: 'json' };

export const PHOTO_CHOICE = policy.photoChoice;

export function replyChoiceContext(message) {
  const intent = message.intent || '';
  if (policy.intentContexts[intent] === 'safety') return 'safety';
  if (Object.hasOwn(policy.contexts, message.choiceContext)) return message.choiceContext;
  if (message.action === 'upload_image') return 'upload';
  const ending = (message.reply || message.text || '').split(/\n\s*\n/).at(-1);
  if (ending.includes('?')) {
    for (const rule of policy.questionRules) {
      if (new RegExp(rule.pattern, 'i').test(ending)) return rule.context;
    }
  }
  return Object.hasOwn(policy.intentContexts, intent) ? policy.intentContexts[intent]
    : Object.hasOwn(policy.contexts, intent) ? intent : 'default';
}

export function getReplyChoices(message) {
  if (message.who === 'user') return [];
  const context = replyChoiceContext(message);
  const existing = context !== 'safety' && Array.isArray(message.followUps) ? message.followUps : [];
  const choices = [], seen = new Set();
  const append = (value) => {
    if (typeof value !== 'string' || !value.trim() || seen.has(value.trim().toLowerCase())) return;
    choices.push(value.trim()); seen.add(value.trim().toLowerCase());
  };
  if (message.action === 'upload_image' && context !== 'safety') append(PHOTO_CHOICE);
  existing.forEach(append);
  for (const value of [...policy.contexts[context], ...policy.contexts.default]) {
    if (choices.length >= policy.minimum) break;
    append(value);
  }
  return choices;
}
