# Flamma: evidence and limitations for a panel defense

## A claim supported by this implementation

Flamma is an English-first educational skin-information and screening prototype.
It organizes reported symptoms, handles follow-up questions, and presents the
image service's supported screening matches. It does not confirm a diagnosis,
prescribe an individualized medicine or dose, or provide validated clinical triage.

## Questions a panel can reasonably ask

| Question | Evidence-based answer |
| --- | --- |
| What did you train? | A balanced logistic-regression text-intent classifier over locally cached MiniLM sentence embeddings. The classifier has 13 message categories. The sentence-embedding model was not fine-tuned. Context rules and a curated information library supply the replies. |
| Does 94.6% mean skin-diagnosis accuracy? | No. v5 correctly categorized 123 of 130 authored text messages. Macro F1 was 0.948. These are raw text-intent results, separate from image accuracy, disease prevalence, clinical outcomes, and end-to-end conversation results. |
| Is this an independent final test? | No. The 130-message benchmark was excluded from fitting but reused across versions. It supports engineering comparisons and carries selection-bias risk. A fresh, independently authored final evaluation is still needed. |
| What does grouped validation mean here? | Similar template variations are grouped by body area, symptom, timeframe, severity, and product. Parameter selection used fold 0 of a five-way stratified grouped split. The reported validation result is one fold, not an average across all five folds. |
| What data was used? | v5 used 6,405 unique fictional English examples, including 524 new broader English examples. The report records source checksums, duplicates, conflicts, package versions, and selected regularization. Saved chats and photos were not used for this training. |
| Does a 97% reply score mean 97% medically correct? | No. Message intent and photo model scores have different meanings. Neither is a measured probability that the person has a disease. Clinical score calibration has not been established here. The interface now labels each score's source visibly. |
| Does the bot learn while people chat? | No. Conversations persist as records. Model training is a separate explicit process. |
| What happens with unsupported diseases or rejected photos? | Rejection invalidates the current photo result and its condition-specific care context. A later named condition can receive general information without being treated as a diagnosis. Supported-class screening cannot rule out diseases outside its labels. |
| Does every condition in the information menu have a trained image class? | No. The information library and the image-label interface are separate. Hives has text information but is not an accepted image label. The chatbot adapter accepts dermatitis, its atopic/contact subtypes, lichen planus, psoriasis, rosacea, and normal-skin labels. Acceptance by the adapter does not prove the partner's active image model was trained or evaluated for every label; verify that against its own artifact and evaluation report. |
| Are medicine questions treated as medication use? | They are tracked separately. Named products and questions do not establish use; explicit use reports are required. Tests cover unknown products, actual usage, and separation of rash onset from treatment duration. |
| Is the storage private or encrypted? | Records are stored in SQLite on the Flamma server and isolated by browser session. There is no account sign-in or application-level encryption. Shared-profile users and server-file access remain risks. This is not a claim of production privacy readiness. |
| What does deletion do? | It removes that browser session's application records, including messages, photos, and associated request receipts. Exported text, backups, and older logs are separate copies. Do not claim certified secure erasure. |
| How do you know the demo uses the evaluated model? | Compare `/health`'s `intent_model` and `intent_model_sha256` with `artifacts/active_intent_model.json` and `artifacts/intent_v5.metadata.json`. Startup refuses a selected artifact whose checksum differs from the manifest. This detects file/report mismatch, not malicious modification of both files. |
| Did passing conversation tests prove medical safety? | No. Authored regression tests demonstrate specified software behavior. Image fixtures simulate classifications and do not test image recognition. Warning rules still need clinician review and prospective safety evaluation. |

## Evidence to show

- `artifacts/intent_v5.metadata.json`: training provenance, validation, reused benchmark results, baseline and candidate artifact hashes.
- `eval/results/intent-v5-generalization.json`: 65 additional authored text-intent examples, with no exact or grouped-template overlap found against the training corpus. This remains a small authored evaluation, not clinical validation.
- `eval/check_english_chatbot.py`: multi-turn tests using the real text classifier, including uncertainty, privacy, medication context, and warning routing.
- `test_panel_readiness.py`: explicit tests for score explanations, privacy claims, runtime model identity, and rejection of changed artifacts before deserialization.
- `data/treatment_guidance.json`: general-care information and source links. These are curated educational entries, not a personalized treatment generator.

To reproduce the claim, storage, and artifact checks, run these from the `Flamma`
folder. The benchmark command prints and saves the seven incorrect v5 predictions
as well as its correct predictions; include failures when presenting the result.

```powershell
.\venv\Scripts\python.exe -B -m unittest test_panel_readiness test_chat_history test_safety_and_reliability
node --test eval/test_model_score.mjs
.\venv\Scripts\python.exe -B eval/final_evaluation.py --output eval/results/panel-intent-benchmark.json
```

## A short, reproducible demo

Use a fresh synthetic conversation. Avoid real identifying photos or patient data.

1. Open **About this prototype and saved chats**. Explain scope, storage, and model-score limits.
2. Enter **My rash is on my arm for two weeks**, then **I used a cream for three days**. Show that rash onset and treatment use remain separate.
3. Enter **Actually, twenty-one days, not two weeks**, then **The rash has come back today**. Request a summary and show that recurrence did not replace onset.
4. Ask **Is dermatitis treatable?**, then **and roseaca**. Show the named-condition change and general-information wording.
5. Ask **Is this my skin condition?** and **What does 94.6% accuracy mean?**. Show that neither confirms a diagnosis.
6. In another synthetic conversation, enter **two nights or twenty days** and select **second one**. Demonstrate clarification instead of silently choosing.
7. Enter **I cannot breathe** as a clearly identified test message. Show that warning routing overrides ordinary screening; do not present it as clinically validated triage.
8. Export, delete, and reopen the synthetic conversation to demonstrate record controls. Keep exports separate from deletion claims.

## Work that code changes cannot establish

Before a clinical or real-patient deployment claim, obtain qualified clinical
review, an independent evaluation protocol, and appropriate access and storage
protections. Evaluate the image service separately on labeled, consented data,
including unsupported conditions, false-normal matches, skin tones, devices,
lighting, and rejection behavior. Use independent annotation and adjudication
for ambiguous examples. Report sample sizes, per-class precision/recall,
confusion matrices, uncertainty, and failure cases. Keep that final test out of
training, prompt/rule tuning, and repeated model selection.

The partner-owned image model was not modified by these chatbot improvements.
