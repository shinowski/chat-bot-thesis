import { Fragment, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble.jsx';
import TypingIndicator from './TypingIndicator.jsx';

export default function MessageList({ messages, isTyping, onFollowUp, onImageUpload, disabled }) {
  const endRef = useRef(null);
  let lastDay;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, isTyping]);

  return (
    <div className="messages">
      {messages.length === 0 && (
        <div className="empty-chat-intro">
          <div className="empty-chat-brand"><span className="empty-chat-mark" aria-hidden="true" />Flamma</div>
          <h1 className="empty-chat-heading">Let’s talk about your <span>skin.</span></h1>
          <p className="empty-chat-subtitle">Ask a question or share a photo. Let’s start there.</p>
        </div>
      )}
      {messages.map((m) => {
        const day = m.createdAt ? new Date(m.createdAt).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' }) : null;
        const showDate = day && day !== lastDay;
        lastDay = day || lastDay;
        return <Fragment key={m.id}>
          {showDate && <div className="message-date">{day}</div>}
          <MessageBubble message={m} onFollowUp={onFollowUp} onImageUpload={onImageUpload} uploadDisabled={disabled || isTyping} />
        </Fragment>;
      })}
      {isTyping && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
