export default function Sidebar({ conversations, activeId, onSelect, onNewChat, open, onClose }) {
  return (
    <>
      {open && <div className="scrim" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark"></span>
          <span className="brand-name">Flamma</span>
        </div>

        <button className="new-chat" onClick={onNewChat}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1V13M1 7H13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          New conversation
        </button>

        <div className="history-label">Recent</div>
        <div className="history">
          {[...conversations].reverse().map((c) => (
            <div
              key={c.id}
              className={'history-item' + (c.id === activeId ? ' active' : '')}
              onClick={() => onSelect(c.id)}
            >
              <div className="t">{c.title}</div>
              <div className="s">{c.preview || 'No messages yet'}</div>
            </div>
          ))}
        </div>

        <div className="sidebar-foot">
          <span className="dot-live"></span> dev build · rule-based engine
        </div>
      </aside>
    </>
  );
}
