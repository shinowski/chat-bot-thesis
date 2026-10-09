"""Verify the upstream image API contract without loading CNN weights or Gemini."""

import importlib.util
import io
import os
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from PIL import Image


class BackendUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend_dir = Path(__file__).resolve().parents[1] / 'Image/thesis-backend'
        classifier = ModuleType('inference.classifier')
        classifier.predict = Mock()
        detector = ModuleType('skin_detector')
        detector.looks_like_skin = Mock(return_value=True)
        with patch.dict(sys.modules, {'inference.classifier': classifier, 'skin_detector': detector}), patch.object(sys, 'path', [str(cls.backend_dir), *sys.path]):
            spec = importlib.util.spec_from_file_location('flamma_image_backend_test', cls.backend_dir / 'app.py')
            cls.backend = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.backend)
        cls.backend.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.backend.app.test_client()
        self.backend.predict.reset_mock()
        self.backend.predict.return_value = {
            'status': 'classified', 'predicted_class': 'psoriasis', 'confidence': .88,
            'is_confident': True, 'all_probabilities': {'psoriasis': .88},
            'gradcam': 'data:image/png;base64,fixture',
        }
        self.backend.looks_like_skin.return_value = True

    def upload(self):
        photo = io.BytesIO()
        Image.new('RGB', (8, 8), '#cc9980').save(photo, format='PNG')
        photo.seek(0)
        return self.client.post('/api/predict', data={'image': (photo, 'skin.png')})

    def test_health_preserves_launcher_identity(self):
        data = self.client.get('/health').get_json()
        self.assertEqual(data['service'], 'flamma-image')
        self.assertEqual(data['pid'], os.getpid())
        self.assertEqual(Path(data['app_path']), self.backend_dir / 'app.py')

    def test_prediction_without_gemini_keeps_scores_heatmap_and_upload_greeting(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.upload()
        self.assertEqual(result.status_code, 200)
        data = result.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['predicted_class'], 'psoriasis')
        self.assertEqual(data['all_probabilities'], {'psoriasis': .88})
        self.assertTrue(data['gradcam'].startswith('data:image/png;base64,'))
        self.assertIn('not a diagnosis', data['chat_greeting'])

    def test_normal_skin_upload_greeting_does_not_clear_the_patient(self):
        self.backend.predict.return_value.update(predicted_class='normal_skin')
        data = self.upload().get_json()
        self.assertEqual(data['condition'], 'No Supported Condition Detected')
        self.assertIn("isn't a clinical clearance", data['chat_greeting'])

    def test_skin_rejection_does_not_call_the_model(self):
        self.backend.looks_like_skin.return_value = False
        self.assertEqual(self.upload().get_json()['reason'], 'no_skin_detected')
        self.backend.predict.assert_not_called()

    def test_inconclusive_image_metadata_is_forwarded_as_a_rejection(self):
        self.backend.predict.return_value = {
            'status': 'inconclusive', 'message': 'More detail is needed.',
            'inconclusive_reasons': ['crop_disagreement'], 'normal_probability': .60, 'crop_disease_max': .45,
        }
        data = self.upload().get_json()
        self.assertEqual(data['status'], 'rejected')
        self.assertEqual(data['reason'], 'inconclusive')
        self.assertEqual(data['inconclusive_reasons'], ['crop_disagreement'])
        self.assertNotIn('predicted_class', data)

    def test_outside_scope_keeps_its_400_response_and_reason(self):
        self.backend.predict.return_value = {'status': 'outside_scope', 'message': 'Outside supported classes.', 'ood_score': .50, 'ood_threshold': .40}
        result = self.upload()
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.get_json()['reason'], 'out_of_scope')

    def test_upload_size_limit_is_preserved(self):
        result = self.client.post('/api/predict', data={'image': (io.BytesIO(b'x' * (10 * 1024 * 1024 + 1)), 'large.png')})
        self.addCleanup(result.request.environ['wsgi.input'].close)
        self.addCleanup(result.close)
        self.assertEqual(result.status_code, 413)
        self.backend.predict.assert_not_called()

    def test_optional_chat_returns_503_without_a_key_and_does_not_generate(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(self.backend, 'handle_chat') as generate:
            result = self.client.post('/api/chat', json={'question': 'What causes psoriasis?'})
        self.assertEqual(result.status_code, 503)
        self.assertIn('local chat', result.get_json()['error'])
        generate.assert_not_called()

    def test_chat_validates_json_question_and_cnn_result(self):
        for payload in [[], 'question', {}, {'question': 123}, {'question': ' '},
                        {'question': 'Help', 'cnn_result': []},
                        {'question': 'Help', 'cnn_result': {'label': []}},
                        {'question': 'Help', 'cnn_result': {'label': 'banana', 'confidence': .8}},
                        {'question': 'Help', 'cnn_result': {'label': 'psoriasis', 'confidence': 2}},
                        {'question': 'Help', 'cnn_result': {'label': 'psoriasis', 'confidence': True}}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/chat', json=payload).status_code, 400)

    def test_chat_passes_valid_question_and_cnn_context_when_configured(self):
        context = {'label': 'contact_dermatitis', 'confidence': .75}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}), patch.object(self.backend, 'handle_chat', return_value='Fixture answer.') as generate:
            result = self.client.post('/api/chat', json={'question': ' What does it mean? ', 'cnn_result': context})
        self.assertEqual(result.get_json(), {'response': 'Fixture answer.'})
        generate.assert_called_once_with(user_question='What does it mean?', cnn_result=context)

    def test_import_does_not_initialize_optional_models_or_google_sdk(self):
        namespace = self.backend.handle_chat.__globals__
        self.assertIsNone(namespace['retrieve'].__globals__['_model'])
        self.assertIsNone(namespace['generate_response'].__globals__['_client'])


if __name__ == '__main__':
    unittest.main()
