"""Compare raw text intents on authored examples, not clinical accuracy.

Run after training; never fit or select parameters with these results.
"""

import argparse
import hashlib
import json
from pathlib import Path
import pickle
import warnings

from model.config import PROJECT_DIR
from model.semantic_model import SemanticModel
from model.text_understanding import clean_message, normalize_message
from model.train_intent import metrics
from model.training_data import example_group, load_training_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=PROJECT_DIR / 'eval/intent_generalization_cases.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    rows = [(text, item['intent']) for item in cases for text in item['texts']]
    texts, expected = zip(*rows)
    normalized = [normalize_message(text) for text in texts]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        baseline = pickle.loads(args.baseline.read_bytes())
        candidate = pickle.loads(args.candidate.read_bytes())
    if set(baseline.classes_) != set(candidate.classes_) or not set(expected) <= set(candidate.classes_):
        raise ValueError('The compared models and evaluation labels must use the same intent taxonomy.')
    metadata = json.loads(args.candidate.with_suffix('.metadata.json').read_text(encoding='utf-8'))
    examples, _ = load_training_examples([Path(source['path']) for source in metadata['training_audit']['sources']])
    training = {clean_message(item['text']) for item in examples}
    if training & set(map(clean_message, texts)):
        raise ValueError('Generalization messages overlap training examples; this is not a held-out comparison.')
    embeddings = SemanticModel().encode(normalized)
    old, new = baseline.predict(embeddings), candidate.predict(embeddings)
    before, after = metrics(expected, old), metrics(expected, new)
    report = {
        'scope': 'authored_english_text_intent_comparison_not_clinical_validation',
        'examples': len(rows), 'exact_training_overlap': 0,
        'template_group_overlap': len({example_group(text) for text in texts} & {item['group'] for item in examples}),
        'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        'baseline_path': str(args.baseline.resolve()),
        'candidate_path': str(args.candidate.resolve()),
        'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
        'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'baseline': before, 'candidate': after,
        'no_aggregate_regression': after['accuracy'] >= before['accuracy'] and after['macro_f1'] >= before['macro_f1'],
        'predictions': [dict(text=text, expected=label, baseline=str(left), candidate=str(right))
                        for (text, label), left, right in zip(rows, old, new)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['examples', 'exact_training_overlap', 'template_group_overlap',
                                                'no_aggregate_regression']}, indent=2))
    print(json.dumps({'baseline_accuracy': before['accuracy'], 'candidate_accuracy': after['accuracy'],
                      'baseline_macro_f1': before['macro_f1'], 'candidate_macro_f1': after['macro_f1']}, indent=2))
    if not report['no_aggregate_regression']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
