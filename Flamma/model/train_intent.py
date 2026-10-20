"""Train a balanced candidate with grouped validation and a frozen test set."""

import hashlib
import json
import os
import pickle
import platform
import re
import tempfile
import warnings
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from model.config import PROJECT_DIR, intent_model_path, ACTIVE_MODEL_MANIFEST
from model.intent_classifier import IntentClassifier
from model.text_understanding import clean_message, normalize_message
from model.training_data import default_training_paths, load_training_examples


def next_candidate_path():
    """Pick the next version without replacing previous models or reports."""
    versions = [4]
    for path in (PROJECT_DIR / 'artifacts').glob('intent_v*'):
        match = re.fullmatch(r'intent_v(\d+)\.(?:pkl|metadata\.json)', path.name)
        if match:
            versions.append(int(match.group(1)))
    return PROJECT_DIR / 'artifacts' / f'intent_v{max(versions) + 1}.pkl'


def metrics(expected, predicted):
    return {
        'accuracy': float(accuracy_score(expected, predicted)),
        'macro_f1': float(f1_score(expected, predicted, average='macro', zero_division=0)),
        'per_intent': classification_report(expected, predicted, output_dict=True, zero_division=0),
    }


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def train_candidate(output, additional_sources=None):
    from eval.final_test_cases import FINAL_TEST_CASES

    output = Path(output).resolve()
    baseline_path = intent_model_path().resolve()
    if output == baseline_path:
        raise ValueError('Train a separate candidate; never overwrite the active model.')
    if output.exists() or output.with_suffix('.metadata.json').exists():
        raise ValueError('A candidate already exists at this path; choose a new version to preserve its report.')
    paths = [*default_training_paths(), *(additional_sources or [])]
    examples, audit = load_training_examples(paths)
    texts = [item['text'] for item in examples]
    labels = np.array([item['label'] for item in examples])
    groups = np.array([item['group'] for item in examples])
    test_texts = [normalize_message(text) for text, _ in FINAL_TEST_CASES]
    test_labels = [label for _, label in FINAL_TEST_CASES]
    overlap = set(map(clean_message, texts)) & set(map(clean_message, test_texts))
    if overlap:
        raise ValueError('Training examples overlap the frozen test set: ' + repr(sorted(overlap)))
    print(json.dumps({'training_audit': audit}, indent=2), flush=True)
    classifier = IntentClassifier()
    versions = {name: version(name) for name in ['scikit-learn', 'sentence-transformers', 'torch', 'numpy']}
    embedding_key = hashlib.sha256(json.dumps({'texts': texts, 'model': classifier.semantic_model.model_name, 'versions': versions}).encode()).hexdigest()
    cache_path = PROJECT_DIR / 'artifacts' / ('embeddings-' + embedding_key[:16] + '.npz')
    if cache_path.exists():
        with np.load(cache_path, allow_pickle=False) as cached:
            embeddings = cached['embeddings']
        if embeddings.shape != (len(texts), 384) or not np.isfinite(embeddings).all():
            raise ValueError('The embedding cache is invalid.')
        print('Using cached training embeddings.', flush=True)
    else:
        print(f'Embedding {len(texts)} fictional training examples...', flush=True)
        embeddings = classifier.semantic_model.encode(texts)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, embeddings=embeddings)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train, validation = next(splitter.split(texts, labels, groups))
    if set(groups[train]) & set(groups[validation]):
        raise AssertionError('Template groups leaked across the split.')
    if set(labels[train]) != set(labels) or set(labels[validation]) != set(labels):
        raise ValueError('Grouped validation must cover every intent.')
    candidates = []
    for regularization in [0.5, 1.0, 2.0]:
        candidate = LogisticRegression(C=regularization, max_iter=2000, class_weight='balanced', random_state=42)
        candidate.fit(embeddings[train], labels[train])
        score = metrics(labels[validation], candidate.predict(embeddings[validation]))
        candidates.append({'C': regularization, 'metrics': score})
        print(f"Grouped validation C={regularization}: macro F1={score['macro_f1']:.3f}", flush=True)
    selected = max(candidates, key=lambda item: (item['metrics']['macro_f1'], -item['C']))
    classifier.classifier = LogisticRegression(C=selected['C'], max_iter=2000, class_weight='balanced', random_state=42)
    classifier.classifier.fit(embeddings, labels)
    artifact = pickle.dumps(classifier.classifier)
    atomic_write(output, artifact)

    # The test set is used after parameter selection, never for fitting.
    test_embeddings = classifier.semantic_model.encode(test_texts)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        baseline = pickle.loads(baseline_path.read_bytes())
    baseline_predictions = baseline.predict(test_embeddings)
    candidate_predictions = classifier.classifier.predict(test_embeddings)
    before, after = metrics(test_labels, baseline_predictions), metrics(test_labels, candidate_predictions)
    report = {
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'english_text_intent_classification_only',
        'embedding_model': classifier.semantic_model.model_name,
        'embedding_cache_key': embedding_key,
        'python_version': platform.python_version(), 'runtime_versions': versions,
        'model_path': str(output), 'model_sha256': hashlib.sha256(artifact).hexdigest(),
        'baseline_path': str(baseline_path), 'baseline_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        'training_audit': audit,
        'validation': {
            'method': 'StratifiedGroupKFold, fold 0 of 5', 'seed': 42,
            'grouping': 'normalized_templates_with_area_symptom_duration_severity_product_slots_v2',
            'train_examples': len(train), 'validation_examples': len(validation),
            'train_class_counts': dict(Counter(labels[train])), 'validation_class_counts': dict(Counter(labels[validation])),
            'overlapping_groups': 0, 'candidates': candidates, 'selected_C': selected['C'],
        },
        'frozen_test': {
            'evaluation_role': 'reused_authored_benchmark_not_untouched_final_validation',
            'examples': len(test_labels), 'training_overlap': 0,
            'test_sha256': hashlib.sha256(json.dumps(FINAL_TEST_CASES).encode()).hexdigest(),
            'baseline': before, 'candidate': after,
            'predictions': [dict(text=text, expected=expected, baseline=str(old), candidate=str(new))
                            for (text, expected), old, new in zip(FINAL_TEST_CASES, baseline_predictions, candidate_predictions)],
        },
        'quality_gate_passed': after['accuracy'] > before['accuracy'] and after['macro_f1'] > before['macro_f1'],
    }
    metadata_path = output.with_suffix('.metadata.json')
    atomic_write(metadata_path, json.dumps(report, indent=2).encode())
    print(json.dumps({'baseline_accuracy': before['accuracy'], 'candidate_accuracy': after['accuracy'],
                      'baseline_macro_f1': before['macro_f1'], 'candidate_macro_f1': after['macro_f1'],
                      'quality_gate_passed': report['quality_gate_passed'], 'metadata': str(metadata_path)}, indent=2), flush=True)
    return report


def activate_candidate(path):
    path = Path(path).resolve()
    report = json.loads(path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if report.get('quality_gate_passed') is not True or report.get('model_sha256') != checksum:
        raise ValueError('Only the verified candidate recorded in a passing report can be activated.')
    current_checksum = hashlib.sha256(intent_model_path().read_bytes()).hexdigest()
    if report.get('baseline_sha256') != current_checksum:
        raise ValueError('The active baseline changed after evaluation; compare this candidate again before activating it.')
    try:
        selected_path = str(path.relative_to(PROJECT_DIR))
    except ValueError:
        selected_path = str(path)
    atomic_write(ACTIVE_MODEL_MANIFEST, json.dumps({
        'path': selected_path, 'sha256': checksum,
        'activated_at': datetime.now(timezone.utc).isoformat(),
        'baseline_path': report['baseline_path'],
    }, indent=2).encode())
