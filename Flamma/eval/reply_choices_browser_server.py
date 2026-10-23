"""Isolated quick-reply UI fixture: real text model, simulated photo labels.

Run with the project Python, then browser_reply_choices.mjs. History stays in
memory, uploads are test fixtures, and no image-accuracy claim is made.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from eval.photo_treatment_browser_server import FixtureImages
from model.semantic_chatbot import SemanticChatbot


if __name__ == '__main__':
    chatbot = SemanticChatbot(image_classifier=FixtureImages())
    create_app(chatbot, history_path=':memory:').run(host='127.0.0.1', port=5017, debug=False)
