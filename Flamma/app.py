import os
import re
import secrets
import json
from datetime import timedelta
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from uuid import uuid4

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, session

from model.image_classifier import ImageClassifierError
from model.chat_history import ChatHistory


def create_app(chatbot=None, history_path=None):
    app = Flask(__name__)
    # Injected bots use isolated memory unless a persistence path is supplied.
    isolated = chatbot is not None and history_path is None
    history_path = history_path or (":memory:" if isolated else Path(app.instance_path) / "chat_history.sqlite3")
    secret = os.environ.get("FLAMMA_SECRET_KEY")
    if not secret and str(history_path) != ":memory:":
        secret_path = Path(history_path).parent / ".session-secret"
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with secret_path.open("x", encoding="utf-8") as file:
                file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = secret_path.read_text(encoding="utf-8").strip()
    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=3650),
    )
    frontend_dist = Path(__file__).resolve().parent / "frontend/dist"
    conversations = OrderedDict()
    lock = RLock()
    prototype = chatbot
    history = ChatHistory(history_path)
    app.extensions["chat_history"] = history

    def owner():
        session.permanent = True
        return session.setdefault("client_id", uuid4().hex)

    @app.after_request
    def private_responses(response):
        if request.path.startswith("/api/") or request.path == "/predict":
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/api/conversations", methods=["GET", "DELETE"])
    def conversation_list():
        client_id = owner()
        with lock:
            if request.method == "DELETE":
                history.delete(client_id)
                for key in list(conversations):
                    if key[0] == client_id:
                        del conversations[key]
                return jsonify(ok=True)
            return jsonify(conversations=history.list(client_id, request.args.get("q", "").strip()))

    @app.route("/api/conversations/<chat_id>", methods=["GET", "PATCH", "DELETE"])
    def saved_conversation(chat_id):
        client_id = owner()
        with lock:
            if history.get(client_id, chat_id) is None:
                return jsonify(error="Conversation not found."), 404
            if request.method == "DELETE":
                history.delete(client_id, chat_id)
                conversations.pop((client_id, chat_id), None)
                return jsonify(ok=True)
            if request.method == "PATCH":
                payload = request.get_json(silent=True)
                title = payload.get("title") if isinstance(payload, dict) else None
                if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
                    return jsonify(error="Choose a title between 1 and 100 characters."), 400
                history.rename(client_id, chat_id, title.strip())
                return jsonify(conversation=history.summary(client_id, chat_id))
            return jsonify(conversation=history.summary(client_id, chat_id), messages=history.messages(client_id, chat_id))

    @app.route("/api/conversations/<chat_id>/images/<message_id>")
    def saved_image(chat_id, message_id):
        with lock:
            image = history.image(owner(), chat_id, message_id)
            if image is None:
                return jsonify(error="Image not found."), 404
            return Response(image["image"], mimetype=image["mime"])

    @app.route("/health")
    def health():
        return jsonify(
            status="ok", service="flamma", pid=os.getpid(),
            app_path=str(Path(__file__).resolve()),
        )

    @app.route("/")
    def home():
        if (frontend_dist / "index.html").is_file():
            return send_from_directory(frontend_dist, "index.html")
        return render_template("index.html")

    @app.route("/assets/<path:filename>")
    def frontend_asset(filename):
        return send_from_directory(frontend_dist / "assets", filename)

    @app.errorhandler(413)
    def upload_too_large(error):
        return jsonify(reply="Please upload an image smaller than 10 MB.", intent="image_rejected", confidence=None, followUps=[]), 413

    @app.route("/predict", methods=["POST"])
    def predict():
        nonlocal prototype
        payload = request.get_json(silent=True) if request.is_json else request.form
        if payload is None or not hasattr(payload, "get"):
            return jsonify(reply="Please send a message or image.", intent="unknown", confidence=None, followUps=[]), 400
        message = payload.get("message", "")
        conversation_id = payload.get("conversation_id", "default")
        if not isinstance(message, str) or not isinstance(conversation_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", conversation_id):
            return jsonify(reply="The message or conversation ID is invalid.", intent="unknown", confidence=None, followUps=[]), 400
        message = message.strip()
        image = request.files.get("image")
        if not message and image is None:
            return jsonify(reply="Please describe your skin concern or upload an image.", intent="unknown", confidence=0.0, followUps=[])

        client_id = owner()
        key = (client_id, conversation_id)
        # Keep a bounded model cache; restore older chats from local storage.
        with lock:
            if prototype is None:
                from model.semantic_chatbot import SemanticChatbot
                prototype = SemanticChatbot()
            if key not in conversations:
                conversations[key] = prototype.new_conversation()
                saved = history.get(client_id, conversation_id)
                if saved:
                    conversations[key].conversation.restore(json.loads(saved["state"]))
                if len(conversations) > 256:
                    conversations.popitem(last=False)
            conversations.move_to_end(key)
            bot = conversations[key]
            attachment, mime = None, None
            if image is not None:
                attachment = image.read()
                image.stream.seek(0)
                # Serve only supported image formats, never an upload's declared MIME.
                if attachment.startswith(b"\x89PNG\r\n\x1a\n"):
                    mime = "image/png"
                elif attachment.startswith(b"\xff\xd8\xff"):
                    mime = "image/jpeg"
                elif attachment.startswith(b"RIFF") and attachment[8:12] == b"WEBP":
                    mime = "image/webp"
                else:
                    attachment = None
            status = 200
            try:
                result = bot.reply(message, image=image)
            except ImageClassifierError:
                result = dict(reply="I couldn't reach the image classifier. Please try the image upload again shortly.",
                              intent="image_error", confidence=None, followUps=[])
                status = 503
            summary, messages = history.save_turn(
                client_id, conversation_id, message, result, bot.conversation.data, attachment, mime,
            )
        return jsonify({**result, "conversation": summary, "messages": messages}), status

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLAMMA_DEBUG") == "1", port=5000)
