import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble.jsx';
import TypingIndicator from './TypingIndicator.jsx';

export default function MessageList({ messages, isTyping, onFollowUp }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, isTyping]);

  return (
    <div className="messages">
      {messages.length === 0 && (
        <MessageBubble
          message={{
            who: 'bot',
            text: "Hi, I'm Flamma. Tell me what you're noticing on your skin and when it started.",
            intent: 'greeting',
            confidence: null,
            followUps: [],
          }}
          onFollowUp={onFollowUp}
        />
      )}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} onFollowUp={onFollowUp} />
      ))}
      {isTyping && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
