"""Check score claims, privacy disclosure, and artifact identity without patient data."""

import hashlib
import json
import os
from pathlib import Path
import pickle
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import create_app
from model.config import read_intent_artifact
from model.intent_classifier import IntentClassifier
from test_image_integration import make_bot


class PanelReadinessTests(unittest.TestCase):
    def test_privacy_questions_disclose_server_storage_and_actual_access_limits(self):
        for question in ['Is my information private?', 'Who can access my photos?',
                         'Is my data encrypted?', 'Are my photos encrypted?', 'Do you encrypt my data?']:
            bot = make_bot()
            reply = bot.reply(question)
            self.assertEqual(reply['intent'], 'bot_identity', question)
            for detail in ['Flamma server', 'not encrypted', 'browser profile', 'no account sign-in', 'backups']:
                self.assertIn(detail, reply['reply'], question)
            self.assertIsNone(bot.conversation.get('classification'))

    def test_percentage_questions_explain_what_the_benchmark_measures(self):
        for question in ['What do your scores mean?', 'What does 94.6% accuracy mean?',
                         'What does the confidence mean?', 'How accurate is this chatbot?']:
            bot = make_bot()
            reply = bot.reply(question)
            self.assertEqual(reply['intent'], 'bot_identity', question)
            self.assertIn('correct message categories', reply['reply'])
            self.assertIn('does not measure diagnostic accuracy', reply['reply'])
            self.assertIn('not established clinical accuracy', reply['reply'])

    def test_initial_photo_result_discloses_score_meaning(self):
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        result = make_bot().reply('', FileStorage(stream=BytesIO(b'fixture'), filename='skin.png'))
        self.assertEqual(result['intent'], 'image_classification')
        self.assertIn('not your probability', result['reply'])
        self.assertIn('not a confirmed diagnosis', result['reply'])

    def test_warning_signs_still_override_questions_about_accuracy_or_privacy(self):
        for text in ['How accurate is this chatbot? I cannot breathe',
                     'Is my data private? My lips are swollen']:
            self.assertEqual(make_bot().reply(text)['intent'], 'emergency')

    def test_artifact_is_checked_before_deserialization_and_recorded_in_health(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'candidate.pkl'
            artifact.write_bytes(pickle.dumps(SimpleNamespace(classes_=['symptom', 'unknown'])))
            checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = Path(directory) / 'active.json'
            manifest.write_text(json.dumps({'path': str(artifact), 'sha256': checksum}))
            with patch('model.config.ACTIVE_MODEL_MANIFEST', manifest), patch.dict(os.environ, {}, clear=True):
                classifier = IntentClassifier.__new__(IntentClassifier)
                classifier.load(artifact)
                self.assertEqual(classifier.model_sha256, checksum)
                bot = make_bot()
                bot.classifier = classifier
                app = create_app(bot, history_path=':memory:')
                self.addCleanup(app.extensions['chat_history'].db.close)
                self.assertEqual(app.test_client().get('/health').get_json()['intent_model_sha256'], checksum)
                artifact.write_bytes(b'changed artifact')
                with patch('model.intent_classifier.pickle.loads') as deserialize:
                    with self.assertRaisesRegex(OSError, 'manifest checksum'):
                        classifier.load(artifact)
                    deserialize.assert_not_called()

    def test_explicit_model_override_has_its_own_checksum_and_legacy_still_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'explicit.pkl'
            artifact.write_bytes(b'fixture for checksum calculation')
            manifest = Path(directory) / 'active.json'
            manifest.write_text(json.dumps({'path': str(artifact), 'sha256': '0' * 64}))
            with patch('model.config.ACTIVE_MODEL_MANIFEST', manifest), patch.dict(os.environ, {'FLAMMA_INTENT_MODEL': str(artifact)}):
                _, data, checksum = read_intent_artifact()
                self.assertEqual(checksum, hashlib.sha256(data).hexdigest())
            with patch('model.config.ACTIVE_MODEL_MANIFEST', Path(directory) / 'missing.json'), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(read_intent_artifact(artifact)[1], artifact.read_bytes())

    def test_selected_manifest_requires_a_valid_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'model.pkl'
            artifact.write_bytes(b'fixture')
            manifest = Path(directory) / 'active.json'
            for expected in [None, 'invalid', '0' * 64]:
                manifest.write_text(json.dumps({'path': str(artifact), 'sha256': expected}))
                with patch('model.config.ACTIVE_MODEL_MANIFEST', manifest), patch.dict(os.environ, {}, clear=True):
                    with self.assertRaises(OSError):
                        read_intent_artifact()


if __name__ == '__main__':
    unittest.main()
