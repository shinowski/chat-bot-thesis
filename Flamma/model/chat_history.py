"""Local chat storage. Every lookup is scoped to the browser's session owner."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class ChatHistory:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            PRAGMA secure_delete = ON;
            CREATE TABLE IF NOT EXISTS conversations (
                owner TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                state TEXT NOT NULL, PRIMARY KEY (owner, id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, conversation_id TEXT NOT NULL,
                text TEXT NOT NULL, payload TEXT NOT NULL,
                image BLOB, mime TEXT, created_at TEXT NOT NULL,
                FOREIGN KEY (owner, conversation_id)
                    REFERENCES conversations(owner, id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS messages_chat
                ON messages(owner, conversation_id, created_at);
        """)

    def get(self, owner, chat_id):
        return self.db.execute(
            "SELECT * FROM conversations WHERE owner=? AND id=?", (owner, chat_id)
        ).fetchone()

    def list(self, owner, query=""):
        # Escape LIKE wildcards so searching for '%' or '_' is literal.
        term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        rows = self.db.execute(r"""
            SELECT c.id, c.title, c.created_at AS createdAt, c.updated_at AS updatedAt,
                (SELECT m.text FROM messages m WHERE m.owner=c.owner AND m.conversation_id=c.id
                 ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1) AS preview,
                (SELECT m.text FROM messages m WHERE m.owner=c.owner AND m.conversation_id=c.id
                 AND m.text LIKE ? ESCAPE '\' ORDER BY m.created_at, m.rowid LIMIT 1) AS match
            FROM conversations c WHERE c.owner=? AND
                (c.title LIKE ? ESCAPE '\' OR EXISTS (
                    SELECT 1 FROM messages m WHERE m.owner=c.owner AND m.conversation_id=c.id
                    AND m.text LIKE ? ESCAPE '\'))
            ORDER BY c.updated_at DESC, c.rowid DESC
        """, (term, owner, term, term)).fetchall()
        return [dict(row) for row in rows]

    def summary(self, owner, chat_id):
        row = self.db.execute("""
            SELECT c.id, c.title, c.created_at AS createdAt, c.updated_at AS updatedAt,
                (SELECT m.text FROM messages m WHERE m.owner=c.owner AND m.conversation_id=c.id
                 ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1) AS preview, NULL AS match
            FROM conversations c WHERE c.owner=? AND c.id=?
        """, (owner, chat_id)).fetchone()
        return dict(row)

    def messages(self, owner, chat_id):
        rows = self.db.execute(
            "SELECT payload FROM messages WHERE owner=? AND conversation_id=? ORDER BY created_at, rowid",
            (owner, chat_id),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_turn(self, owner, chat_id, text, result, state, image=None, mime=None):
        now = datetime.now(timezone.utc).isoformat()
        user_id, bot_id = uuid4().hex, uuid4().hex
        user = {"id": user_id, "who": "user", "text": text or "Uploaded an image", "createdAt": now}
        if image is not None:
            user["image"] = f"/api/conversations/{chat_id}/images/{user_id}"
        bot = {**result, "id": bot_id, "who": "bot", "text": result["reply"], "createdAt": now}
        bot.pop("reply", None)
        with self.db:
            self.db.execute("""
                INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner, id) DO UPDATE SET updated_at=excluded.updated_at, state=excluded.state
            """, (owner, chat_id, (text or "Skin photo")[:60], now, now, json.dumps(state)))
            for message, attachment in [(user, image), (bot, None)]:
                self.db.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    message["id"], owner, chat_id, message["text"], json.dumps(message),
                    attachment, mime if attachment is not None else None, now,
                ))
        return self.summary(owner, chat_id), [user, bot]

    def rename(self, owner, chat_id, title):
        with self.db:
            self.db.execute("UPDATE conversations SET title=? WHERE owner=? AND id=?", (title, owner, chat_id))

    def delete(self, owner, chat_id=None):
        with self.db:
            if chat_id is None:
                self.db.execute("DELETE FROM conversations WHERE owner=?", (owner,))
            else:
                self.db.execute("DELETE FROM conversations WHERE owner=? AND id=?", (owner, chat_id))

    def image(self, owner, chat_id, message_id):
        return self.db.execute(
            "SELECT image, mime FROM messages WHERE owner=? AND conversation_id=? AND id=? AND image IS NOT NULL",
            (owner, chat_id, message_id),
        ).fetchone()
