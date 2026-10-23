"""Evaluate the active image pipeline on a supplied test manifest; never calibrate here."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[2] / 'Image' / 'thesis-backend'


def metrics(rows, labels):
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    if not rows:
        return {'samples': 0, 'accuracy': None, 'classification_report': None, 'confusion_matrix': None}
    actual, predicted = zip(*[(r['label'], r['predicted']) for r in rows])
    return {'samples': len(rows), 'accuracy': float(accuracy_score(actual, predicted)),
            'classification_report': classification_report(actual, predicted, labels=labels, output_dict=True, zero_division=0),
            'confusion_labels': labels, 'confusion_matrix': confusion_matrix(actual, predicted, labels=labels).tolist()}


def summarize(rows, labels):
    supported = [r for r in rows if r['label'] in labels]
    accepted = [r for r in supported if r['accepted']]
    unsupported = [r for r in rows if r['label'] == 'unsupported']
    return {'raw_supported_classifier': metrics(supported, labels),
            'accepted_supported_classifier': metrics(accepted, labels),
            'supported_coverage': len(accepted)/len(supported) if supported else None,
            'supported_end_to_end_correct_fraction': sum(r['accepted'] and r['label'] == r['predicted'] for r in supported)/len(supported) if supported else None,
            'per_class_gate_results': {label: {'samples': sum(r['label']==label for r in supported),
                                              'accepted': sum(r['label']==label and r['accepted'] for r in supported),
                                              'rejected': sum(r['label']==label and not r['accepted'] for r in supported)} for label in labels},
            'unsupported_samples': len(unsupported),
            'unsupported_rejection_fraction': sum(not r['accepted'] for r in unsupported)/len(unsupported) if unsupported else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True, help='CSV: image_path,label,split,subject_id,source_id; split must be test.')
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--split-provenance', type=Path, required=True)
    parser.add_argument('--training-manifest', type=Path, help='Optional CSV for detecting exact file/subject/source overlap.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset_root.resolve(strict=True)
    provenance = json.loads(args.split_provenance.read_text(encoding='utf-8'))
    for field in ['test_frozen_before_model_selection', 'not_used_for_training_or_calibration']:
        if provenance.get(field) is not True:
            parser.error('Split provenance must declare ' + field + '=true; do not call a tuning set held-out.')
    with args.manifest.open(encoding='utf-8-sig', newline='') as f:
        records = list(csv.DictReader(f))
    if not records:
        parser.error('Test manifest is empty.')
    for row in records:
        path = (root/row['image_path']).resolve(strict=True)
        if not path.is_relative_to(root) or row.get('split') != 'test':
            parser.error('All image paths must stay within dataset-root and all rows must have split=test.')
        row['_path'] = path
        row['_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len({r['_sha256'] for r in records}) != len(records):
        parser.error('Duplicate image contents in test manifest; deduplicate before evaluation.')
    split_audit = {'provenance_declarations': provenance, 'independently_verified_provenance': False,
                   'training_overlap_check': 'not performed; training manifest unavailable'}
    if args.training_manifest:
        with args.training_manifest.open(encoding='utf-8-sig', newline='') as f:
            train = list(csv.DictReader(f))
        train_hashes = {hashlib.sha256((root/r['image_path']).read_bytes()).hexdigest() for r in train}
        if train_hashes & {r['_sha256'] for r in records}:
            parser.error('Image contents overlap training; final evaluation refused.')
        for field in ['subject_id', 'source_id']:
            overlap = {r.get(field) for r in train if r.get(field)} & {r.get(field) for r in records if r.get(field)}
            split_audit[field+'_overlap'] = len(overlap)
            if overlap:
                parser.error(field + ' overlaps training. Supply a genuinely disjoint final set.')
        split_audit['training_overlap_check'] = 'No exact content or supplied subject/source IDs overlap.'

    import numpy as np
    import torch
    from PIL import Image, ImageOps
    sys.path.insert(0, str(BACKEND))
    from inference.skin_detector import estimate_skin_ratio, SKIN_PIXEL_THRESHOLD, get_skin_crops_with_boxes
    from inference.blur_check import blur_status
    from inference import classifier as active
    checkpoint_path = Path(active.MODEL_PATH).resolve()
    labels = list(active.MODEL_INFO['classes'])
    if set(labels) - {r['label'] for r in records}:
        parser.error('Test set must include all six supported classes for per-disease evaluation.')
    if any(r['label'] not in labels+['unsupported'] for r in records):
        parser.error('Unknown label; use an exact checkpoint class or unsupported.')
    ood = json.loads((BACKEND/'models/ood_config.json').read_text())
    model = active._model
    transform = active._inference_transform
    rows = []
    with torch.no_grad():
        model(torch.zeros(1,3,224,224).to(active.DEVICE))  # warm-up excluded from timings
        for row in records:
            started = perf_counter()
            with Image.open(row['_path']) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
            blur_state, blur = blur_status(image)
            skin_ratio = estimate_skin_ratio(image)
            crops = get_skin_crops_with_boxes(image, active.N_CROPS)[0] if active.CROP_TO_SKIN else [image]
            all_logits = model(torch.stack([transform(crop) for crop in crops]).to(active.DEVICE))
            logits = all_logits.mean(dim=0, keepdim=True)
            probabilities = torch.softmax(logits,dim=1)
            confidence, index = probabilities[0].max(dim=0)
            score = active._ood_score(logits)
            confidence_value = round(float(confidence), 4)
            predicted = labels[int(index)]
            crop_disease_max = float(torch.softmax(all_logits, dim=1)[:, active._disease_idxs].max()) if active._disease_idxs else 0.0
            normal_rejected = active.NORMAL_GATE_ENABLED and predicted == active.NORMAL_CLASS and (
                confidence_value < active.NORMAL_MIN_CONFIDENCE or crop_disease_max >= active.NORMAL_CROP_VETO_PROB)
            reason = ('too_blurry' if blur_state == 'blocked' else
                      'no_skin_detected' if skin_ratio < SKIN_PIXEL_THRESHOLD else
                      'out_of_scope' if active.OOD_ENABLED and score > active.OOD_THRESHOLD else
                      'inconclusive' if normal_rejected else
                      'low_confidence' if confidence_value < active.CONFIDENCE_THRESHOLD else None)
            rows.append(dict(image_path=row['image_path'], sha256=row['_sha256'], label=row['label'],
                             predicted=predicted, confidence=float(confidence), skin_ratio=skin_ratio,
                             blur_status=blur_state, blur_score=blur, crops=len(crops), crop_disease_max=crop_disease_max,
                             ood_score=score, accepted=reason is None, rejection_reason=reason,
                             seconds=perf_counter()-started))
    durations = [r['seconds'] for r in rows]
    output = {'scope': 'Held-out image engineering evaluation; provenance supplied by dataset owner.',
              'checkpoint': str(checkpoint_path), 'checkpoint_sha256': hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
              'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(), 'split_audit': split_audit,
              'ood_configuration': ood, 'active_pipeline': active.MODEL_INFO, **summarize(rows, labels),
              'timing': {'device':str(active.DEVICE),'median_seconds':float(np.median(durations)), 'p95_seconds':float(np.percentile(durations,95)),
                         'scope':'Read, orientation, blur/skin checks, crop-averaged classifier and gates; excludes Grad-CAM, HTTP and UI. Raw predictions include rejected samples.'},
              'predictions': rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ['predictions','split_audit']},indent=2))

if __name__ == '__main__':
    main()
