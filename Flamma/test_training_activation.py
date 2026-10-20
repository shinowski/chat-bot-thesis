"""Candidate activation must refer to the exact evaluated baseline and artifact."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model.train_intent import activate_candidate, train_candidate, next_candidate_path


class TrainingActivationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.baseline = self.root / 'baseline.pkl'
        self.candidate = self.root / 'candidate.pkl'
        self.manifest = self.root / 'active.json'
        self.baseline.write_bytes(b'original baseline')
        self.candidate.write_bytes(b'evaluated candidate')
        self.report = {
            'quality_gate_passed': True,
            'model_sha256': hashlib.sha256(self.candidate.read_bytes()).hexdigest(),
            'baseline_sha256': hashlib.sha256(self.baseline.read_bytes()).hexdigest(),
            'baseline_path': str(self.baseline),
        }
        self.write_report()
        self.baseline_patch = patch('model.train_intent.intent_model_path', return_value=self.baseline)
        self.baseline_patch.start()
        self.addCleanup(self.baseline_patch.stop)
        self.manifest_patch = patch('model.train_intent.ACTIVE_MODEL_MANIFEST', self.manifest)
        self.manifest_patch.start()
        self.addCleanup(self.manifest_patch.stop)

    def write_report(self):
        self.candidate.with_suffix('.metadata.json').write_text(json.dumps(self.report), encoding='utf-8')

    def test_verified_candidate_can_be_selected_without_overwriting_the_baseline(self):
        activate_candidate(self.candidate)
        selected = json.loads(self.manifest.read_text())
        self.assertEqual(selected['sha256'], self.report['model_sha256'])
        self.assertEqual(self.baseline.read_bytes(), b'original baseline')

    def test_changed_baseline_cannot_use_a_stale_passing_report(self):
        self.baseline.write_bytes(b'a different active model')
        with self.assertRaisesRegex(ValueError, 'baseline changed'):
            activate_candidate(self.candidate)
        self.assertFalse(self.manifest.exists())

    def test_changed_candidate_and_failed_gate_cannot_be_activated(self):
        for modified in ['artifact', 'gate']:
            with self.subTest(modified=modified):
                if modified == 'artifact':
                    self.candidate.write_bytes(b'unverified artifact')
                else:
                    self.candidate.write_bytes(b'evaluated candidate')
                    self.report['quality_gate_passed'] = False
                    self.write_report()
                with self.assertRaisesRegex(ValueError, 'verified candidate'):
                    activate_candidate(self.candidate)
                self.assertFalse(self.manifest.exists())

    def test_training_does_not_overwrite_a_previous_candidate(self):
        with self.assertRaisesRegex(ValueError, 'candidate already exists'):
            train_candidate(self.candidate)
        self.assertEqual(self.candidate.read_bytes(), b'evaluated candidate')

    def test_default_candidate_version_preserves_models_and_metadata_only_runs(self):
        artifacts = self.root / 'artifacts'
        artifacts.mkdir()
        (artifacts / 'intent_v5.pkl').write_bytes(b'previous')
        (artifacts / 'intent_v7.metadata.json').write_text('{}')
        (artifacts / 'intent_v999-unrelated.txt').write_text('unrelated')
        with patch('model.train_intent.PROJECT_DIR', self.root):
            self.assertEqual(next_candidate_path(), artifacts / 'intent_v8.pkl')


if __name__ == '__main__':
    unittest.main()
