import { modelScore } from '../model-score.js';

export default function ChatHeader({ title, lastIntent, lastConfidence, confidenceSource, onMenuClick }) {
  const score = modelScore(lastConfidence, confidenceSource);
  const pillText =
    lastIntent
      ? score ? `${score.label}: ${score.percent}` : 'Skin information and screening'
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
      <div className="model-pill" title={score?.explanation || 'Educational information; screening suggestions are not a diagnosis.'}>{pillText}</div>
    </div>
  );
}
