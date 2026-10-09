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

export default function MessageBubble({ message, onFollowUp, onImageUpload, uploadDisabled }) {
  const { who, text, intent, confidence, confidenceSource, followUps, animate, image, imageResult, action } = message;
  const [copied, setCopied] = useState(false);
  const [revealing, setRevealing] = useState(!!animate);
  useEffect(() => { if (!animate) setRevealing(false); }, [animate]);
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
        {image && <img className="message-image" src={image} alt="Uploaded skin photo" />}
        <div
          className="bubble"
          style={who === 'bot' ? { '--intent-color': meta.color } : undefined}
        >
          {shown}
          {revealing && <span className="caret" />}
        </div>

        {who === 'bot' && imageResult?.status === 'ok' && !revealing && (
          <div className="image-result">
            <strong>{imageResult.condition}</strong>
            {imageResult.all_probabilities && (
              <details>
                <summary>Model scores</summary>
                <ul>
                  {Object.entries(imageResult.all_probabilities)
                    .sort((a, b) => b[1] - a[1])
                    .map(([name, score]) => (
                      <li key={name}>{name.replaceAll('_', ' ')}: {(score * 100).toFixed(1)}%</li>
                    ))}
                </ul>
              </details>
            )}
            {imageResult.gradcam?.startsWith('data:image/png;base64,') && (
              <figure>
                <img className="message-image" src={imageResult.gradcam} alt="Model attention heatmap" />
                <figcaption>Highlighted areas show where the image model focused.</figcaption>
              </figure>
            )}
          </div>
        )}

        {who === 'bot' && intent && !revealing && (
          <div className="meta-row">
            <span className="intent-tag" style={{ '--intent-color': meta.color }}>
              · intent: {meta.label}
            </span>
            {typeof confidence === 'number' && (
              <span className="confidence" title={`${(confidence * 100).toFixed(1)}% ${confidenceSource === 'image_model' ? 'image model confidence' : 'text intent confidence'}`}>
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

        {who === 'bot' && action === 'upload_image' && !revealing && (
          <button className="follow-up" onClick={onImageUpload} disabled={uploadDisabled}>
            Choose photo
          </button>
        )}

        {who === 'bot' && followUps && followUps.length > 0 && !revealing && (
          <div className="follow-ups">
            {followUps.map((f, i) => (
              <button key={i} className="follow-up" disabled={uploadDisabled} onClick={() => onFollowUp(f)}>
                {f}
              </button>
            ))}
          </div>
        )}
        {message.createdAt && <time className="message-time" dateTime={message.createdAt} title={new Date(message.createdAt).toLocaleString()}>
          {new Date(message.createdAt).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
        </time>}
      </div>
    </div>
  );
}
