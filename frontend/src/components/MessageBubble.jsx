import { useEffect, useRef, useState } from 'react';
import { intentMeta } from '../intents.js';

// Bot replies arrive whole from /predict, but revealing them word-by-word
// (instead of slamming the full paragraph on screen) is what makes the
// bot feel like it's actually composing an answer rather than pasting one.
function useReveal(fullText, enabled, onDone) {
  const [shown, setShown] = useState(enabled ? '' : fullText);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!enabled) { setShown(fullText); return; }
    doneRef.current = false;
    const words = fullText.split(' ');
    let i = 0;
    setShown('');
    const id = setInterval(() => {
      i += 1;
      setShown(words.slice(0, i).join(' '));
      if (i >= words.length) {
        clearInterval(id);
        if (!doneRef.current) { doneRef.current = true; onDone && onDone(); }
      }
    }, 32);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullText, enabled]);

  return shown;
}

export default function MessageBubble({ message, onFollowUp }) {
  const { who, text, intent, confidence, followUps, animate } = message;
  const [copied, setCopied] = useState(false);
  const [revealing, setRevealing] = useState(!!animate);
  const shown = useReveal(text, !!animate, () => setRevealing(false));
  const meta = intentMeta(intent);

  const handleCopy = () => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    });
  };

  return (
    <div className={`row ${who} enter`}>
      <div className="avatar">{who === 'bot' ? 'F' : 'U'}</div>

      <div className="bubble-wrap">
        <div
          className="bubble"
          style={who === 'bot' ? { '--intent-color': meta.color } : undefined}
        >
          {shown}
          {revealing && <span className="caret" />}
        </div>

        {who === 'bot' && intent && !revealing && (
          <div className="meta-row">
            <span className="intent-tag" style={{ '--intent-color': meta.color }}>
              · intent: {meta.label}
            </span>
            {typeof confidence === 'number' && (
              <span className="confidence" title={`${(confidence * 100).toFixed(1)}% confidence`}>
                <span className="confidence-track">
                  <span
                    className="confidence-fill"
                    style={{ width: `${Math.round(confidence * 100)}%`, '--intent-color': meta.color }}
                  />
                </span>
                {(confidence * 100).toFixed(0)}%
              </span>
            )}
            <button className="ghost-btn" onClick={handleCopy}>
              {copied ? 'copied' : 'copy'}
            </button>
          </div>
        )}

        {who === 'bot' && followUps && followUps.length > 0 && !revealing && (
          <div className="follow-ups">
            {followUps.map((f, i) => (
              <button key={i} className="follow-up" onClick={() => onFollowUp(f)}>
                {f}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
