"""Shared model selection for application, training, and evaluation."""

import os
import json
import hashlib
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ACTIVE_MODEL_MANIFEST = PROJECT_DIR / 'artifacts/active_intent_model.json'


def intent_model_path():
    configured = os.environ.get('FLAMMA_INTENT_MODEL')
    if configured is None and ACTIVE_MODEL_MANIFEST.exists():
        try:
            configured = json.loads(ACTIVE_MODEL_MANIFEST.read_text(encoding='utf-8'))['path']
            if not isinstance(configured, str) or not configured:
                raise ValueError('Missing path')
        except (ValueError, KeyError, TypeError) as error:
            raise OSError('The active intent model manifest is invalid.') from error
    path = Path(configured or 'semantic_classifier.pkl')
    return path if path.is_absolute() else PROJECT_DIR / path


def read_intent_artifact(path=None):
    """Check the selected manifest before deserializing the local artifact."""
    selected = Path(path if path is not None else intent_model_path()).resolve()
    artifact = selected.read_bytes()
    checksum = hashlib.sha256(artifact).hexdigest()
    if os.environ.get('FLAMMA_INTENT_MODEL') is None and ACTIVE_MODEL_MANIFEST.exists() and selected == intent_model_path().resolve():
        manifest = json.loads(ACTIVE_MODEL_MANIFEST.read_text(encoding='utf-8'))
        expected = manifest.get('sha256')
        if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected) or checksum != expected:
            raise OSError('The selected intent model does not match its manifest checksum.')
    return selected, artifact, checksum
