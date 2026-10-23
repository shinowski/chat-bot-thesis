"""Read local model evidence and produce an adviser report without retraining."""
from pathlib import Path
import csv
import hashlib
import html
import json
import os
import pickle
import sys
import warnings
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FLAMMA = ROOT / 'Flamma'
sys.path.insert(0, str(FLAMMA))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from model.semantic_model import SemanticModel
from model.text_understanding import normalize_message
from model.training_data import load_training_examples
from eval.final_test_cases import FINAL_TEST_CASES


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, default=str) + '\n', encoding='utf-8')


def write_csv(name, rows, columns=None):
    if not rows:
        return
    with (OUT / name).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pct(value):
    return 'Unavailable' if value is None else f'{100 * value:.2f}%'


manifest = read(FLAMMA / 'artifacts/active_intent_model.json')
active_text = (FLAMMA / manifest['path']).resolve()
if sha(active_text) != manifest['sha256']:
    raise ValueError('Active text artifact does not match the manifest.')
metadata = {p.stem.replace('.metadata', ''): read(p) for p in sorted((FLAMMA / 'artifacts').glob('*.metadata.json'))}
source_checks = []
for name, report in metadata.items():
    if sha(FLAMMA / 'artifacts' / (name + '.pkl')) != report['model_sha256']:
        raise ValueError('Model metadata checksum mismatch: ' + name)
    for source in report['training_audit']['sources']:
        path = Path(source['path'])
        if not path.is_absolute():
            path = FLAMMA / path
        source_checks.append({'model': name, 'source': relative(path), 'matches_training_checksum': sha(path) == source['sha256']})

print('Encoding the 130 authored benchmark messages once for all six classifiers.', flush=True)
encoder = SemanticModel()
expected = [label for _, label in FINAL_TEST_CASES]
embeddings = encoder.encode([normalize_message(text) for text, _ in FINAL_TEST_CASES])
labels = sorted(set(expected))
text_results = []
paths = sorted(FLAMMA.glob('semantic*.pkl')) + sorted((FLAMMA / 'artifacts').glob('intent_v*.pkl'))
for path in paths:
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        model = pickle.loads(path.read_bytes())
    predicted = model.predict(embeddings)
    result = {
        'file': relative(path), 'active_by_manifest': path.resolve() == active_text,
        'sha256': sha(path), 'bytes': path.stat().st_size,
        'type': type(model).__name__, 'parameters': model.get_params(),
        'embedding_dimensions': int(model.n_features_in_), 'classes': list(model.classes_),
        'iterations': model.n_iter_.tolist(), 'samples': len(expected),
        'correct': int(sum(a == b for a, b in zip(expected, predicted))),
        'accuracy': float(accuracy_score(expected, predicted)),
        'classification_report': classification_report(expected, predicted, output_dict=True, zero_division=0),
        'confusion_labels': labels, 'confusion_matrix': confusion_matrix(expected, predicted, labels=labels).tolist(),
        'predictions': [{'message': text, 'expected': label, 'predicted': str(pred)}
                        for (text, label), pred in zip(FINAL_TEST_CASES, predicted)],
    }
    text_results.append(result)
    print(path.name, result['correct'], '/', len(expected), flush=True)

image_results = []
image_source = (ROOT / 'Image/thesis-backend/inference/classifier.py').read_text()
for path in sorted((ROOT / 'Image/thesis-backend/models').glob('*.pth')):
    with torch.serialization.safe_globals([np._core.multiarray.scalar, np.dtype, np.dtypes.Float64DType, np.dtypes.Float32DType]):
        checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    result = {k: v.item() if isinstance(v, np.generic) else v for k, v in checkpoint.items() if k != 'model_state_dict'}
    result.update(file=relative(path), sha256=sha(path), bytes=path.stat().st_size,
                  configured_for_inference=path.name in image_source,
                  final_layer_shape=list(checkpoint['model_state_dict']['fc.weight'].shape))
    image_results.append(result)
    del checkpoint

evaluation_index = []
for path in sorted((FLAMMA / 'eval/results').glob('*.json')):
    d = read(path)
    row = {'file': relative(path), 'sha256': sha(path)}
    if isinstance(d, dict):
        for key in ['scope', 'evaluated_at', 'model_path', 'model_sha256', 'samples', 'examples', 'scenarios', 'turns', 'passed', 'accuracy']:
            if key in d:
                row[key] = d[key]
        if 'failures' in d:
            row['failure_count'] = len(d['failures'])
        if 'candidate' in d:
            row['candidate_accuracy'] = d['candidate'].get('accuracy')
            row['candidate_macro_f1'] = d['candidate'].get('macro_f1')
    else:
        row['entries'] = len(d)
    evaluation_index.append(row)

v5 = metadata['intent_v5']
training_paths = [Path(x['path']) if Path(x['path']).is_absolute() else FLAMMA / x['path'] for x in v5['training_audit']['sources']]
_, current_audit = load_training_examples(training_paths)
legacy = read(FLAMMA / 'model_weights.json')
legacy_info = {'file': 'Flamma/model_weights.json', 'sha256': sha(FLAMMA / 'model_weights.json'),
               'input_dimensions': len(legacy['hidden'][0]['weights']), 'hidden_neurons': len(legacy['hidden']),
               'output_neurons': len(legacy['output']), 'saved_accuracy': None, 'saved_epoch_history': None}
data_inventory = []
for path in sorted((FLAMMA / 'data').glob('*.json')):
    d = read(path)
    row = {'file': relative(path), 'sha256': sha(path)}
    if 'intents' in d:
        row.update(intent_entries=len(d['intents']), raw_patterns=sum(len(x['patterns']) for x in d['intents']))
    else:
        row['top_level_keys'] = list(d) if isinstance(d, dict) else None
    data_inventory.append(row)

active = next(x for x in text_results if x['active_by_manifest'])
facts = {'report_date': '2026-10-22', 'timezone': 'Asia/Manila',
         'generated_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
         'scope': 'Local source, saved training evidence, and fresh authored text benchmark; no image test dataset evaluated.',
         'active_text_manifest': manifest, 'training_source_checks': source_checks,
         'training_metadata': metadata, 'current_v5_corpus_audit': current_audit,
         'text_model_evaluations': text_results, 'image_checkpoints': image_results,
         'legacy_network': legacy_info, 'ood_configuration': read(ROOT / 'Image/thesis-backend/models/ood_config.json'),
         'data_inventory': data_inventory, 'saved_evaluation_index': evaluation_index}
save('model-audit.json', facts)
write_csv('text-model-comparison.csv', [dict(model=x['file'], active=x['active_by_manifest'], samples=x['samples'], correct=x['correct'], accuracy=x['accuracy'], macro_f1=x['classification_report']['macro avg']['f1-score'], sha256=x['sha256']) for x in text_results])
write_csv('image-model-comparison.csv', [dict(model=x['file'], configured=x['configured_for_inference'], classes=x['num_classes'], saved_test_accuracy=x.get('test_accuracy'), outlier_exposure=x['outlier_exposure'], sha256=x['sha256']) for x in image_results])
write_csv('active-model-per-intent.csv', [dict(intent=k, training_examples=v5['training_audit']['class_counts'][k], **active['classification_report'][k]) for k in labels])
write_csv('active-model-predictions.csv', active['predictions'])
write_csv('active-model-confusion-matrix.csv', [dict(expected=label, **dict(zip(labels, row))) for label, row in zip(labels, active['confusion_matrix'])])

lines = []
def paragraph(text):
    lines.extend([text, ''])
def table(headers, rows):
    lines.append('| ' + ' | '.join(headers) + ' |')
    lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
    lines.extend('| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows)
    lines.append('')

paragraph('# Flamma: current models and training results')
paragraph('Prepared for adviser review — 22 October 2026 (Asia/Manila). Source: the local project at C:\\flamma chatbot. Text benchmark scores below were rerun for this report; historical training results and checkpoint values are explicitly identified.')
paragraph('## Summary for presentation')
paragraph('Flamma is an English-first educational skin-information and screening prototype. Its configured text pipeline uses pretrained all-MiniLM-L6-v2 sentence embeddings and a trained logistic-regression intent classifier (v5). Conversation rules and a curated knowledge library produce replies. A separate ResNet-50 image service screens six supported classes and produces Grad-CAM heatmaps.')
paragraph(f'The active-by-manifest text classifier scored {active["correct"]}/130 ({pct(active["accuracy"])}) with macro F1 {active["classification_report"]["macro avg"]["f1-score"]:.4f} on the reused authored text-intent benchmark. The configured image checkpoint is v10-1; its test_accuracy is null. Only the archived image v3 checkpoint stores a test accuracy (95.19%), which must be attributed to v3.')
paragraph('At the initial local health check during this review, neither port 5000 nor port 8000 accepted a connection. Model selection below is verified from files and checksums; a live service model identity was not observed. No services were started and no models were retrained.')
paragraph('## 1. Complete saved text-model inventory and fresh benchmark')
table(['Artifact', 'Selection', 'Correct / 130', 'Accuracy', 'Macro F1'], [(Path(x['file']).name, 'Configured active' if x['active_by_manifest'] else 'Archived', x['correct'], pct(x['accuracy']), f'{x["classification_report"]["macro avg"]["f1-score"]:.4f}') for x in text_results])
paragraph('All six artifacts are logistic-regression classifiers with 384 input features and 13 output categories. The original classifier has no class weighting; the other five use class_weight=balanced. The two balanced legacy artifacts have no accompanying saved training metadata in this checkout; their numbers above are fresh evaluation results, not recovered training scores. Full parameters, iterations, hashes, predictions, and confusion matrices are in model-audit.json.')
paragraph('The MiniLM sentence encoder is pretrained and is not fine-tuned by this project training pipeline. It generates normalized sentence vectors. There is no evidence here of a locally trained generative language model.')
paragraph('## 2. Saved training and validation results')
table(['Version', 'Training completed (Manila)', 'Unique examples', 'Split: train / validation', 'Validation accuracy', 'Validation macro F1', 'Saved benchmark accuracy'], [(name, datetime.fromisoformat(m['trained_at']).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M'), m['training_audit']['unique_examples'], f'{m["validation"]["train_examples"]} / {m["validation"]["validation_examples"]}', pct(next(c['metrics']['accuracy'] for c in m['validation']['candidates'] if c['C']==m['validation']['selected_C'])), f'{next(c["metrics"]["macro_f1"] for c in m["validation"]["candidates"] if c["C"]==m["validation"]["selected_C"]):.4f}', pct(m['frozen_test']['candidate']['accuracy'])) for name,m in metadata.items()])
paragraph('Validation uses fold 0 of a five-way StratifiedGroupKFold split with seed 42 and no overlapping template groups recorded. These are single-fold results, not five-fold averages. Grouping logic evolved between versions, so validation rows are not identical evaluation sets. C values 0.5, 1.0, and 2.0 were compared; each version selected C=2.0 by validation macro F1. The selected classifier was then refit on all unique examples. Training uses max_iter=2000, balanced class weights, and random_state=42. Logistic-regression iterations are not neural-network training epochs.')
table(['Version', 'C', 'Validation accuracy', 'Validation macro F1'], [(name,c['C'],pct(c['metrics']['accuracy']),f'{c["metrics"]["macro_f1"]:.4f}') for name,m in metadata.items() for c in m['validation']['candidates']])
paragraph('v5 training recorded 6,484 input examples, 6,405 unique examples, 79 removed duplicates, no conflicting labels, and 1,918 template groups. The parameter-selection split contained 5,110 training and 1,295 validation examples. Its four sources are intents.json, training_supplement.json, english_location_supplement.json, and english_intent_supplement.json. v4 added 480 location examples over v3; v5 added 524 broader intent examples over v4.')
paragraph(f'All recorded source checksum comparisons passed: {all(x["matches_training_checksum"] for x in source_checks)}. Reprocessing the current v5 sources yields {current_audit["unique_examples"]:,} unique examples. Saved chats and photos were not training sources in these reports. The corpus contains authored fictional examples; its size does not represent patient counts. Class weighting addresses unequal class counts without making the dataset numerically balanced.')
paragraph('Training runtime recorded for v5: Python ' + v5['python_version'] + '; ' + '; '.join(f'{k} {v}' for k,v in v5['runtime_versions'].items()) + '.')
paragraph('## 3. Active v5 results by intent')
table(['Intent', 'Training examples', 'Test messages', 'Precision', 'Recall', 'F1'], [(k,v5['training_audit']['class_counts'][k],int(active['classification_report'][k]['support']),f'{active["classification_report"][k]["precision"]:.4f}',f'{active["classification_report"][k]["recall"]:.4f}',f'{active["classification_report"][k]["f1-score"]:.4f}') for k in labels])
paragraph('Macro F1 gives each intent equal weight. Accuracy counts the fraction of correctly categorized messages. The 130-message benchmark contains ten examples per intent. It was excluded from fitting but has been reused across development versions, so it is not an untouched independent final test.')
paragraph('### Incorrect v5 benchmark predictions')
table(['Authored message', 'Expected', 'Predicted'], [(x['message'],x['expected'],x['predicted']) for x in active['predictions'] if x['expected']!=x['predicted']])
paragraph('## 4. Other saved text and conversation evaluations')
general = read(FLAMMA / 'eval/results/intent-v5-generalization.json')
paragraph(f'Additional authored intent comparison: v4 {pct(general["baseline"]["accuracy"])} (63/65), v5 {pct(general["candidate"]["accuracy"])} (65/65), with v5 macro F1 1.0000. The saved report records zero exact training overlap and zero template-group overlap. This small authored set remains an engineering evaluation.')
table(['Saved result file', 'Scenarios', 'Passed / turns', 'Interpretation'], [(name,d['scenarios'],f'{d["passed"]}/{d["turns"]}','Authored conversation regression') for name in ['course-core-conversations.json','course-all-followups.json','course-questions-after.json'] for d in [read(FLAMMA/'eval/results'/name)]])
paragraph('These are saved results from 16 October 2026 by local file timestamps, not fresh runs for this report. Some scenarios overlap across suites; their counts must not be added as independent samples. They measure specified conversation behavior, not image recognition or medical correctness. model-audit.json indexes every saved evaluation JSON in eval/results, including historical before/after reports.')
paragraph('## 5. Complete image-model inventory')
table(['Checkpoint', 'Selection in source', 'Classes', 'Saved test accuracy', 'Outlier exposure'], [(Path(x['file']).name,'Configured active' if x['configured_for_inference'] else 'Archived',x['num_classes'],pct(x.get('test_accuracy')),'Yes' if x['outlier_exposure'] else 'No') for x in image_results])
paragraph('All four checkpoints identify architecture=resnet50 and the same six classes: atopic dermatitis, contact dermatitis, lichen planus, normal skin, psoriasis, and rosacea. The final linear layer has 2,048 inputs and six outputs. The newer filename v11c is present but is not selected by inference/classifier.py.')
paragraph('The archived v3 checkpoint stores test_accuracy=0.9519230769230769 (95.19%). No test sample count, test-set definition, per-class report, confusion matrix, optimizer settings, epoch history, or training/validation curves are included in these checkpoints. No image dataset or image-training notebook was found in the project folders inspected. A 2,400-image dataset is mentioned in a skin-filter source comment, but its size and split cannot be verified from local data. No new image accuracy was measured for this report.')
paragraph('Each checkpoint records outlier exposure and 12 auxiliary category names. Those auxiliary categories are not additional supported diagnostic classes. The names are preserved in model-audit.json.')
paragraph('### Configured image pipeline')
table(['Setting', 'Verified value'], [('Input','RGB, resized to 224 x 224'),('Normalization mean','0.485, 0.456, 0.406'),('Normalization standard deviation','0.229, 0.224, 0.225'),('Skin-content prefilter','YCrCb OR HSV color heuristic; minimum skin-like pixel ratio 0.15'),('OOD score','Entropy; reject when score > 0.9399791955947876'),('OOD target_tpr setting','0.95 (configuration target, not an observed result in this review)'),('Confidence threshold','0.55'),('Explanation','Grad-CAM on ResNet layer4[-1]')])
paragraph('The color filter and OOD/confidence gates are screening mechanisms. Their thresholds do not establish measured sensitivity, specificity, clinical calibration, or the ability to rule out unsupported disease. The OOD configuration does not identify which checkpoint it was calibrated against; calibration correspondence with v10-1 cannot be verified here.')
paragraph('## 6. Legacy and supporting components')
table(['Component', 'Current evidence'], [('Custom bag-of-words neural network','model_weights.json contains 636 inputs, 8 hidden neurons, and 10 output neurons. train.py requests 1,000 epochs with SGD learning rate 0.01 and cross-entropy; no saved actual epoch/loss history or accuracy is present. It is not used by the current SemanticChatbot app path.'),('Embedding cache','Three NPZ training-embedding caches are present; these are intermediate vectors, not additional trained classifiers.'),('Conversation and knowledge layer','Rules, context tracking, warning checks, and curated JSON information. They are software/knowledge components rather than independently trained models.'),('Optional Gemini endpoint','Image backend includes a separate optional /api/chat endpoint. The current Flamma chat interface uses the local semantic chatbot; Gemini is not part of the local training results.')])
paragraph('## 7. Evidence files and remaining results to obtain')
paragraph('Primary evidence: Flamma/artifacts/active_intent_model.json; Flamma/artifacts/intent_v3.metadata.json; intent_v4.metadata.json; intent_v5.metadata.json; Flamma/eval/results; Image/thesis-backend/inference/classifier.py; Image/thesis-backend/models/*.pth; Image/thesis-backend/models/ood_config.json; and Flamma/DEFENSE_NOTES.md.')
paragraph('To report complete image training results, obtain the original image-training notebook, dataset provenance and counts by class, patient/source-level splits, preprocessing and augmentation settings, optimizer and learning-rate schedule, actual epoch logs, checkpoint selection rule, independent test labels, per-class precision/recall/F1, confusion matrix, and OOD calibration/evaluation evidence. An independently authored text test is also needed for a stronger final generalization claim.')
paragraph('Suggested adviser statement: "Our active v5 text-intent classifier was trained on 6,405 unique fictional English examples across 13 intents. It achieved 98.30% accuracy and 0.9664 macro F1 on one grouped validation fold, and 94.62% accuracy with 0.9478 macro F1 on a reused 130-message benchmark. The configured image classifier is ResNet-50 v10-1 with six output classes; its checkpoint does not include test accuracy. Archived image v3 stores 95.19%, which we attribute only to v3. These are prototype engineering results, not established clinical diagnostic accuracy."')
paragraph('## 8. Reproduce this report')
paragraph('From C:\\flamma chatbot, run: .\\Flamma\\venv\\Scripts\\python.exe -B reports\\2026-10-22\\build_report.py. This reads local checkpoints, evaluates authored text cases with cached MiniLM embeddings, checks recorded checksums, and rewrites the report artifacts. It does not train or activate a model.')
paragraph('Companion files: model-audit.json (complete extracted model evidence and saved evaluation index); text-model-comparison.csv; image-model-comparison.csv; active-model-per-intent.csv; active-model-predictions.csv; active-model-confusion-matrix.csv. The HTML version is self-contained and can be printed or saved to PDF from a browser.')
report_text = '\n'.join(lines)
(OUT / 'ADVISER_REPORT.md').write_text(report_text, encoding='utf-8')

# Convert the small, controlled Markdown subset to an offline printable document.
blocks = []
i = 0
while i < len(lines):
    line = lines[i]
    if not line:
        i += 1
        continue
    if line.startswith('| '):
        rows = []
        while i < len(lines) and lines[i].startswith('| '):
            rows.append([x.strip() for x in lines[i].strip('|').split('|')])
            i += 1
        blocks.append('<table><thead><tr>' + ''.join('<th>'+html.escape(x)+'</th>' for x in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in rows[2:]) + '</tbody></table>')
        continue
    if line.startswith('#'):
        level = len(line) - len(line.lstrip('#'))
        blocks.append(f'<h{level}>'+html.escape(line[level:].strip())+f'</h{level}>')
    else:
        blocks.append('<p>'+html.escape(line)+'</p>')
    i += 1
document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flamma — Adviser model and training report</title><style>
body{font:15px/1.6 system-ui,sans-serif;color:#192537;max-width:1100px;margin:40px auto;padding:0 24px}h1{font-size:32px;color:#953517}h2{margin-top:36px;color:#953517}h3{margin-top:24px}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}th,td{border:1px solid #ccd2d9;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#f3e9e5}tr:nth-child(even){background:#fafafa}p{overflow-wrap:anywhere}@media print{body{max-width:none;margin:0;font-size:10pt;padding:0}table{font-size:8pt}tr{break-inside:avoid}h2,h3{break-after:avoid}thead{display:table-header-group}@page{size:A4 landscape;margin:14mm}}
</style><body>''' + '\n'.join(blocks) + '</body></html>'
(OUT / 'ADVISER_REPORT.html').write_text(document, encoding='utf-8')
print('Report written to', OUT, flush=True)
