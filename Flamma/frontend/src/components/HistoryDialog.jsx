import { useEffect, useRef, useState } from 'react';

export default function HistoryDialog({ action, busy, onClose, onConfirm }) {
  const ref = useRef(null);
  const [title, setTitle] = useState(action.chat?.title || '');
  const rename = action.type === 'rename';
  const clear = action.type === 'clear';
  useEffect(() => { if (!ref.current.open) ref.current.showModal(); }, []);
  return (
    <dialog className="history-dialog" ref={ref} aria-labelledby="history-dialog-title"
      onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
      <form onSubmit={(event) => { event.preventDefault(); if (!busy) onConfirm(title.trim()); }}>
        <h2 id="history-dialog-title">{rename ? 'Rename conversation' : clear ? 'Clear all history?' : 'Delete conversation?'}</h2>
        {rename ? <label>Conversation name<input autoFocus value={title} onChange={(event) => setTitle(event.target.value)}
          maxLength={100} required disabled={busy} /></label>
          : <p>{clear ? 'This removes all your saved conversations and photos.' : `“${action.chat.title}” and its photos will be removed.`} This cannot be undone.</p>}
        {action.error && <p className="dialog-error" role="alert">{action.error}</p>}
        <div className="dialog-actions">
          <button type="button" onClick={onClose} disabled={busy} autoFocus={!rename}>Cancel</button>
          <button className={rename ? 'primary' : 'danger'} disabled={busy || (rename && !title.trim())}>
            {busy ? 'Saving…' : rename ? 'Save name' : clear ? 'Clear history' : 'Delete'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
