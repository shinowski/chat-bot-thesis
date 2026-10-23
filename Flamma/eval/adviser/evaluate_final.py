"""Consume the frozen final set once, after candidate selection is locked."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import warnings

PROJECT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=PROJECT.parent/'reports/adviser-evaluation-2026-10-22'
sys.path.insert(0,str(PROJECT))
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from model.training_data import load_training_examples, example_group
from model.text_understanding import normalize_message, clean_message
from model.semantic_model import SemanticModel
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if (OUT/'final-text-results.json').exists():
    raise SystemExit('Final results already exist. Do not reuse this set to tune or reselect a candidate.')
freeze=json.loads((HERE/'final-set.lock.json').read_text())
lock=json.loads((HERE/'candidate.lock.json').read_text())
assert sha(HERE/'final-cases.json')==freeze['sha256']
assert sha(Path(lock['selected_model']))==lock['model_sha256']
for name,expected_hash in lock['source_hashes'].items():
    assert sha(PROJECT/name)==expected_hash, 'Application changed after candidate lock: '+name
cases=json.loads((HERE/'final-cases.json').read_text())
labels=sorted({x['expected'] for x in cases})
expected=[x['expected'] for x in cases]
results=[]
encoder=SemanticModel()
embeddings=encoder.encode([normalize_message(x['text']) for x in cases])
for path in [PROJECT/'artifacts/intent_v5.pkl',Path(lock['selected_model'])]:
    metadata=json.loads(path.with_suffix('.metadata.json').read_text())
    paths=[Path(s['path']) if Path(s['path']).is_absolute() else PROJECT/s['path'] for s in metadata['training_audit']['sources']]
    for source,p in zip(metadata['training_audit']['sources'],paths):
        assert sha(p)==source['sha256'], 'Training source changed.'
    training,_=load_training_examples(paths)
    normalized={clean_message(normalize_message(x['text'])) for x in training}
    assert not normalized & {clean_message(normalize_message(x['text'])) for x in cases}
    groups={x['group'] for x in training}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        model=pickle.loads(path.read_bytes())
    predicted=model.predict(embeddings)
    predictions=[dict(case,predicted=str(pred),correct=case['expected']==pred) for case,pred in zip(cases,predicted)]
    report=classification_report(expected,predicted,labels=labels,output_dict=True,zero_division=0)
    result={'model':path.name,'sha256':sha(path),'samples':len(cases),'correct':sum(x['correct'] for x in predictions),
            'accuracy':float(accuracy_score(expected,predicted)),'classification_report':report,
            'training_exact_overlap':0,'training_template_group_overlap':sum(example_group(x['text']) in groups for x in cases),
            'confusion_labels':labels,'confusion_matrix':confusion_matrix(expected,predicted,labels=labels).tolist(),
            'predictions':predictions,'failures':[x for x in predictions if not x['correct']]}
    results.append(result)
    for suffix,rows in [('predictions',predictions),('per-intent',[dict(intent=k,**report[k]) for k in labels]),
                        ('confusion-matrix',[dict(expected=k,**dict(zip(labels,row))) for k,row in zip(labels,result['confusion_matrix'])])]:
        with (OUT/(path.stem+'-final-'+suffix+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
output={'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'New authored single-turn final intent evaluation; not clinical validation or independent human annotation.',
        'final_set_sha256':freeze['sha256'],'candidate_lock_sha256':sha(HERE/'candidate.lock.json'),
        'frozen_before_candidate_training':True,'final_not_used_for_training_or_selection':True,
        'no_post_final_tuning_permitted':True,'models':results,
        'limitations':['Labels authored by the coding assistant; independent human adjudication pending.',
                       'Exact deduplication does not guarantee semantic novelty; template overlap disclosed.',
                       'Balanced authored categories do not represent real-user prevalence.']}
(OUT/'final-text-results.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'evaluated_at':output['evaluated_at'],'models':[{k:v for k,v in r.items() if k not in ['predictions','classification_report','confusion_matrix','failures']} for r in results]},indent=2))
