"""Choose from development results only, then lock before final evaluation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(PROJECT))
from model.train_intent import activate_candidate

lock=HERE/'candidate.lock.json'
if lock.exists():
    raise SystemExit('Candidate already locked. Do not replace it after consuming final results.')
baseline=json.loads((PROJECT/'artifacts/intent_v5.metadata.json').read_text())
known={x['text'] for x in baseline['frozen_test']['predictions'] if x['expected']!=x['candidate']}
attempts=[]
for version in [6,7,8]:
    path=PROJECT/f'artifacts/intent_v{version}.pkl'
    m=json.loads(path.with_suffix('.metadata.json').read_text())
    fixed=sum(x['expected']==x['candidate'] for x in m['frozen_test']['predictions'] if x['text'] in known)
    attempts.append(dict(version=version,known_errors_fixed=fixed,
                         benchmark_accuracy=m['frozen_test']['candidate']['accuracy'],
                         benchmark_macro_f1=m['frozen_test']['candidate']['macro_f1'],
                         quality_gate_passed=m['quality_gate_passed']))
selected=max((x for x in attempts if x['quality_gate_passed']),key=lambda x:(x['known_errors_fixed'],x['benchmark_accuracy'],x['benchmark_macro_f1'],-x['version']))
if selected['known_errors_fixed']!=7:
    raise SystemExit('No candidate fixes all seven known errors; keep development separate from final.')
model=PROJECT/f'artifacts/intent_v{selected["version"]}.pkl'
conversations=PROJECT.parent/f'reports/adviser-evaluation-2026-10-22/conversation-checks-v{selected["version"]}.json'
checks=json.loads(conversations.read_text())
if checks['failures']:
    raise SystemExit('Development conversations failed; final evaluation not authorized by protocol.')
software=json.loads((conversations.parent/'software-checks.json').read_text())
if not software['successful']:
    raise SystemExit('Software regressions failed.')
previous=(PROJECT/'artifacts/active_intent_model.json').read_bytes()
(HERE/'previous-active-intent-model.json').write_bytes(previous)
activate_candidate(model)
sources=[PROJECT/'app.py',*(PROJECT/'model').glob('*.py'),*(PROJECT/'frontend/src').rglob('*.js'),*(PROJECT/'frontend/src').rglob('*.jsx')]
record={'locked_at':datetime.now(timezone.utc).isoformat(),
        'selection_basis':'Development only: prioritize fixing the seven known errors, then old benchmark accuracy/macro F1. Three successful training attempts recorded. New final predictions have not been inspected.',
        'attempts':attempts,'selected_version':selected['version'],'selected_model':str(model),
        'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
        'source_hashes':{str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'known_limitations':'Selected v7 has one severity error on the reused 130-message development benchmark. v8 regressed one of the seven known errors and was not selected. One attempted development supplement was refused for exact overlap with the old benchmark, removed before fitting.',
        'final_test_used_for_selection':False}
lock.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2))
