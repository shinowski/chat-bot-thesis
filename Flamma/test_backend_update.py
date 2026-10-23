"""Verify the partner image API, quality gates, and Flamma integration contract."""

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
        classifier.MODEL_INFO = {'checkpoint': 'fixture.pth', 'sha256': 'a' * 64}
        detector = ModuleType('inference.skin_detector')
        detector.looks_like_skin = Mock(return_value=True)
        blur = ModuleType('inference.blur_check')
        blur.blur_status = Mock(return_value=('ok', 42.0))
        with patch.dict(sys.modules, {'inference.classifier': classifier, 'inference.skin_detector': detector,
                                      'inference.blur_check': blur}), patch.object(sys, 'path', [str(cls.backend_dir), *sys.path]):
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
        self.backend.blur_status.reset_mock()
        self.backend.blur_status.return_value = ('ok', 42.0)

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
        self.assertEqual(data['model']['checkpoint'], 'fixture.pth')
        self.assertEqual(data['model']['sha256'], 'a' * 64)

    def test_prediction_without_api_keys_keeps_scores_heatmap_and_quality(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.upload()
        self.assertEqual(result.status_code, 200)
        data = result.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['predicted_class'], 'psoriasis')
        self.assertEqual(data['all_probabilities'], {'psoriasis': .88})
        self.assertTrue(data['gradcam'].startswith('data:image/png;base64,'))
        self.assertEqual(data['quality'], {'blur_status': 'ok', 'blur_score': 42.0})

    def test_normal_skin_upload_greeting_does_not_clear_the_patient(self):
        self.backend.predict.return_value.update(predicted_class='normal_skin')
        data = self.upload().get_json()
        self.assertEqual(data['condition'], 'No Supported Condition Detected')
        self.assertIn('not a clearance', data['description'])

    def test_blurry_photo_is_rejected_before_skin_check_or_model_inference(self):
        self.backend.blur_status.return_value = ('blocked', 1.2)
        with patch.object(self.backend, 'looks_like_skin') as skin_check:
            response = self.upload()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['reason'], 'too_blurry')
        self.assertEqual(response.get_json()['quality']['blur_score'], 1.2)
        self.backend.predict.assert_not_called()
        skin_check.assert_not_called()

    def test_blur_warning_is_visible_without_blocking_an_accepted_result(self):
        self.backend.blur_status.return_value = ('warn', 10.1234)
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')
        self.assertEqual(response.get_json()['quality'], {'blur_status': 'warn', 'blur_score': 10.12})

    def test_image_orientation_is_normalized_before_all_pipeline_stages(self):
        photo = io.BytesIO()
        image = Image.new('RGB', (12, 8), '#cc9980')
        exif = image.getexif()
        exif[274] = 6
        image.save(photo, format='JPEG', exif=exif)
        photo.seek(0)
        self.client.post('/api/predict', data={'image': (photo, 'portrait.jpg')})
        self.assertEqual(self.backend.blur_status.call_args.args[0].size, (8, 12))
        self.assertEqual(self.backend.predict.call_args.args[0].size, (8, 12))

    def test_invalid_or_missing_upload_does_not_run_the_model(self):
        for body in [{}, {'image': (io.BytesIO(b'not an image'), 'invalid.jpg')},
                     {'image': (io.BytesIO(b'anything'), 'payload.txt')}]:
            with self.subTest(body=list(body)):
                response = self.client.post('/api/predict', data=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()['status'], 'rejected')
        self.backend.predict.assert_not_called()

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
        self.assertEqual(result.get_json()['reason'], 'too_large')
        self.backend.predict.assert_not_called()

    def test_image_backend_no_longer_exposes_the_removed_cloud_chat_endpoint(self):
        self.assertEqual(self.client.post('/api/chat', json={'question': 'Hello'}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
