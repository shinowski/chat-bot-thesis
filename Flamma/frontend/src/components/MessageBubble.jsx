import { useState } from 'react';
import { intentMeta } from '../intents.js';
import { modelScore, formatModelPercent } from '../model-score.js';

export default function MessageBubble({ message, onFollowUp, onImageUpload, uploadDisabled }) {
  const { who, text, intent, confidence, confidenceSource, followUps, image, imageResult, action } = message;
  const [copied, setCopied] = useState(false);
  const meta = intentMeta(intent);
  const score = modelScore(confidence, confidenceSource);

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
          {text}
        </div>

        {who === 'bot' && imageResult?.status === 'ok' && (
          <div className="image-result">
            <strong>Screening match: {imageResult.condition}</strong>
            <p className="score-note">Model scores are not disease probabilities or measured diagnostic accuracy.</p>
            {imageResult.all_probabilities && (
              <details>
                <summary>Model scores</summary>
                <ul>
                  {Object.entries(imageResult.all_probabilities)
                    .filter(([, value]) => formatModelPercent(value) !== null)
                    .sort((a, b) => b[1] - a[1])
                    .map(([name, score]) => (
                      <li key={name}>{name.replaceAll('_', ' ')}: {formatModelPercent(score)}</li>
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

        {who === 'bot' && intent && (
          <div className="meta-row">
            <span className="intent-tag" style={{ '--intent-color': meta.color }}>
              · intent: {meta.label}
            </span>
            {score && (
              <span className="confidence" title={score.explanation}>
                <span>{score.label}:</span>
                <span className="confidence-track">
                  <span
                    className="confidence-fill"
                    style={{ width: `${Math.round(confidence * 100)}%`, '--intent-color': meta.color }}
                  />
                </span>
                {score.percent}
              </span>
            )}
            <button className="ghost-btn" onClick={handleCopy}>
              {copied ? 'copied' : 'copy'}
            </button>
          </div>
        )}

        {who === 'bot' && action === 'upload_image' && (
          <button className="follow-up" onClick={onImageUpload} disabled={uploadDisabled}>
            Choose photo
          </button>
        )}

        {who === 'bot' && message.treatmentInfo?.sources?.length > 0 && (
          <div className="care-sources">
            <span>Care information sources:</span>
            {message.treatmentInfo.sources.map(source => (
              <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">{source.title}{source.source_checked_on ? ` (checked ${source.source_checked_on})` : ''}</a>
            ))}
            {message.treatmentInfo.source_checked_on && <span>Source links checked: {message.treatmentInfo.source_checked_on}</span>}
          </div>
        )}

        {who === 'bot' && followUps && followUps.length > 0 && (
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
