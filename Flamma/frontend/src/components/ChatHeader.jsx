export default function ChatHeader({ title, lastIntent, lastConfidence, confidenceSource, onMenuClick }) {
  const pillText =
    lastIntent
      ? `intent: ${lastIntent}${typeof lastConfidence === 'number' ? ` (${(lastConfidence * 100).toFixed(1)}%)` : ''}`
      : 'intent: —';

  return (
    <div className="chat-header">
      <div className="header-left">
        <button className="menu-btn" onClick={onMenuClick} aria-label="Toggle sidebar">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M2 5H16M2 9H16M2 13H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <div>
          <div className="chat-title">{title}</div>
          <div className="chat-sub">Describe what you're noticing — I'll ask a few follow-ups</div>
        </div>
      </div>
      <div className="model-pill" title={confidenceSource === 'image_model' ? 'Image model confidence' : 'Text intent; percentages appear only when the model prediction matches the reply intent'}>{pillText}</div>
    </div>
  );
}
