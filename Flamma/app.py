import os
import re
import secrets
import json
import hashlib
from datetime import timedelta
from collections import OrderedDict
from pathlib import Path
from threading import Lock, RLock, Thread
from uuid import uuid4

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, session

from model.image_classifier import ImageClassifierError
from model.chat_history import ChatHistory
from model.request_locks import OwnerLocks
from model.conversation import Conversation
from model.safety import safety_intent, safety_response
from model.errors import TextModelUnavailable


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
    history_lock = RLock()
    cache_lock = RLock()
    model_lock = Lock()
    owner_locks = OwnerLocks()
    prototype = chatbot
    history = ChatHistory(history_path)
    app.extensions["chat_history"] = history

    def warm_chat_model():
        """Begin cached model initialization before the first user message."""
        def warm():
            nonlocal prototype
            with model_lock:
                if prototype is not None:
                    return
                try:
                    from model.semantic_chatbot import SemanticChatbot
                    prototype = SemanticChatbot()
                except (TextModelUnavailable, OSError):
                    app.logger.warning('The local chat model could not be loaded during startup.')
        worker = Thread(target=warm, name='flamma-chat-startup', daemon=True)
        worker.start()
        return worker

    app.extensions['warm_chat_model'] = warm_chat_model

    def owner():
        session.permanent = True
        return session.setdefault("client_id", uuid4().hex)

    def attachment_data(image):
        if image is None:
            return None, None
        attachment = image.read()
        image.stream.seek(0)
        # Serve supported image formats, never an upload's declared MIME.
        if attachment.startswith(b"\x89PNG\r\n\x1a\n"):
            return attachment, "image/png"
        if attachment.startswith(b"\xff\xd8\xff"):
            return attachment, "image/jpeg"
        if attachment.startswith(b"RIFF") and attachment[8:12] == b"WEBP":
            return attachment, "image/webp"
        return None, None

    def restore_conversation(conversation, client_id, chat_id):
        saved = history.get(client_id, chat_id)
        if saved:
            conversation.restore(json.loads(saved["state"]))
            # Older releases saved service failures with a stale successful
            # prediction. The saved exchange is the evidence for invalidation.
            latest = history.latest_image_result(client_id, chat_id)
            if latest and latest['intent'] in {'image_error', 'image_rejected'} and conversation.get('classification') is not None:
                conversation.invalidate_image_result(latest['text'])

    @app.after_request
    def private_responses(response):
        if request.path.startswith("/api/") or request.path == "/predict":
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/api/conversations", methods=["GET", "DELETE"])
    def conversation_list():
        client_id = owner()
        if request.method == "DELETE":
            with owner_locks.hold(client_id), cache_lock, history_lock:
                history.delete(client_id)
                for key in list(conversations):
                    if key[0] == client_id:
                        del conversations[key]
                return jsonify(ok=True)
        with history_lock:
            return jsonify(conversations=history.list(client_id, request.args.get("q", "").strip()))

    @app.route("/api/conversations/<chat_id>", methods=["GET", "PATCH", "DELETE"])
    def saved_conversation(chat_id):
        client_id = owner()
        if request.method == "GET":
            with history_lock:
                if history.get(client_id, chat_id) is None:
                    return jsonify(error="Conversation not found."), 404
                return jsonify(conversation=history.summary(client_id, chat_id), messages=history.messages(client_id, chat_id))
        with owner_locks.hold(client_id), cache_lock, history_lock:
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
        with history_lock:
            image = history.image(owner(), chat_id, message_id)
            if image is None:
                return jsonify(error="Image not found."), 404
            return Response(image["image"], mimetype=image["mime"])

    @app.route("/health")
    def health():
        return jsonify(
            status="ok", service="flamma", pid=os.getpid(),
            app_path=str(Path(__file__).resolve()),
            warning_checks="rules_v1",
            chat_model="ready" if prototype is not None else "loading" if model_lock.locked() else "not_loaded",
            intent_model=Path(prototype.classifier.model_path).name if getattr(getattr(prototype, 'classifier', None), 'model_path', None) else None,
            intent_model_sha256=getattr(getattr(prototype, 'classifier', None), 'model_sha256', None),
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
        request_id = payload.get('request_id')
        if request_id is not None and (not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', request_id)):
            return jsonify(reply='The request ID is invalid.', intent='text_error', confidence=None, followUps=[]), 400
        if not isinstance(message, str) or not isinstance(conversation_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", conversation_id):
            return jsonify(reply="The message or conversation ID is invalid.", intent="unknown", confidence=None, followUps=[]), 400
        message = message.strip()
        image = request.files.get("image")
        if not message and image is None:
            return jsonify(reply="Please describe your skin concern or upload an image.", intent="unknown", confidence=0.0, followUps=[])

        client_id = owner()
        key = (client_id, conversation_id)
        attachment, mime = attachment_data(image)
        fingerprint = None
        if request_id:
            digest = hashlib.sha256(json.dumps(
                {'message': message, 'image_filename': image.filename if image is not None else None},
                sort_keys=True, ensure_ascii=False, separators=(',', ':'),
            ).encode('utf-8'))
            if image is not None:
                digest.update(image.read())
                image.stream.seek(0)
            fingerprint = digest.hexdigest()
        # Browser mutations serialize so deletion cannot resurrect an in-flight
        # chat. Database and cache locks cover only short local operations.
        with owner_locks.hold(client_id):
            if request_id:
                with history_lock:
                    receipt = history.request_receipt(client_id, conversation_id, request_id)
                if receipt is not None:
                    if receipt['fingerprint'] != fingerprint:
                        return jsonify(reply='This retry contains a different message or photo. Send it as a new message.',
                                       intent='text_error', confidence=None, followUps=[]), 409
                    return jsonify(receipt['response']), receipt['status']
            safety = safety_intent(message)
            if safety:
                # Warning replies must not wait for a cold model download/load.
                # Mutate a cached conversation, or persist state for later restore.
                with cache_lock, history_lock:
                    cached = conversations.get(key)
                    conversation = cached.conversation if cached else Conversation()
                    if cached is None:
                        restore_conversation(conversation, client_id, conversation_id)
                    if image is not None:
                        conversation.invalidate_image_result("The latest photo was not classified; please follow the safety advice in this reply.")
                    result = safety_response(safety, conversation, message)
                    summary, messages = history.save_turn(
                        client_id, conversation_id, message, result, conversation.data, attachment, mime,
                        request_id=request_id, fingerprint=fingerprint,
                    )
                return jsonify({**result, "conversation": summary, "messages": messages, 'requestId': request_id})
            if not model_lock.acquire(timeout=30):
                return jsonify(reply="Chat is still starting. Please try again shortly.",
                               intent="text_error", confidence=None, followUps=[]), 503
            try:
                if prototype is None:
                    from model.semantic_chatbot import SemanticChatbot
                    prototype = SemanticChatbot()
            except (TextModelUnavailable, OSError):
                app.logger.warning("The local chat model could not be loaded.")
                return jsonify(reply="The chat model isn't available on this computer yet. Please check the model setup before trying again.",
                               intent="text_error", confidence=None, followUps=[]), 503
            finally:
                model_lock.release()
            with cache_lock, history_lock:
                if key not in conversations:
                    conversations[key] = prototype.new_conversation()
                    restore_conversation(conversations[key].conversation, client_id, conversation_id)
                    if len(conversations) > 256:
                        conversations.popitem(last=False)
                conversations.move_to_end(key)
                bot = conversations[key]
            status = 200
            try:
                result = bot.reply(message, image=image)
            except ImageClassifierError:
                result = dict(reply="I couldn't reach the image classifier. Please try the image upload again shortly.",
                              intent="image_error", confidence=None, followUps=[])
                bot.conversation.invalidate_image_result(result["reply"])
                bot.conversation.set("last_reply_intent", "image_error")
                bot.conversation.set("pending_question", None)
                status = 503
            if result["intent"] == "image_error":
                status = 503
            with history_lock:
                summary, messages = history.save_turn(
                    client_id, conversation_id, message, result, bot.conversation.data, attachment, mime,
                    request_id=request_id, fingerprint=fingerprint, response_status=status,
                )
        return jsonify({**result, "conversation": summary, "messages": messages, 'requestId': request_id}), status

    return app


app = create_app()

if __name__ == "__main__":
    if os.environ.get('FLAMMA_DEBUG') != '1' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        app.extensions['warm_chat_model']()
    app.run(debug=os.environ.get("FLAMMA_DEBUG") == "1", port=5000)
