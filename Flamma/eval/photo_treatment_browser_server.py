"""Isolated UI fixture: real chat model, simulated photo labels, no image service.

Run with the project's Python environment, then browser_photo_treatments.mjs.
Fixture uploads are named after a supported class. These tests do not measure
image-model or clinical accuracy, and keep their history in memory only.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from model.semantic_chatbot import SemanticChatbot


class FixtureImages:
    def predict(self, upload):
        label = Path(upload.filename).stem
        if label == 'rejected':
            return {'status': 'rejected', 'reason': 'low_confidence'}
        score = .997 if label == 'contact_dermatitis' else .88
        return dict(status='ok', predicted_class=label, confidence=score,
                    condition=label.replace('_', ' ').title(), all_probabilities={label: score})


if __name__ == '__main__':
    bot = SemanticChatbot(image_classifier=FixtureImages())
    create_app(bot, history_path=':memory:').run(host='127.0.0.1', port=5010, debug=False)
