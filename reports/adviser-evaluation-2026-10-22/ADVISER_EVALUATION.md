# Flamma — adviser evaluation results

22 October 2026, Asia/Manila. This report supersedes the earlier model inventory for current model selection. It distinguishes measured software behavior, authored text classification, synthetic image transport checks, and unfinished clinical/image evaluation.

## Checklist status

| Adviser item | Status | Evidence / remaining work |
| --- | --- | --- |
| 1. New Intent v5 dataset | Completed with annotation limitation | 260 newly authored messages; v5 and locked v7 tested once. Independent human label review remains pending. |
| 2. Seven original intent errors | Fixed; further errors reported | v7 fixes all original seven. Old development benchmark 129/130; one different severity error. New final set has 18 v7 errors, retained without tuning. |
| 3. Active image held-out metrics | Pending data | Test dataset and split provenance not confirmed. Evaluator and manifest requirements prepared. No new disease accuracy claimed. |
| 4. Dermatologist expert-system validation | Pending reviewer | Review form and source bundle prepared. Expert rules remain empty and awaiting validation. No clinical sign-off claimed. |
| 5. Complete conversations | Automated checks completed | 106 authored scenarios / 289 turns passed using real v7; browser checks cover follow-up, reload persistence, reset and fallback. |
| 6. Image/chatbot integration | Automated checks completed | All six label mappings and rejection checked with fixtures; 12 real-model HTTP smoke uploads checked with synthetic pixels. Image recognition accuracy remains unmeasured. |
| 7. Safety and uncertainty | Software fixes/checks completed; image-gate limitation open | Low-confidence success payloads and explicit uncertainty now rejected. Nonfinite expert-system scores rejected. Emergency/negation tests pass. Synthetic flat/noisy skin colors were accepted by image gate; clinical validation pending. |
| 8. Usability and performance | Automated portion completed; human study pending | Four browser viewports and local timings recorded. No participant task-success rate, satisfaction or SUS score exists. |

## New frozen 260-message test

The final set contains 20 messages for each of 13 intents, including typos, short replies, ambiguous questions and varied phrasing. It was frozen and hashed before development training. Normalized exact overlap was zero against training JSON, historical evaluation JSON, and string constants in prior top-level test/evaluation Python files. One template group overlaps training; semantic independence is not established by exact deduplication. Cases and provisional labels were authored by the coding assistant; independent human annotation/adjudication is still needed.

| Model | Correct / 260 | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | --- | --- | --- | --- | --- |
| intent_v5.pkl | 236/260 | 90.77% | 0.9052 | 0.9077 | 0.8927 |
| intent_v7.pkl | 242/260 | 93.08% | 0.9328 | 0.9308 | 0.9296 |

The absolute accuracy improvement is 2.31 percentage points (six additional correct messages). Both models have zero exact overlap with their training corpora. The current manifest selects v7; v5 remains unchanged. Selection and activation occurred before final predictions, using development evidence only. No threshold, classifier, or application source was changed after examining final results. The final set is now consumed and must not be recycled for tuning or model selection.

### Results per intent (20 test messages each)

| Intent | v5 precision | v5 recall | v5 F1 | v7 precision | v7 recall | v7 F1 |
| --- | --- | --- | --- | --- | --- | --- |
| bot_identity | 0.8636 | 0.9500 | 0.9048 | 0.8571 | 0.9000 | 0.8780 |
| confirmation | 0.6897 | 1.0000 | 0.8163 | 0.8261 | 0.9500 | 0.8837 |
| duration | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| emergency | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| goodbye | 0.8696 | 1.0000 | 0.9302 | 0.9091 | 1.0000 | 0.9524 |
| greeting | 1.0000 | 0.8500 | 0.9189 | 1.0000 | 0.8500 | 0.9189 |
| image_upload | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| location | 0.8636 | 0.9500 | 0.9048 | 0.9500 | 0.9500 | 0.9500 |
| medication | 0.9091 | 1.0000 | 0.9524 | 0.9091 | 1.0000 | 0.9524 |
| severity | 0.9524 | 1.0000 | 0.9756 | 1.0000 | 1.0000 | 1.0000 |
| symptom | 0.9524 | 1.0000 | 0.9756 | 0.9524 | 1.0000 | 0.9756 |
| thanks | 1.0000 | 0.8500 | 0.9189 | 1.0000 | 0.8000 | 0.8889 |
| unknown | 0.6667 | 0.2000 | 0.3077 | 0.7222 | 0.6500 | 0.6842 |

Unknown and ambiguous wording remains a weakness. Improvements are aggregate; some greeting, confirmation, thanks and identity cases still fail or regress. The classifier is a message router; raw intent accuracy does not measure diagnosis, referral safety, or whether the conversation rules ultimately provide an appropriate answer.

### All remaining v7 final-test errors

| Case | New authored message | Expected | Predicted |
| --- | --- | --- | --- |
| F007 | Greetings to you, Flamma assistant. | greeting | bot_identity |
| F014 | Hello again, I'm back at the keyboard. | greeting | goodbye |
| F020 | Greetings, skin information assistant! | greeting | bot_identity |
| F044 | Only the skin between my second and third toes is affected. | location | symptom |
| F114 | Yeh, precisely what I meant. | confirmation | unknown |
| F201 | Many thanks for putting that into plain language. | thanks | unknown |
| F203 | Thank you for explaining the score so clearly. | thanks | unknown |
| F211 | Thanks a million for walking me through it. | thanks | goodbye |
| F215 | Thnks for explaining that bit, bot. | thanks | unknown |
| F233 | Are you able to prescribe a personal medicine dose? | bot_identity | medication |
| F240 | What can this prototype reliably claim about its accuracy? | bot_identity | unknown |
| F242 | Would the same apply to it, whatever it was? | unknown | location |
| F246 | Can you do the thing with the stuff from before? | unknown | medication |
| F248 | Could that work for this without knowing what this is? | unknown | bot_identity |
| F252 | Is it okay though, whatever it is? | unknown | confirmation |
| F253 | Would you say so about that thing? | unknown | confirmation |
| F257 | Does this count as that or is that this? | unknown | confirmation |
| F259 | Perhaps yes, perhaps no, I need to clarify the question. | unknown | confirmation |

All v5 errors, all predictions, per-intent precision/recall/F1 and both confusion matrices are included in final-text-results.json and the companion CSV files. Do not omit these failures from an adviser presentation.

## Development fixes and provenance

The original errors came from confusing descriptions of affected skin with actual anatomical locations, underrepresented descriptions of already attached/uploaded photos, and vague duration phrases. Three separately versioned candidates were trained using fictional development examples, not the new final set. The original v5 artifact and every candidate metadata file were preserved. One candidate supplement initially matched a sentence from the old benchmark; the training overlap guard refused that attempt, and the exact sentence was excluded before fitting. The refusal is disclosed rather than counted as a trained model.

| Candidate | Original seven fixed | Old development benchmark | Macro F1 |
| --- | --- | --- | --- |
| v6 | 6/7 | 98.46% | 0.9846 |
| v7 | 7/7 | 99.23% | 0.9923 |
| v8 | 6/7 | 99.23% | 0.9923 |

v7 was selected because it fixed all seven known errors and improved the old benchmark. It still misclassifies "the itching has become extremely uncomfortable" as symptom instead of severity. v8 was not selected because one of the original seven errors regressed. These repeated development comparisons should not be presented as independent final-test evidence.

| Known development message | Expected | v5 | v7 |
| --- | --- | --- | --- |
| there is an irritated patch that keeps itching | symptom | location | symptom |
| I've noticed some new irritated areas | symptom | location | symptom |
| the skin issue appears near my right shoulder | location | symptom | location |
| the irritation has been present for several days | duration | symptom | duration |
| I've attached a picture of the affected skin | image_upload | location | image_upload |
| here is an image showing the skin problem | image_upload | location | image_upload |
| I uploaded an image showing the affected spot | image_upload | location | image_upload |

v7 training: 6,814 inputs; 6,735 unique examples; 79 duplicates removed; no conflicting labels. The additional development supplement contains 330 patterns. Model: balanced logistic regression on 384-dimensional frozen MiniLM embeddings, C=2.0, max_iter=2000, seed=42. Parameter selection used one grouped validation fold with 5,383 training / 1,352 validation examples, accuracy 96.15% and macro F1 0.9546. It was refit on the full development corpus. Fold membership differs from v5; do not treat their validation rows as an identical held-out comparison.

### Safety fixes implemented

The chatbot now enforces the image service's 0.55 acceptance floor even if a response is marked status=ok. An explicit is_confident=false also rejects the response. Invalid or low-confidence results cannot establish a current condition or reuse an earlier photo's treatment context. Boolean image confidence values are rejected. The separate expert-system evaluator now rejects NaN and infinity confidence values. Existing warning escalation, negation, medicine boundaries and normal-skin caveats remain covered by regression checks. These are software safeguards; dermatologist validation remains pending.

## Conversation, API and browser results

| Check | Observed result |
| --- | --- |
| Python software regressions | 354 run; no failures/errors/skips |
| Frontend automated checks | 27 passed; production build completed |
| Real-model authored development conversations | 289/289 turns across 106 scenarios |
| In-process API performance calls | 30 calls; 0 non-200 responses |
| Simulated class/rejection API mapping | All six classes plus rejection passed |
| Browser viewports | 360 x 800; 390 x 844; 768 x 1024; 1366 x 900; no horizontal overflow; composer accessible and visible |
| Browser conversation flow | Follow-up, treatment context, refresh persistence, reset, fallback and emergency routing passed |
| Browser uploads | All six simulated labels and rejection passed |
| Browser runtime | Zero uncaught JavaScript exceptions |

Conversation suites are authored development/regression checks. Counts must not be combined with the 260-message final classifier evaluation as if they were independent diagnostic samples. Browser image responses were simulated, and mobile checks use emulation rather than physical devices. Four viewport screenshots are included. No human usability outcome was measured.

## Performance observed on this computer

| Measurement | Samples | Median | 95th percentile | Scope |
| --- | --- | --- | --- | --- |
| Warm real-model reply | 289 | 16.3 ms | 22.4 ms | Python reply; excludes browser/network/model startup |
| In-process Flask request | 30 | 13.9 ms | 17.4 ms | Test-client requests; excludes network |
| Browser send to rendered reply | 10 | 106.7 ms | 174.0 ms | Local browser + HTTP + rendering; 50 ms polling resolution |
| Real image pipeline, accepted synthetic input | 6 | 0.452 s | 0.606 s | Actual CPU v10-1, HTTP, Grad-CAM and chatbot mapping |
| Real image pipeline, rejected synthetic input | 6 | 0.060 s | 0.117 s | Skin/OOD rejection paths |

Text-model construction/loading took 13.74 seconds (excluding module import time). Image backend startup took 5.56 seconds including imports. These small local samples are descriptive, not load tests or production service guarantees. Error counts above describe expected software behavior and HTTP status, not clinical error rates.

## Image accuracy remains pending — observed gate limitation

The active image weights are still ResNet-50 v10-1. Its saved test_accuracy is null, and no held-out image test dataset or split provenance has been confirmed. Accordingly, accuracy, precision, recall, macro F1, confusion matrix and per-disease diagnostic performance for v10-1 remain unmeasured. Archived v3's 95.19% must not be reused as the v10-1 result.

The actual v10-1 HTTP integration smoke used four synthetic pixel patterns, three repeats each. Blue pixels were rejected by the skin-content gate and random pixels by the OOD gate. Uniform skin-colored pixels and noisy skin-colored pixels were accepted (six accepted uploads total), despite containing no genuine lesion photograph. This is an observed out-of-distribution gate limitation. The smoke passes transport/state/wording invariants; it does not pass a claim that unsupported images are reliably rejected. Do not describe it as diagnostic validation.

A held-out evaluator is implemented in Flamma/eval/adviser/evaluate_images.py. It reports raw metrics for every supported labeled image, accepted-only metrics alongside coverage, per-class rejection, end-to-end correct accepted predictions divided by all supported images, and unsupported-image rejection. Dataset provenance and optional exact/patient/source training overlap are recorded. Thresholds are fixed; no calibration is performed on the final image set. See IMAGE_DATA_REQUIREMENTS.md for the manifest and command.

## Dermatologist and human usability review remain pending

The expert-system JSON has status=awaiting_dermatologist_validation and an empty rules list. No dermatologist-approved recommendations or clinical rule validation were established. A review form, editable review matrix, and a source snapshot are included. They cover explanations, treatment information, red flags, referral, unsupported conditions, uncertainty, medicine boundaries and normal-skin interpretation. A qualified reviewer must review actual responses and sign the scoped decision. No review request was sent.

USABILITY_STUDY.md defines participant tasks, outcomes and a recording template. Human comprehension, task success, satisfaction, physical mobile-device behavior, assistive technology and SUS remain pending participant testing.

## Evidence, reproduction and rollback

Primary final evidence: final-text-results.json, intent_v5-final-*.csv and intent_v7-final-*.csv. Development and locking evidence: Flamma/eval/adviser/PROTOCOL.md, final-set.lock.json, candidate.lock.json, development supplements and artifacts/intent_v6–v8.metadata.json. Software/browser/performance evidence is stored beside this report. Clinical source snapshots are listed with hashes in clinical-review-source-manifest.json.

Re-run software checks from the Flamma directory: .\venv\Scripts\python.exe -B eval\adviser\run_checks.py. Re-run development conversations: .\venv\Scripts\python.exe -B eval\adviser\run_conversations.py --model artifacts\intent_v7.pkl --output ..\reports\adviser-evaluation-2026-10-22\conversation-checks-v7.json. The final evaluator deliberately refuses to overwrite an existing result; it is not a tuning loop.

The active manifest selects intent_v7.pkl. v5 is preserved, and the prior manifest is saved in Flamma/eval/adviser/previous-active-intent-model.json. For a temporary rollback before starting the app, set FLAMMA_INTENT_MODEL=artifacts\intent_v5.pkl in that process environment. Keep final-test evidence and the candidate lock unchanged. The older reports/2026-10-22 folder is a historical inventory snapshot and has not been rewritten.

Suggested adviser statement: "We completed a new 260-message authored test, with zero exact overlap against scanned training/prior tests. V5 achieved 90.77% accuracy and macro F1 0.8927; the development-selected v7 achieved 93.08% and macro F1 0.9296. V7 fixes the seven original errors, with 18 failures on the new test retained without tuning. We passed 354 software checks, 289 scripted conversation turns and browser checks at four viewport sizes. Held-out image accuracy, dermatologist validation and human usability results remain pending. Synthetic image tests exposed an image-gate limitation that we disclose."
