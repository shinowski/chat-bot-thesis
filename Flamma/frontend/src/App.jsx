import { useEffect, useRef, useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import ChatHeader from './components/ChatHeader.jsx';
import MessageList from './components/MessageList.jsx';
import Composer from './components/Composer.jsx';
import HistoryDialog from './components/HistoryDialog.jsx';
import { DEFAULT_FOLLOWUPS } from './intents.js';
import { fetchJson, RequestTimeoutError } from './request.js';
import { formatChatExport } from './chat-export.js';
import { RetryRequests, mergeSavedExchange } from './retry-requests.js';

function newConversation() {
  return { id: crypto.randomUUID(), title: 'New conversation', preview: '', messages: [], loaded: true };
}
async function api(path, options) {
  const { response, data } = await fetchJson(path, options);
  if (!response.ok) throw new Error(data.error || 'Could not save your changes. Please try again.');
  return data;
}
function restoreMessages(messages) {
  return messages.map((m) => ({ ...m, followUps: m.followUps || DEFAULT_FOLLOWUPS[m.intent] || [] }));
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
  const retries = useRef(null);
  retries.current ||= new RetryRequests();
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
        retries.current.reconcile(chosen.id, detail.messages);
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
      const attempt = await retries.current.forPayload(chatId, text, imageToSend);
      const form = new FormData();
      form.append('message', text); form.append('conversation_id', chatId);
      form.append('request_id', attempt.requestId);
      if (imageToSend) form.append('image', imageToSend);
      const { response, data } = await fetchJson('/predict', { method: 'POST', body: form }, imageToSend ? 120000 : 60000);
      if (!response.ok && !data.messages) {
        const failure = new Error(data.reply || 'This message could not be saved.');
        failure.confirmedUnsaved = true;
        throw failure;
      }
      if (!data.reply) throw new Error('No reply received');
      const bot = { id: crypto.randomUUID(), who: 'bot', text: data.reply, intent: data.intent,
        confidence: data.confidence, confidenceSource: data.confidenceSource, imageResult: data.imageResult,
        treatmentInfo: data.treatmentInfo,
        action: data.action, followUps: data.followUps || DEFAULT_FOLLOWUPS[data.intent] || [] };
      updateChat(chatId, (c) => ({ ...c, ...data.conversation, saved: !!data.conversation || c.saved,
        messages: data.messages
          ? mergeSavedExchange(c.messages, userMsg.id, data.messages)
          : [...c.messages, bot],
      }));
      if (data.messages && imagePreview) URL.revokeObjectURL(imagePreview);
      if (data.messages) retries.current.clear(chatId, attempt.requestId);
      if (!data.conversation) setError('This exchange was not saved. You can send it again.');
    } catch (err) {
      updateChat(chatId, (c) => ({ ...c, messages: c.messages.filter((m) => m.id !== userMsg.id) }));
      if (imagePreview) URL.revokeObjectURL(imagePreview);
      if (selectedRef.current === chatId) {
        setInput((draft) => draft || text);
        setSelectedImage((draft) => draft || imageToSend);
      }
      setError(err.confirmedUnsaved ? err.message : err instanceof RequestTimeoutError
        ? 'This reply is taking too long. Your draft is restored. You can resend it, or reload the conversation to check for a saved reply.'
        : 'The reply could not be confirmed. Your draft is restored. Check your connection, then resend it or reload the conversation.');
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
      const resolved = retries.current.reconcile(id, data.messages);
      if (resolved && selectedRef.current === id) {
        const original = data.messages.find(message => message.who === 'user' && message.requestId === resolved.requestId);
        if (original) setInput(draft => draft.trim() === original.text ? '' : draft);
        if (resolved.image) setSelectedImage(draft => draft === resolved.image ? null : draft);
      }
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
    const text = formatChatExport(chat);
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
        if (type === 'clear') retries.current.clearAll(); else retries.current.clear(chat.id);
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
        <details className="prototype-info">
          <summary>About this prototype and saved chats</summary>
          <p>Flamma provides educational skin information and photo screening. It cannot confirm a diagnosis or replace a clinician. Model scores are not disease probabilities.</p>
          <p>Chats and photos save on the Flamma server and are linked to this browser session. The app does not encrypt stored records or provide account sign-in. Anyone using this browser profile or with access to server files may access them. Use the conversation menu or Clear history to delete application records; exports and backups are separate copies.</p>
        </details>
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
