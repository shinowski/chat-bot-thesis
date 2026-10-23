"""Engineering checks for the updated image pipeline, not clinical accuracy."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image


BACKEND = Path(__file__).resolve().parents[1] / 'Image/thesis-backend'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImageProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blur = load_module('partner_blur_tests', BACKEND / 'inference/blur_check.py')
        cls.skin = load_module('partner_skin_tests', BACKEND / 'inference/skin_detector.py')
        cls.cam = load_module('partner_cam_tests', BACKEND / 'inference/gradcam.py')

    def test_flat_and_sharp_fixtures_have_different_blur_outcomes(self):
        flat = Image.new('RGB', (256, 256), '#be876e')
        pattern = (np.indices((256, 256)).sum(axis=0) // 4 % 2 * 255).astype(np.uint8)
        sharp = Image.fromarray(pattern).convert('RGB')
        self.assertEqual(self.blur.blur_status(flat)[0], 'blocked')
        self.assertEqual(self.blur.blur_status(sharp)[0], 'ok')

    def test_crop_boxes_stay_inside_original_photos_across_aspect_ratios(self):
        for width, height in [(240, 320), (320, 240), (512, 512), (2400, 8), (1, 1000)]:
            with self.subTest(size=(width, height)):
                pixels = np.full((height, width, 3), [0, 0, 255], dtype=np.uint8)
                pixels[:max(1, height // 2), :] = [190, 135, 110]
                image = Image.fromarray(pixels)
                crops, boxes = self.skin.get_skin_crops_with_boxes(image, n_crops=5)
                self.assertTrue(1 <= len(crops) <= 5)
                self.assertEqual(len(crops), len(boxes))
                for crop, (left, top, right, bottom) in zip(crops, boxes):
                    self.assertTrue(0 <= left < right <= width)
                    self.assertTrue(0 <= top < bottom <= height)
                    self.assertEqual(crop.size, (right - left, bottom - top))

    def test_closeup_skin_fixture_is_not_cropped_unnecessarily(self):
        image = Image.new('RGB', (80, 120), (190, 135, 110))
        crops, boxes = self.skin.get_skin_crops_with_boxes(image)
        self.assertEqual(boxes, [(0, 0, 80, 120)])
        self.assertEqual(crops[0].size, image.size)

    def test_stitched_heatmap_is_finite_and_uncovered_pixels_keep_the_photo(self):
        cams = [np.array([[0, .1], [.5, 1]], dtype=np.float32), np.full((2, 2), .6, dtype=np.float32)]
        cam, covered = self.cam.stitch_cams(cams, [(0, 0, 12, 12), (8, 8, 20, 20)], (32, 24))
        self.assertEqual(cam.shape, (24, 32))
        self.assertTrue(np.isfinite(cam).all())
        self.assertTrue(0 <= float(cam.min()) <= float(cam.max()) <= 1)
        image = Image.new('RGB', (32, 24), '#be876e')
        overlay = self.cam.create_gradcam_overlay(image, cam, covered)
        np.testing.assert_array_equal(overlay[~covered], np.array(image)[~covered])


class ImageModelGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(sys, 'path', [str(BACKEND), *sys.path]):
            cls.active = load_module('partner_gate_classifier_tests', BACKEND / 'inference/classifier.py')
        cls.addClassCleanup(cls.active._gradcam.remove_hooks)

    def controlled_prediction(self, normal_scores, disease_scores, ood=None):
        import torch
        module = self.active
        normal_index = module._normal_idx
        disease_index = module._disease_idxs[0]
        rows = []
        for normal, disease in zip(normal_scores, disease_scores):
            row = torch.full((len(module._idx_to_class),), (1 - normal - disease) / (len(module._idx_to_class) - 2))
            row[normal_index], row[disease_index] = normal, disease
            rows.append(torch.log(row))
        image = Image.new('RGB', (32, 32), '#be876e')
        crops = [image] * len(rows)
        boxes = [(0, 0, 32, 32)] * len(rows)
        cam = Mock()
        cam.generate.return_value = np.array([[0, .1], [.5, 1]], dtype=np.float32)
        with patch.object(module, '_model', return_value=torch.stack(rows).to(module.DEVICE)), \
             patch.object(module, 'get_skin_crops_with_boxes', return_value=(crops, boxes)), \
             patch.object(module, '_ood_score', return_value=0 if ood is None else ood), \
             patch.object(module, '_gradcam', cam):
            result = module.predict(image)
        return result, cam

    def test_selected_checkpoint_is_the_new_partner_model(self):
        self.assertEqual(self.active.MODEL_INFO['checkpoint'], 'resnet50_skin_finale_oe.pth')
        self.assertRegex(self.active.MODEL_INFO['sha256'], r'^[a-f0-9]{64}$')
        self.assertTrue(self.active.MODEL_INFO['normal_gate_enabled'])
        self.assertEqual(self.active.MODEL_INFO['skin_crops'], 5)

    def test_uncertain_normal_match_is_inconclusive_and_has_no_heatmap(self):
        result, cam = self.controlled_prediction([.6], [.2])
        self.assertEqual(result['status'], 'inconclusive')
        self.assertTrue(result['inconclusive_reasons']['normal_confidence_too_low'])
        self.assertIsNone(result['predicted_class'])
        cam.generate.assert_not_called()

    def test_disease_like_crop_can_veto_a_high_averaged_normal_score(self):
        result, cam = self.controlled_prediction([.9999, .45], [.00002, .51])
        self.assertGreaterEqual(result['normal_probability'], self.active.NORMAL_MIN_CONFIDENCE)
        self.assertEqual(result['status'], 'inconclusive')
        self.assertTrue(result['inconclusive_reasons']['disease_pattern_in_a_crop'])
        cam.generate.assert_not_called()

    def test_accepted_prediction_returns_a_stitched_png_heatmap(self):
        result, cam = self.controlled_prediction([.99, .99], [.002, .002])
        self.assertEqual(result['status'], 'classified')
        self.assertEqual(result['predicted_class'], 'normal_skin')
        self.assertTrue(result['gradcam'].startswith('data:image/png;base64,'))
        self.assertGreaterEqual(cam.generate.call_count, 2)

    def test_ood_rejection_precedes_normal_gate_and_heatmap(self):
        result, cam = self.controlled_prediction([.99], [.002], ood=self.active.OOD_THRESHOLD + 1)
        self.assertEqual(result['status'], 'outside_scope')
        self.assertIsNone(result['predicted_class'])
        cam.generate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
