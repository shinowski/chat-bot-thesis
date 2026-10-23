"""Assemble existing evaluation evidence; never run models or change results."""
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
from pathlib import Path
import statistics

PROJECT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=PROJECT.parent/'reports/adviser-evaluation-2026-10-22'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def percent(value):return f'{value*100:.2f}%'

final=read(OUT/'final-text-results.json')
lock=read(HERE/'candidate.lock.json')
freeze=read(HERE/'final-set.lock.json')
software=read(OUT/'software-checks.json')
conversation=read(OUT/'conversation-checks-v7.json')
browser=read(OUT/'browser-checks.json')
image=read(OUT/'real-image-integration-smoke.json')
old=read(PROJECT/'artifacts/intent_v5.metadata.json')
new=read(PROJECT/'artifacts/intent_v7.metadata.json')
v5,v7=final['models']
assert sha(HERE/'final-cases.json')==freeze['sha256']
assert sha(Path(lock['selected_model']))==lock['model_sha256']
assert all(sha(PROJECT/name)==value for name,value in lock['source_hashes'].items())
assert read(PROJECT/'artifacts/active_intent_model.json')['sha256']==v7['sha256']
assert sum(map(sum,v7['confusion_matrix']))==260
assert v7['correct']+len(v7['failures'])==260

checklist=[
    ('1. New Intent v5 dataset','Completed with annotation limitation','260 newly authored messages; v5 and locked v7 tested once. Independent human label review remains pending.'),
    ('2. Seven original intent errors','Fixed; further errors reported','v7 fixes all original seven. Old development benchmark 129/130; one different severity error. New final set has 18 v7 errors, retained without tuning.'),
    ('3. Active image held-out metrics','Pending data','Test dataset and split provenance not confirmed. Evaluator and manifest requirements prepared. No new disease accuracy claimed.'),
    ('4. Dermatologist expert-system validation','Pending reviewer','Review form and source bundle prepared. Expert rules remain empty and awaiting validation. No clinical sign-off claimed.'),
    ('5. Complete conversations','Automated checks completed','106 authored scenarios / 289 turns passed using real v7; browser checks cover follow-up, reload persistence, reset and fallback.'),
    ('6. Image/chatbot integration','Automated checks completed','All six label mappings and rejection checked with fixtures; 12 real-model HTTP smoke uploads checked with synthetic pixels. Image recognition accuracy remains unmeasured.'),
    ('7. Safety and uncertainty','Software fixes/checks completed; image-gate limitation open','Low-confidence success payloads and explicit uncertainty now rejected. Nonfinite expert-system scores rejected. Emergency/negation tests pass. Synthetic flat/noisy skin colors were accepted by image gate; clinical validation pending.'),
    ('8. Usability and performance','Automated portion completed; human study pending','Four browser viewports and local timings recorded. No participant task-success rate, satisfaction or SUS score exists.'),
]
with (OUT/'adviser-checklist.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['item','status','evidence_or_remaining_work']);w.writerows(checklist)

lines=[]
def p(text):lines.extend([text,''])
def table(headers,rows):
    lines.append('| '+' | '.join(headers)+' |')
    lines.append('| '+' | '.join(['---']*len(headers))+' |')
    lines.extend('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows)
    lines.append('')

p('# Flamma — adviser evaluation results')
p('22 October 2026, Asia/Manila. This report supersedes the earlier model inventory for current model selection. It distinguishes measured software behavior, authored text classification, synthetic image transport checks, and unfinished clinical/image evaluation.')
p('## Checklist status')
table(['Adviser item','Status','Evidence / remaining work'],checklist)
p('## New frozen 260-message test')
p('The final set contains 20 messages for each of 13 intents, including typos, short replies, ambiguous questions and varied phrasing. It was frozen and hashed before development training. Normalized exact overlap was zero against training JSON, historical evaluation JSON, and string constants in prior top-level test/evaluation Python files. One template group overlaps training; semantic independence is not established by exact deduplication. Cases and provisional labels were authored by the coding assistant; independent human annotation/adjudication is still needed.')
table(['Model','Correct / 260','Accuracy','Macro precision','Macro recall','Macro F1'],[(m['model'],f'{m["correct"]}/260',percent(m['accuracy']),f'{m["classification_report"]["macro avg"]["precision"]:.4f}',f'{m["classification_report"]["macro avg"]["recall"]:.4f}',f'{m["classification_report"]["macro avg"]["f1-score"]:.4f}') for m in [v5,v7]])
p('The absolute accuracy improvement is 2.31 percentage points (six additional correct messages). Both models have zero exact overlap with their training corpora. The current manifest selects v7; v5 remains unchanged. Selection and activation occurred before final predictions, using development evidence only. No threshold, classifier, or application source was changed after examining final results. The final set is now consumed and must not be recycled for tuning or model selection.')
p('### Results per intent (20 test messages each)')
labels=v7['confusion_labels']
table(['Intent','v5 precision','v5 recall','v5 F1','v7 precision','v7 recall','v7 F1'],[(label,*[f'{m["classification_report"][label][metric]:.4f}' for m in [v5,v7] for metric in ['precision','recall','f1-score']]) for label in labels])
p('Unknown and ambiguous wording remains a weakness. Improvements are aggregate; some greeting, confirmation, thanks and identity cases still fail or regress. The classifier is a message router; raw intent accuracy does not measure diagnosis, referral safety, or whether the conversation rules ultimately provide an appropriate answer.')
p('### All remaining v7 final-test errors')
table(['Case','New authored message','Expected','Predicted'],[(x['id'],x['text'],x['expected'],x['predicted']) for x in v7['failures']])
p('All v5 errors, all predictions, per-intent precision/recall/F1 and both confusion matrices are included in final-text-results.json and the companion CSV files. Do not omit these failures from an adviser presentation.')
p('## Development fixes and provenance')
p('The original errors came from confusing descriptions of affected skin with actual anatomical locations, underrepresented descriptions of already attached/uploaded photos, and vague duration phrases. Three separately versioned candidates were trained using fictional development examples, not the new final set. The original v5 artifact and every candidate metadata file were preserved. One candidate supplement initially matched a sentence from the old benchmark; the training overlap guard refused that attempt, and the exact sentence was excluded before fitting. The refusal is disclosed rather than counted as a trained model.')
table(['Candidate','Original seven fixed','Old development benchmark','Macro F1'],[(f'v{x["version"]}',f'{x["known_errors_fixed"]}/7',percent(x['benchmark_accuracy']),f'{x["benchmark_macro_f1"]:.4f}') for x in lock['attempts']])
p('v7 was selected because it fixed all seven known errors and improved the old benchmark. It still misclassifies "the itching has become extremely uncomfortable" as symptom instead of severity. v8 was not selected because one of the original seven errors regressed. These repeated development comparisons should not be presented as independent final-test evidence.')
known={x['text'] for x in old['frozen_test']['predictions'] if x['expected']!=x['candidate']}
table(['Known development message','Expected','v5','v7'],[(x['text'],x['expected'],x['baseline'],x['candidate']) for x in new['frozen_test']['predictions'] if x['text'] in known])
selected=next(x for x in new['validation']['candidates'] if x['C']==new['validation']['selected_C'])
p(f'v7 training: {new["training_audit"]["input_examples"]:,} inputs; {new["training_audit"]["unique_examples"]:,} unique examples; {new["training_audit"]["duplicates_removed"]} duplicates removed; no conflicting labels. The additional development supplement contains 330 patterns. Model: balanced logistic regression on 384-dimensional frozen MiniLM embeddings, C={new["validation"]["selected_C"]}, max_iter=2000, seed=42. Parameter selection used one grouped validation fold with {new["validation"]["train_examples"]:,} training / {new["validation"]["validation_examples"]:,} validation examples, accuracy {percent(selected["metrics"]["accuracy"])} and macro F1 {selected["metrics"]["macro_f1"]:.4f}. It was refit on the full development corpus. Fold membership differs from v5; do not treat their validation rows as an identical held-out comparison.')
p('### Safety fixes implemented')
p('The chatbot now enforces the image service\'s 0.55 acceptance floor even if a response is marked status=ok. An explicit is_confident=false also rejects the response. Invalid or low-confidence results cannot establish a current condition or reuse an earlier photo\'s treatment context. Boolean image confidence values are rejected. The separate expert-system evaluator now rejects NaN and infinity confidence values. Existing warning escalation, negation, medicine boundaries and normal-skin caveats remain covered by regression checks. These are software safeguards; dermatologist validation remains pending.')
p('## Conversation, API and browser results')
table(['Check','Observed result'],[
    ('Python software regressions',f'{software["tests_run"]} run; no failures/errors/skips'),
    ('Frontend automated checks','27 passed; production build completed'),
    ('Real-model authored development conversations',f'{conversation["passed"]}/{conversation["turns"]} turns across {conversation["scenarios"]} scenarios'),
    ('In-process API performance calls',f'{conversation["api_in_process_timing"]["samples"]} calls; {conversation["api_in_process_timing"]["non_200_responses"]} non-200 responses'),
    ('Simulated class/rejection API mapping','All six classes plus rejection passed'),
    ('Browser viewports','360 x 800; 390 x 844; 768 x 1024; 1366 x 900; no horizontal overflow; composer accessible and visible'),
    ('Browser conversation flow','Follow-up, treatment context, refresh persistence, reset, fallback and emergency routing passed'),
    ('Browser uploads','All six simulated labels and rejection passed'),
    ('Browser runtime','Zero uncaught JavaScript exceptions')])
p('Conversation suites are authored development/regression checks. Counts must not be combined with the 260-message final classifier evaluation as if they were independent diagnostic samples. Browser image responses were simulated, and mobile checks use emulation rather than physical devices. Four viewport screenshots are included. No human usability outcome was measured.')
p('## Performance observed on this computer')
browser_ms=[x['milliseconds'] for x in browser['reply_timings']]
accepted=[x['seconds'] for x in image['results'] if x['intent']=='image_classification']
rejected=[x['seconds'] for x in image['results'] if x['intent']=='image_rejected']
import numpy as np
table(['Measurement','Samples','Median','95th percentile','Scope'],[
    ('Warm real-model reply',conversation['turns'],f'{conversation["text_reply_timing"]["median_seconds"]*1000:.1f} ms',f'{conversation["text_reply_timing"]["p95_seconds"]*1000:.1f} ms','Python reply; excludes browser/network/model startup'),
    ('In-process Flask request',30,f'{conversation["api_in_process_timing"]["median_seconds"]*1000:.1f} ms',f'{conversation["api_in_process_timing"]["p95_seconds"]*1000:.1f} ms','Test-client requests; excludes network'),
    ('Browser send to rendered reply',len(browser_ms),f'{statistics.median(browser_ms):.1f} ms',f'{float(np.percentile(browser_ms,95)):.1f} ms','Local browser + HTTP + rendering; 50 ms polling resolution'),
    ('Real image pipeline, accepted synthetic input',len(accepted),f'{statistics.median(accepted):.3f} s',f'{float(np.percentile(accepted,95)):.3f} s','Actual CPU v10-1, HTTP, Grad-CAM and chatbot mapping'),
    ('Real image pipeline, rejected synthetic input',len(rejected),f'{statistics.median(rejected):.3f} s',f'{float(np.percentile(rejected,95)):.3f} s','Skin/OOD rejection paths')])
p(f'Text-model construction/loading took {conversation["load_seconds_excluding_module_imports"]:.2f} seconds (excluding module import time). Image backend startup took {image["startup_seconds_including_imports"]:.2f} seconds including imports. These small local samples are descriptive, not load tests or production service guarantees. Error counts above describe expected software behavior and HTTP status, not clinical error rates.')
p('## Image accuracy remains pending — observed gate limitation')
p('The active image weights are still ResNet-50 v10-1. Its saved test_accuracy is null, and no held-out image test dataset or split provenance has been confirmed. Accordingly, accuracy, precision, recall, macro F1, confusion matrix and per-disease diagnostic performance for v10-1 remain unmeasured. Archived v3\'s 95.19% must not be reused as the v10-1 result.')
p('The actual v10-1 HTTP integration smoke used four synthetic pixel patterns, three repeats each. Blue pixels were rejected by the skin-content gate and random pixels by the OOD gate. Uniform skin-colored pixels and noisy skin-colored pixels were accepted (six accepted uploads total), despite containing no genuine lesion photograph. This is an observed out-of-distribution gate limitation. The smoke passes transport/state/wording invariants; it does not pass a claim that unsupported images are reliably rejected. Do not describe it as diagnostic validation.')
p('A held-out evaluator is implemented in Flamma/eval/adviser/evaluate_images.py. It reports raw metrics for every supported labeled image, accepted-only metrics alongside coverage, per-class rejection, end-to-end correct accepted predictions divided by all supported images, and unsupported-image rejection. Dataset provenance and optional exact/patient/source training overlap are recorded. Thresholds are fixed; no calibration is performed on the final image set. See IMAGE_DATA_REQUIREMENTS.md for the manifest and command.')
p('## Dermatologist and human usability review remain pending')
p('The expert-system JSON has status=awaiting_dermatologist_validation and an empty rules list. No dermatologist-approved recommendations or clinical rule validation were established. A review form, editable review matrix, and a source snapshot are included. They cover explanations, treatment information, red flags, referral, unsupported conditions, uncertainty, medicine boundaries and normal-skin interpretation. A qualified reviewer must review actual responses and sign the scoped decision. No review request was sent.')
p('USABILITY_STUDY.md defines participant tasks, outcomes and a recording template. Human comprehension, task success, satisfaction, physical mobile-device behavior, assistive technology and SUS remain pending participant testing.')
p('## Evidence, reproduction and rollback')
p('Primary final evidence: final-text-results.json, intent_v5-final-*.csv and intent_v7-final-*.csv. Development and locking evidence: Flamma/eval/adviser/PROTOCOL.md, final-set.lock.json, candidate.lock.json, development supplements and artifacts/intent_v6–v8.metadata.json. Software/browser/performance evidence is stored beside this report. Clinical source snapshots are listed with hashes in clinical-review-source-manifest.json.')
p('Re-run software checks from the Flamma directory: .\\venv\\Scripts\\python.exe -B eval\\adviser\\run_checks.py. Re-run development conversations: .\\venv\\Scripts\\python.exe -B eval\\adviser\\run_conversations.py --model artifacts\\intent_v7.pkl --output ..\\reports\\adviser-evaluation-2026-10-22\\conversation-checks-v7.json. The final evaluator deliberately refuses to overwrite an existing result; it is not a tuning loop.')
p('The active manifest selects intent_v7.pkl. v5 is preserved, and the prior manifest is saved in Flamma/eval/adviser/previous-active-intent-model.json. For a temporary rollback before starting the app, set FLAMMA_INTENT_MODEL=artifacts\\intent_v5.pkl in that process environment. Keep final-test evidence and the candidate lock unchanged. The older reports/2026-10-22 folder is a historical inventory snapshot and has not been rewritten.')
p('Suggested adviser statement: "We completed a new 260-message authored test, with zero exact overlap against scanned training/prior tests. V5 achieved 90.77% accuracy and macro F1 0.8927; the development-selected v7 achieved 93.08% and macro F1 0.9296. V7 fixes the seven original errors, with 18 failures on the new test retained without tuning. We passed 354 software checks, 289 scripted conversation turns and browser checks at four viewport sizes. Held-out image accuracy, dermatologist validation and human usability results remain pending. Synthetic image tests exposed an image-gate limitation that we disclose."')

text='\n'.join(lines)
(OUT/'ADVISER_EVALUATION.md').write_text(text,encoding='utf-8')
def render(source):
    blocks=[];i=0
    while i<len(source):
        line=source[i]
        if not line:i+=1;continue
        if line.startswith('| '):
            rows=[]
            while i<len(source) and source[i].startswith('| '):
                rows.append([v.strip() for v in source[i].strip('|').split('|')]);i+=1
            blocks.append('<table><thead><tr>'+''.join('<th>'+html.escape(v)+'</th>' for v in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in row)+'</tr>' for row in rows[2:])+'</tbody></table>');continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#'));blocks.append(f'<h{level}>'+html.escape(line[level:].strip())+f'</h{level}>')
        else:blocks.append('<p>'+html.escape(line)+'</p>')
        i+=1
    return '\n'.join(blocks)
css='body{font:15px/1.6 system-ui,sans-serif;max-width:1150px;margin:36px auto;padding:0 24px;color:#192537}h1,h2{color:#913c24}h2{margin-top:32px}table{border-collapse:collapse;width:100%;font-size:12px;margin:20px 0}th,td{padding:8px;border:1px solid #cdd3d9;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#f3e9e5}tr:nth-child(even){background:#fafafa}p,pre{overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:11px;background:#f5f6f7;padding:12px}.review{min-height:65px;border:1px solid #bbb;padding:12px}@media print{body{font-size:10pt;margin:0;padding:0}table{font-size:8pt}tr{break-inside:avoid}h2,h3{break-after:avoid}thead{display:table-header-group}@page{size:A4 landscape;margin:13mm}}'
def document(title,body):return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+css+'</style><body>'+body+'</body></html>'
(OUT/'ADVISER_EVALUATION.html').write_text(document('Flamma — adviser evaluation',render(lines)),encoding='utf-8')

# Package current clinical source text without inventing or approving guidance.
clinical=['data/knowledge_base.json','data/treatment_guidance.json','data/course_guidance.json',
          'data/expert_rules.json','model/safety.py','model/expert_system.py']
manifest=[];body=['<h1>Flamma — dermatologist review source snapshot</h1><p>Status: awaiting actual dermatologist review and signature. All content below is existing implementation material; inclusion is not approval.</p>']
for name in clinical:
    path=PROJECT/name;manifest.append({'path':name,'sha256':sha(path)})
    body.extend(['<h2>'+html.escape(name)+'</h2><p>SHA-256: '+sha(path)+'</p><pre>'+html.escape(path.read_text(encoding='utf-8'))+'</pre>',
                 '<div class="review">Decision: acceptable / revise / unsafe / not applicable<br>Clinical comments and required change:<br><br>Reviewer initials / date:</div>'])
(OUT/'DERMATOLOGIST_SOURCE_REVIEW.html').write_text(document('Dermatologist review — not validated','\n'.join(body)),encoding='utf-8')
(OUT/'clinical-review-source-manifest.json').write_text(json.dumps({'status':'awaiting_dermatologist_validation','files':manifest},indent=2)+'\n')
for name in ['DERMATOLOGIST_REVIEW.md','USABILITY_STUDY.md','IMAGE_DATA_REQUIREMENTS.md']:
    (OUT/name).write_bytes((HERE/name).read_bytes())
with (OUT/'dermatologist-review-matrix.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['source','sha256','decision','severity','reviewer_comments','required_change','reviewer_initials','review_date'])
    w.writerows([x['path'],x['sha256'],'','','','','',''] for x in manifest)
with (OUT/'usability-participant-template.csv').open('w',newline='',encoding='utf-8-sig') as f:
    csv.writer(f).writerow(['participant_id','device','viewport','task','completed','assisted','seconds','error_count','comments'])
summary={'generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
         'active_model':'intent_v7.pkl','active_model_sha256':v7['sha256'],'final_samples':260,
         'v5_accuracy':v5['accuracy'],'v5_macro_f1':v5['classification_report']['macro avg']['f1-score'],
         'v7_accuracy':v7['accuracy'],'v7_macro_f1':v7['classification_report']['macro avg']['f1-score'],
         'original_errors_fixed':7,'new_final_v7_errors':len(v7['failures']),
         'software_tests_passed':software['tests_run'],'real_model_conversation_turns_passed':conversation['passed'],
         'browser_successful':browser['successful'],'heldout_image_results':'pending_dataset',
         'dermatologist_review':'pending_reviewer','human_usability':'pending_participants',
         'observed_open_issue':'Uniform and noisy skin-colored synthetic inputs accepted by image gate.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
