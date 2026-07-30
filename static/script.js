// ---------------------------------------------------------------
// Minimal in-memory "intent classifier" — a stand-in for Phase 5/6
// (tokenizer -> vocabulary -> LSTM). Swap this function's internals
// for a fetch() to your Flask /predict endpoint later.
// ---------------------------------------------------------------
const INTENTS = {
  greeting:   { color:'#0F5C56', keywords:['hello','hi','hey','good morning','good afternoon','good evening'] },
  symptom:    { color:'#E8592A', keywords:['itchy','itch','rash','red','pain','hurts','swollen','burning','bump','dry','flaky','sore'] },
  duration:   { color:'#8A6D3B', keywords:['days','week','weeks','months','since','ago','started'] },
  medication: { color:'#4C6FBF', keywords:['cream','medicine','medication','pill','ointment','can i use','should i take'] },
  emergency:  { color:'#C43A3A', keywords:['bleeding','fever','difficulty breathing','severe pain','can\'t breathe','emergency'] },
  goodbye:    { color:'#5C6D68', keywords:['thank you','thanks','bye','goodbye','that\'s all'] },
};

function classify(text){
  const t = text.toLowerCase();
  for (const [intent, def] of Object.entries(INTENTS)){
    if (def.keywords.some(k => t.includes(k))) return intent;
  }
  return 'unknown';
}

function respond(intent, text){
  switch(intent){
    case 'greeting':
      return { reply: "Hi there. What's been bothering you — where on your body, and when did you first notice it?", followUps: [] };
    case 'symptom':
      return {
        reply: "Thanks for the detail. A couple quick follow-ups so I can narrow this down:",
        followUps: ["Is it red?", "Is it painful?", "Is it flaky?", "How long has it been present?"]
      };
    case 'duration':
      return { reply: "Got it, that timing helps. Has it stayed the same size, or changed since it started?", followUps: ["Stayed the same", "Getting bigger", "Getting smaller", "Comes and goes"] };
    case 'medication':
      return { reply: "I can't recommend a specific product without knowing more first — is the area broken, weeping, or intact skin?", followUps: ["Intact", "Broken / weeping"] };
    case 'emergency':
      return { reply: "That combination of symptoms is worth getting checked in person soon rather than waiting — please consider urgent or same-day care.", followUps: [] };
    case 'goodbye':
      return { reply: "Take care of that skin — come back any time if it changes.", followUps: [] };
    default:
      return { reply: "Tell me a bit more — for example, where it is and what it looks like — and I'll try to help narrow it down.", followUps: ["It's a rash", "It's itchy", "It's painful"] };
  }
}

// ---------------------------------------------------------------
// State
// ---------------------------------------------------------------
let conversations = [
  { id: 1, title: 'New conversation', preview: '', messages: [] }
];
let activeId = 1;

const messagesEl = document.getElementById('messages');
const historyEl  = document.getElementById('historyList');
const titleEl    = document.getElementById('chatTitle');
const pillEl     = document.getElementById('modelPill');
const inputEl    = document.getElementById('input');
const sendBtn    = document.getElementById('sendBtn');

function activeConvo(){ return conversations.find(c => c.id === activeId); }

function renderHistory(){
  historyEl.innerHTML = '';
  [...conversations].reverse().forEach(c => {
    const div = document.createElement('div');
    div.className = 'history-item' + (c.id === activeId ? ' active' : '');
    div.innerHTML = `<div class="t">${escapeHtml(c.title)}</div><div class="s">${escapeHtml(c.preview || 'No messages yet')}</div>`;
    div.onclick = () => { activeId = c.id; render(); };
    historyEl.appendChild(div);
  });
}

function bubbleRow(who, text, intent, followUps){
  const row = document.createElement('div');
  row.className = 'row ' + who;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = who === 'bot' ? 'F' : 'U';

  const wrap = document.createElement('div');
  wrap.className = 'bubble-wrap';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  if (who === 'bot' && intent){
    bubble.style.setProperty('--intent-color', INTENTS[intent] ? INTENTS[intent].color : '#0F5C56');
  }
  wrap.appendChild(bubble);

  if (who === 'bot' && intent){
    const tag = document.createElement('div');
    tag.className = 'intent-tag';
    tag.style.setProperty('--intent-color', INTENTS[intent] ? INTENTS[intent].color : '#0F5C56');
    tag.textContent = '· intent: ' + intent;
    wrap.appendChild(tag);
  }

  if (followUps && followUps.length){
    const fu = document.createElement('div');
    fu.className = 'follow-ups';
    followUps.forEach(f => {
      const btn = document.createElement('button');
      btn.className = 'follow-up';
      btn.textContent = f;
      btn.onclick = () => sendMessage(f);
      fu.appendChild(btn);
    });
    wrap.appendChild(fu);
  }

  row.appendChild(who === 'bot' ? avatar : wrap);
  row.appendChild(who === 'bot' ? wrap : avatar);
  return row;
}

function render(){
  const c = activeConvo();
  titleEl.textContent = c.title;
  messagesEl.innerHTML = '';
  if (c.messages.length === 0){
    messagesEl.appendChild(bubbleRow('bot', "Hi, I'm Flamma. Tell me what you're noticing on your skin and when it started.", 'greeting', []));
  }
  c.messages.forEach(m => {
    messagesEl.appendChild(bubbleRow(m.who, m.text, m.intent, m.followUps));
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
  renderHistory();
}

function showTyping(){
  const row = document.createElement('div');
  row.className = 'row bot';
  row.id = 'typingRow';
  const avatar = document.createElement('div');
  avatar.className = 'avatar'; avatar.textContent = 'F';
  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.innerHTML = '<span></span><span></span><span></span>';
  row.appendChild(avatar);
  row.appendChild(typing);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideTyping(){
  const row = document.getElementById('typingRow');
  if (row) row.remove();
}

function escapeHtml(s){
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function sendMessage(textOverride){
  const text = (textOverride !== undefined ? textOverride : inputEl.value).trim();
  if (!text) return;

  const c = activeConvo();
  c.messages.push({ who:'user', text, intent:null, followUps:[] });
  if (c.messages.filter(m=>m.who==='user').length === 1){
    c.title = text.length > 28 ? text.slice(0,28) + '…' : text;
  }
  c.preview = text;
  inputEl.value = '';
  inputEl.style.height = 'auto';
  render();

  showTyping();
  try {

    const flaskResponse = await fetch("/predict", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            message: text
        })

    });

    const data = await flaskResponse.json();

    hideTyping();

    pillEl.textContent =
    data.intent +
    " (" +
    (data.confidence * 100).toFixed(1) +
    "%)";

c.messages.push({
    who: "bot",
    text: data.reply,
    intent: null,
    followUps: []
});

    render();

}
catch(error){

    hideTyping();

    console.error(error);

}
}

sendBtn.addEventListener('click', () => sendMessage());
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
});
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

document.getElementById('newChatBtn').addEventListener('click', () => {
  const id = Math.max(...conversations.map(c=>c.id)) + 1;
  conversations.push({ id, title:'New conversation', preview:'', messages:[] });
  activeId = id;
  pillEl.textContent = 'intent: —';
  render();
});

render();