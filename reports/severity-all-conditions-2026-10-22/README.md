# Severity discussion for all covered conditions — 22 October 2026

Every entry in Flamma's knowledge library now has its own severity guidance
profile and cited sources in `Flamma/data/severity_guidance.json`.

| Condition / label | Condition-specific discussion |
| --- | --- |
| Dermatitis / eczema | Symptoms, spread, daily impact, and clarification of subtype or contact trigger |
| Atopic dermatitis | Itch, scratching, sleep, extent and recurring flare pattern |
| Contact dermatitis | Itch/burning/cracking, contact distribution, daily tasks and possible continued exposure |
| Lichen planus | Skin and mouth/genital sites, daily impact, scalp hair loss and nail changes |
| Psoriasis | Affected sites, estimated coverage, symptom impact and new joint symptoms |
| Rosacea | Facial symptoms, daily impact, eye symptoms and urgent eye-warning interruption |
| Hives / urticaria | Welts, spread, itch, individual-welt duration and recurrence; warning interruption |
| Normal-skin screening label | Symptoms despite the label; no disease-severity classification or assurance that disease is absent |

Questions and answers remain separate from diagnosed conditions and the ordinary
screening severity field. The chatbot records the user's descriptions and
summarizes burden; it does not calculate a validated score or assign a clinical
mild/moderate/severe grade. The curated content still requires dermatologist
review. Psoriasis body-surface guidance and joint questions are not reused as
severity criteria for other diseases. Hives remains a text-information topic,
not an added image class.

Rosacea eye pain, vision change or light sensitivity, and hives with faintness
or racing heart interrupt the optional questions with source-based care advice.
Existing emergency checks still run first. These prototype rules need the
planned clinical review; software tests do not establish triage accuracy.

Verification artifacts:

- `software-checks.json` / `.log`: feature tests plus the existing regression suite.
- `real-model-checks.json` / `.log`: feature tests with actual intent v7 and simulated photo results.
- `existing-conversations.json`: existing real-model development conversations.
- `all-condition-examples.json`: new demonstration exchanges for every library entry.
- `source-snapshot.json`: exact source checksums; classifier weights remain unchanged.
- `live-service-check.json`: condition coverage verified through the reloaded local service.

Earlier reports remain snapshots of their original source and results. The
consumed 260-message final set was not reused and the classifier was not
retrained for this feature.

Reproduce from the Flamma directory:

```powershell
.\venv\Scripts\python.exe -B eval\check_severity_guidance.py --real-model --output-dir ..\reports\severity-all-conditions-2026-10-22
```
