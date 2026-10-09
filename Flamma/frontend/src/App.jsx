import { useEffect, useRef, useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import ChatHeader from './components/ChatHeader.jsx';
import MessageList from './components/MessageList.jsx';
import Composer from './components/Composer.jsx';
import HistoryDialog from './components/HistoryDialog.jsx';
import { DEFAULT_FOLLOWUPS } from './intents.js';

function newConversation() {
  return { id: crypto.randomUUID(), title: 'New conversation', preview: '', messages: [], loaded: true };
}
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not save your changes. Please try again.');
  return data;
}
function restoreMessages(messages) {
  return messages.map((m) => ({ ...m, animate: false, followUps: m.followUps || DEFAULT_FOLLOWUPS[m.intent] || [] }));
}

export default function App() {
  const [initial] = useState(newConversation);
  const [conversations, setConversations] = useState([initial]);
  const [activeId, setActiveId] = useState(initial.id);
  const [input, setInput] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [typingId, setTypingId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState('');
  const [dialog, setDialog] = useState(null);
  const [dialogBusy, setDialogBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const sendingRef = useRef(false);
  const imageInputRef = useRef(null);
  const bootRef = useRef(null);
  const selectedRef = useRef(initial.id);
  const active = conversations.find((c) => c.id === activeId) || initial;
  const lastBotMsg = [...active.messages].reverse().find((m) => m.who === 'bot');
  const blocked = loading || !active.loaded || !!typingId;

  useEffect(() => {
    let cancelled = false;
    // Reuse the initial request during StrictMode's effect replay.
    bootRef.current ||= api('/api/conversations');
    bootRef.current.then(async (data) => {
      let selected;
      try { selected = localStorage.getItem('flamma.activeChat'); } catch { /* optional */ }
      const summaries = data.conversations.map((c) => ({ ...c, messages: [], loaded: false, saved: true }));
      // An unsaved selected chat should stay blank after refresh, rather than
      // silently reopening an older saved conversation.
      const chosen = selected ? summaries.find((c) => c.id === selected) : summaries[0];
      if (chosen) {
        const detail = await api(`/api/conversations/${chosen.id}`);
        chosen.messages = restoreMessages(detail.messages);
        chosen.loaded = true;
      }
      if (cancelled) return;
      setConversations(chosen ? summaries : [...summaries, initial]);
      setActiveId(chosen?.id || initial.id);
      selectedRef.current = chosen?.id || initial.id;
      setLoading(false); setError('');
    }).catch(() => {
      if (!cancelled) setError('Your history could not be loaded. Check the connection and try again.');
    });
    return () => { cancelled = true; };
  }, [reload, initial]);

  useEffect(() => {
    if (loading) return;
    try { localStorage.setItem('flamma.activeChat', activeId); } catch { /* optional */ }
  }, [activeId, loading]);

  useEffect(() => {
    let cancelled = false;
    setSearchError(''); setSearchResults(null);
    if (!query.trim() || loading) return;
    const timer = setTimeout(() => {
      api(`/api/conversations?q=${encodeURIComponent(query.trim())}`).then((data) => {
        if (!cancelled) setSearchResults(data.conversations);
      }).catch(() => {
        if (!cancelled) setSearchError('Search is unavailable. Please try again.');
      });
    }, 200);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, conversations, loading]);

  function updateChat(id, updater) {
    setConversations((prev) => prev.map((c) => c.id === id ? updater(c) : c));
  }
  function openImagePicker() {
    const picker = imageInputRef.current;
    if (!picker || blocked) return;
    try { if (picker.showPicker) picker.showPicker(); else picker.click(); }
    catch { picker.click(); }
  }

  async function handleSend(override) {
    if (sendingRef.current || blocked) return;
    const text = (override !== undefined ? override : input).trim();
    if (!text && !selectedImage) return;
    sendingRef.current = true;
    const chatId = activeId;
    const imageToSend = selectedImage;
    const imagePreview = imageToSend ? URL.createObjectURL(imageToSend) : null;
    const userMsg = { id: crypto.randomUUID(), who: 'user', text: text || 'Uploaded an image', image: imagePreview };
    updateChat(chatId, (c) => ({ ...c,
      title: c.messages.length ? c.title : (text || 'Skin photo').slice(0, 60),
      preview: userMsg.text, updatedAt: new Date().toISOString(), messages: [...c.messages, userMsg],
    }));
    setInput(''); setSelectedImage(null); setTypingId(chatId); setError('');
    try {
      const form = new FormData();
      form.append('message', text); form.append('conversation_id', chatId);
      if (imageToSend) form.append('image', imageToSend);
      const response = await fetch('/predict', { method: 'POST', body: form });
      const data = await response.json();
      if (!data.reply) throw new Error('No reply received');
      const bot = { id: crypto.randomUUID(), who: 'bot', text: data.reply, intent: data.intent,
        confidence: data.confidence, confidenceSource: data.confidenceSource, imageResult: data.imageResult,
        action: data.action, followUps: data.followUps || DEFAULT_FOLLOWUPS[data.intent] || [], animate: true };
      updateChat(chatId, (c) => ({ ...c, ...data.conversation, saved: !!data.conversation || c.saved,
        messages: data.messages
          ? [...c.messages.filter((m) => m.id !== userMsg.id), data.messages[0], { ...data.messages[1], animate: selectedRef.current === chatId }]
          : [...c.messages, bot],
      }));
      if (data.messages && imagePreview) URL.revokeObjectURL(imagePreview);
      if (!data.conversation) setError('This exchange was not saved. You can send it again.');
    } catch {
      updateChat(chatId, (c) => ({ ...c, messages: c.messages.filter((m) => m.id !== userMsg.id) }));
      if (imagePreview) URL.revokeObjectURL(imagePreview);
      if (selectedRef.current === chatId) {
        setInput((draft) => draft || text);
        setSelectedImage((draft) => draft || imageToSend);
      }
      setError('The message could not be confirmed as saved. Check your connection and reload the conversation before retrying.');
    } finally { setTypingId(null); sendingRef.current = false; }
  }

  function handleNewChat() {
    const chat = newConversation();
    // Keep chats with messages, but avoid accumulating unused blank entries.
    setConversations((prev) => [...prev.filter((c) => c.saved || c.messages.length), chat]);
    selectedRef.current = chat.id; setActiveId(chat.id);
    setInput(''); setSelectedImage(null); setSidebarOpen(false); setQuery(''); setError('');
  }
  async function loadChat(id) {
    try {
      const data = await api(`/api/conversations/${id}`);
      setConversations((prev) => {
        const restored = { ...data.conversation, saved: true, messages: restoreMessages(data.messages), loaded: true };
        return prev.some((c) => c.id === id) ? prev.map((c) => c.id === id ? { ...c, ...restored } : c) : [...prev, restored];
      });
    } catch {
      if (selectedRef.current === id) setError('This conversation could not be loaded. Please try again.');
    }
  }
  function handleSelect(id) {
    selectedRef.current = id; setActiveId(id);
    setInput(''); setSelectedImage(null); setSidebarOpen(false); setError('');
    updateChat(id, (c) => ({ ...c, messages: restoreMessages(c.messages) }));
    if (!conversations.find((c) => c.id === id)) {
      setConversations((prev) => [...prev, { id, title: 'Conversation', messages: [], loaded: false, saved: true }]);
    }
    if (!conversations.find((c) => c.id === id)?.loaded) loadChat(id);
  }

  function exportChat(chat) {
    const text = `${chat.title}\n\n` + chat.messages.map((m) =>
      `${m.who === 'user' ? 'You' : 'Flamma'}${m.createdAt ? ` · ${new Date(m.createdAt).toLocaleString()}` : ''}\n${m.text}${m.image ? '\n[Attached photo]' : ''}`
    ).join('\n\n');
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${chat.title.replace(/[^a-z0-9 -]/gi, '').slice(0, 60) || 'Flamma chat'}.txt`;
    link.click(); URL.revokeObjectURL(url);
  }
  async function handleAction(type, chat) {
    if (type === 'export') {
      try {
        if (chat.loaded) exportChat(chat);
        else { const data = await api(`/api/conversations/${chat.id}`); exportChat({ ...chat, messages: data.messages }); }
      } catch { setError('Could not export this conversation. Please try again.'); }
      return;
    }
    setDialog({ type, chat, error: '' });
  }
  async function confirmAction(title) {
    if (dialogBusy) return;
    setDialogBusy(true);
    const { type, chat } = dialog;
    try {
      if (type === 'rename') {
        const data = await api(`/api/conversations/${chat.id}`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
        });
        updateChat(chat.id, (c) => ({ ...c, ...data.conversation }));
      } else {
        await api(type === 'clear' ? '/api/conversations' : `/api/conversations/${chat.id}`, { method: 'DELETE' });
        const remaining = type === 'clear' ? [] : conversations.filter((c) => c.id !== chat.id);
        if (!remaining.length) remaining.push(newConversation());
        setConversations(remaining);
        if (type === 'clear' || activeId === chat.id) {
          setActiveId(remaining[0].id); selectedRef.current = remaining[0].id;
          setInput(''); setSelectedImage(null);
          if (!remaining[0].loaded) loadChat(remaining[0].id);
        }
      }
      setDialog(null); setError('');
    } catch (err) { setDialog((current) => ({ ...current, error: err.message })); }
    finally { setDialogBusy(false); }
  }
  function retry() {
    if (loading) { bootRef.current = null; setReload((n) => n + 1); }
    else if (active.saved) {
      updateChat(activeId, (c) => ({ ...c, loaded: false })); setError(''); loadChat(activeId);
    } else { bootRef.current = null; setLoading(true); setReload((n) => n + 1); }
  }

  return (
    <div className="app">
      <Sidebar conversations={conversations} activeId={activeId} onSelect={handleSelect}
        onNewChat={handleNewChat} open={sidebarOpen} onClose={() => setSidebarOpen(false)}
        query={query} onSearch={setQuery} searchResults={searchResults} searchError={searchError}
        onAction={handleAction} disabled={loading || !!typingId || dialogBusy} loading={loading} />
      <main className={`main${!loading && active.loaded && active.messages.length === 0 ? ' chat-empty' : ''}`}>
        <ChatHeader title={active.title} lastIntent={lastBotMsg?.intent} lastConfidence={lastBotMsg?.confidence}
          confidenceSource={lastBotMsg?.confidenceSource} onMenuClick={() => setSidebarOpen((o) => !o)} />
        {error && <div className="history-notice" role="alert">{error} <button onClick={retry}>Try again</button></div>}
        {loading || !active.loaded ? <div className="chat-loading" role="status">Loading your conversation…</div>
          : <MessageList key={`messages-${activeId}`} messages={active.messages} isTyping={typingId === activeId}
              onFollowUp={handleSend} onImageUpload={openImagePicker} disabled={blocked} />}
        <Composer key={`composer-${activeId}`} value={input} onChange={setInput} onSend={() => handleSend()}
          onImageSelect={setSelectedImage} selectedImage={selectedImage} fileInputRef={imageInputRef}
          disabled={loading || !active.loaded} isSending={!!typingId} />
      </main>
      {dialog && <HistoryDialog action={dialog} busy={dialogBusy} onClose={() => setDialog(null)} onConfirm={confirmAction} />}
    </div>
  );
}
