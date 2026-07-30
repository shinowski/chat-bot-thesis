import { useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import ChatHeader from './components/ChatHeader.jsx';
import MessageList from './components/MessageList.jsx';
import Composer from './components/Composer.jsx';
import { DEFAULT_FOLLOWUPS } from './intents.js';

let nextConvoId = 2;
let nextMsgId = 1;

function newConversation() {
  return { id: nextConvoId++, title: 'New conversation', preview: '', messages: [] };
}

export default function App() {
  const [conversations, setConversations] = useState([
    { id: 1, title: 'New conversation', preview: '', messages: [] },
  ]);
  const [activeId, setActiveId] = useState(1);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const active = conversations.find((c) => c.id === activeId);
  const lastBotMsg = [...active.messages].reverse().find((m) => m.who === 'bot');

  const updateActive = (updater) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === activeId ? updater(c) : c))
    );
  };

  const handleSend = async (override) => {
    const text = (override !== undefined ? override : input).trim();
    if (!text) return;

    const userMsg = { id: nextMsgId++, who: 'user', text };
    updateActive((c) => {
      const isFirst = c.messages.filter((m) => m.who === 'user').length === 0;
      return {
        ...c,
        title: isFirst ? (text.length > 28 ? text.slice(0, 28) + '…' : text) : c.title,
        preview: text,
        messages: [...c.messages, userMsg],
      };
    });
    setInput('');
    setIsTyping(true);

    try {
      const res = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();

      const botMsg = {
        id: nextMsgId++,
        who: 'bot',
        text: data.reply,
        intent: data.intent,
        confidence: data.confidence,
        followUps: data.followUps || DEFAULT_FOLLOWUPS[data.intent] || [],
        animate: true,
      };
      setIsTyping(false);
      updateActive((c) => ({ ...c, messages: [...c.messages, botMsg] }));
    } catch (err) {
      console.error(err);
      setIsTyping(false);
      const errMsg = {
        id: nextMsgId++,
        who: 'bot',
        text: "I couldn't reach the server just now — check that the Flask backend is running and try again.",
        intent: 'unknown',
        confidence: null,
        followUps: [],
        animate: true,
      };
      updateActive((c) => ({ ...c, messages: [...c.messages, errMsg] }));
    }
  };

  const handleNewChat = () => {
    const convo = newConversation();
    setConversations((prev) => [...prev, convo]);
    setActiveId(convo.id);
    setSidebarOpen(false);
  };

  const handleSelect = (id) => {
    setActiveId(id);
    setSidebarOpen(false);
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main">
        <ChatHeader
          title={active.title}
          lastIntent={lastBotMsg?.intent}
          lastConfidence={lastBotMsg?.confidence}
          onMenuClick={() => setSidebarOpen((o) => !o)}
        />
        <MessageList
          messages={active.messages}
          isTyping={isTyping}
          onFollowUp={(f) => handleSend(f)}
        />
        <Composer
          value={input}
          onChange={setInput}
          onSend={() => handleSend()}
          disabled={isTyping}
        />
      </main>
    </div>
  );
}
