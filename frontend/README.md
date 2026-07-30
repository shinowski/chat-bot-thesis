# Flamma — React front end

This replaces `templates/index.html`, `static/script.js`, and `static/style.css`
with a proper React (Vite) app. Your Flask backend (`app.py`, `/predict`) is
untouched — nothing here changes what the model expects or returns.

## Setup

```bash
cd flamma-react
npm install
npm run dev
```

This starts the React dev server on `http://localhost:5173`. Run your Flask
app separately (`python app.py`, usually on port 5000) — `vite.config.js`
already proxies any request to `/predict` straight through to Flask, so the
browser never sees a cross-origin request and `app.py` needs zero changes.

## Contract with the backend

`App.jsx` POSTs to `/predict` exactly like your old `script.js` did:

```js
fetch('/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: text }),
})
```

and expects back:

```json
{ "intent": "symptom", "confidence": 0.87, "reply": "..." }
```

If you later have your Flask route also return a `followUps` array (list of
strings), the UI will render them as quick-reply chips automatically —
otherwise it falls back to sensible defaults per intent (see `src/intents.js`).

## What's new vs. the old vanilla-JS version

- **Word-by-word reveal** on bot replies instead of the text appearing all at once.
- **Animated confidence meter** next to each bot message and in the header pill, driven by the real `confidence` value from `/predict`.
- **Copy button** on bot bubbles (hover/appears after the message finishes revealing).
- **Mobile drawer sidebar** with a hamburger toggle and dimmed backdrop — the old layout just hid the sidebar completely below 720px.
- **Message enter animation** (subtle rise + fade) so new messages don't just pop in.
- Same color system (teal / ember / sage), same fonts (Fraunces / Inter / IBM Plex Mono), same layout — nothing about the visual identity changed, it's just componentized and a bit more alive.

## Shipping it

When you're ready to serve this from Flask instead of running two dev
servers:

```bash
npm run build
```

This outputs static files to `flamma-react/dist/`. Point Flask's static
folder at `dist/` (or copy `dist/assets` into your existing `static/` folder
and `dist/index.html` into `templates/`), and drop the old `script.js` /
`style.css` — they're fully superseded by this project.

## Project structure

```
flamma-react/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx          # entry point
    ├── App.jsx           # state, conversations, /predict fetch
    ├── index.css         # design tokens + all styles
    ├── intents.js        # intent → color/label, default follow-ups
    └── components/
        ├── Sidebar.jsx
        ├── ChatHeader.jsx
        ├── MessageList.jsx
        ├── MessageBubble.jsx
        ├── TypingIndicator.jsx
        └── Composer.jsx
```
