import { useEffect, useState } from 'react';

function dateGroup(date) {
  if (!date) return 'New conversation';
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const time = new Date(date);
  if (time >= today) return 'Today';
  if (time >= yesterday) return 'Yesterday';
  return 'Earlier';
}
function Highlight({ text = '', query }) {
  const index = text.toLowerCase().indexOf(query.trim().toLowerCase());
  if (!query.trim() || index < 0) return text;
  return <>{text.slice(0, index)}<mark>{text.slice(index, index + query.trim().length)}</mark>{text.slice(index + query.trim().length)}</>;
}

export default function Sidebar({ conversations, activeId, onSelect, onNewChat, open, onClose,
  query, onSearch, searchResults, searchError, onAction, disabled, loading }) {
  const [menu, setMenu] = useState(null);
  useEffect(() => {
    function close(event) {
      if (event.type === 'keydown' && event.key !== 'Escape') return;
      if (event.type === 'pointerdown' && event.target.closest('.history-actions')) return;
      setMenu(null);
    }
    document.addEventListener('pointerdown', close); document.addEventListener('keydown', close);
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close); };
  }, []);
  const searching = !!query.trim();
  const list = searching ? (searchResults || []).map((c) => ({
    ...(conversations.find((local) => local.id === c.id) || { ...c, saved: true }), match: c.match,
  })) : [...conversations];
  list.sort((a, b) => (b.updatedAt || '9999').localeCompare(a.updatedAt || '9999'));
  let lastGroup;
  function action(type, chat) { setMenu(null); onAction(type, chat); }
  return (
    <>
      {open && <div className="scrim" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'open' : ''}`} aria-label="Conversation history">
        <div className="brand"><span className="brand-mark" /><span className="brand-name">Flamma</span></div>
        <button className="new-chat" onClick={onNewChat} disabled={loading}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 1V13M1 7H13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          New conversation
        </button>
        <div className="history-search">
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.5" /><path d="m12 12 5 5" stroke="currentColor" strokeWidth="1.5" /></svg>
          <input type="search" aria-label="Search conversations" placeholder="Search conversations" value={query}
            onChange={(event) => onSearch(event.target.value)} disabled={loading} />
        </div>
        <div className="history-label">{searching ? 'Search results' : 'Your conversations'}</div>
        <nav className="history" aria-label="Saved conversations">
          {loading ? <p className="history-empty">Loading history…</p>
            : searching && !searchResults && !searchError ? <p className="history-empty" role="status">Searching…</p>
            : searchError ? <p className="history-empty" role="alert">{searchError}</p>
            : !list.length ? <p className="history-empty">{searching ? 'No conversations found. Try a different word.' : 'Your chats will appear here.'}</p> : null}
          {list.map((chat) => {
            const group = dateGroup(chat.updatedAt);
            const showGroup = !searching && group !== lastGroup;
            lastGroup = group;
            const match = searching ? chat.match || chat.preview || '' : chat.preview || 'No messages yet';
            const index = match.toLowerCase().indexOf(query.trim().toLowerCase());
            const preview = searching && index > 25 ? '…' + match.slice(index - 25) : match;
            return <div key={chat.id}>
              {showGroup && <div className="history-date">{group}</div>}
              <div className={'history-item' + (chat.id === activeId ? ' active' : '')}>
                <button className="history-select" data-conversation-id={chat.id} onClick={() => onSelect(chat.id)} aria-current={chat.id === activeId ? 'page' : undefined} title={chat.title}>
                  <span className="t"><Highlight text={chat.title} query={query} /></span>
                  <span className="s" title={match}><Highlight text={preview} query={query} /></span>
                </button>
                {chat.saved && <div className="history-actions">
                  <button className="history-menu-toggle" aria-label={`Actions for ${chat.title}`} aria-expanded={menu === chat.id}
                    onClick={() => setMenu(menu === chat.id ? null : chat.id)} disabled={disabled}>···</button>
                  {menu === chat.id && <div className="history-menu">
                    <button onClick={() => action('rename', chat)}>Rename</button>
                    <button onClick={() => action('export', chat)}>Export text</button>
                    <button className="delete-action" onClick={() => action('delete', chat)}>Delete</button>
                  </div>}
                </div>}
              </div>
            </div>;
          })}
        </nav>
        <div className="sidebar-footer">
          <button className="clear-history" onClick={() => action('clear')} disabled={disabled || !conversations.some((c) => c.saved)}>Clear history</button>
          <div className="sidebar-foot"><span className="dot-live" />History saved on this computer</div>
        </div>
      </aside>
    </>
  );
}
