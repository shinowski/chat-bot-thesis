// Persist only IDs and hashes. Chat text and photo bytes are kept out of storage.
export class RetryRequests {
  constructor(storage) {
    try { this.storage = storage ?? globalThis.sessionStorage; } catch { this.storage = null; }
    this.pending = new Map();
  }
  key(chatId) { return `flamma.pendingRequest.${chatId}`; }
  get(chatId) {
    if (this.pending.has(chatId)) return this.pending.get(chatId);
    try {
      const record = JSON.parse(this.storage?.getItem(this.key(chatId)) || 'null');
      if (record?.requestId && record?.fingerprint) return record;
    } catch { /* storage is optional */ }
    return null;
  }
  async forPayload(chatId, text, image = null) {
    const header = new TextEncoder().encode(JSON.stringify([text.trim(), image?.name ?? null]) + '\n');
    const bytes = image ? new Uint8Array(await image.arrayBuffer()) : new Uint8Array();
    const combined = new Uint8Array(header.length + bytes.length);
    combined.set(header); combined.set(bytes, header.length);
    const fingerprint = [...new Uint8Array(await crypto.subtle.digest('SHA-256', combined))]
      .map(value => value.toString(16).padStart(2, '0')).join('');
    const previous = this.get(chatId);
    const record = { requestId: previous?.fingerprint === fingerprint ? previous.requestId : crypto.randomUUID(), fingerprint };
    this.pending.set(chatId, { ...record, image });
    try { this.storage?.setItem(this.key(chatId), JSON.stringify(record)); } catch { /* in-memory retries still work */ }
    return record;
  }
  clear(chatId, requestId) {
    const record = this.get(chatId);
    if (!record || (requestId && record.requestId !== requestId)) return;
    this.pending.delete(chatId);
    try { this.storage?.removeItem(this.key(chatId)); } catch { /* optional */ }
  }
  reconcile(chatId, messages) {
    const record = this.get(chatId);
    if (!record || !messages.some(message => message.who === 'bot' && message.requestId === record.requestId)) return null;
    this.clear(chatId, record.requestId);
    return record;
  }
  clearAll() {
    this.pending.clear();
    try {
      const keys = [];
      for (let i = 0; i < this.storage.length; i++) {
        const key = this.storage.key(i);
        if (key?.startsWith('flamma.pendingRequest.')) keys.push(key);
      }
      for (const key of keys) this.storage.removeItem(key);
    } catch { /* optional storage */ }
  }
}

export function mergeSavedExchange(messages, optimisticId, saved) {
  const replaced = new Set([optimisticId, ...saved.map(message => message.id)]);
  const alreadyShown = messages.some(message => message.id === saved[1].id);
  if (alreadyShown) return messages.filter(message => message.id !== optimisticId);
  return [...messages.filter(message => !replaced.has(message.id)), ...saved];
}
