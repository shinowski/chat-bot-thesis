# Severity discussion feature — 22 October 2026

The question “how can i know how severe my psoriasis is” now starts a guided
severity discussion instead of a general disease overview. The response explains
that extent, affected sites, plaque features and personal impact matter. It asks
about body areas, coverage, daily-life impact and, for psoriasis, new joint
symptoms. Other conditions receive general symptom-burden discussion, without
applying psoriasis-specific criteria.

Answers stay in a separate `severity_discussion` field and are shown as the
user's descriptions. They do not establish a diagnosis, a clinical mild/moderate/
severe grade, a validated score, or an individualized treatment choice. No new
dermatologist-approved expert rules were claimed. AAD/NPF references and their
check date travel with the response into saved messages and exports.

Optional uncertainty, stopping, reset, topic changes, condition choices, photo
provenance, rejected images, summaries and emergency interruption are covered.

Verification:

- `software-checks.json`: 374 software regressions passed, including 20 new cases.
- `real-model-checks.json`: the 20 new cases also passed with actual intent v7.
- `existing-conversations.json`: 289 existing conversation turns passed.
- `frontend-checks.log`: 27 frontend tests passed; production build completed.
- `example-conversation.txt` / `.json`: actual v7 demonstration transcript.
- `source-snapshot.json`: source checksums for this feature.
- `live-service-check.json`: the exact requested question and four follow-up
  replies verified through the reloaded local service. Its synthetic test
  conversation was deleted afterward.

The text model was not retrained. Earlier adviser evidence and its frozen final
set remain unchanged; that final set was not used to develop or retest this new
conversation behavior. Medical content still needs the planned dermatologist
review, and this is not clinical validation.

Reproduce from the Flamma directory:

```powershell
.\venv\Scripts\python.exe -B eval\check_severity_guidance.py --real-model
```
