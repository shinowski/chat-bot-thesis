# Dermatologist validation — review required

Status: NOT REVIEWED. Prepared materials are not dermatologist approval. `data/expert_rules.json` currently contains no validated rules. The current chatbot's educational responses come from the knowledge library and conversation/safety rules, not an approved clinical expert-rule set.

Reviewer name: __________  Credentials/registration: __________
Date: __________  Reviewed software/artifact hashes: __________
Intended users and setting: __________  Age/pregnancy exclusions: __________

For every item, record: acceptable / revise / unsafe / not applicable; severity; rationale; required change; and reviewer initials. Review the actual generated wording, not only a condition name. Review must cover skin-tone variation, sensitive body areas, pediatric cases, pregnancy, immunosuppression, coexisting illness, and uncertain or misleading photographs.

| Review area | Material to review | Decision / required changes |
| --- | --- | --- |
| Supported-condition explanations | `data/knowledge_base.json`, all entries and topics | |
| General care and medicine boundaries | `data/treatment_guidance.json`, all six image classes plus dermatitis/hives information | |
| Course and prognosis wording | `data/course_guidance.json`; ensure no individual recovery promises | |
| Red flags and escalation | `model/safety.py`: patterns, negation, general questions, emergency and referral wording | |
| Referral thresholds | Each condition's referral text and general-care responses | |
| Unsupported conditions | Out-of-scope and rejection responses; supported labels cannot rule out other disease | |
| Low confidence and normal skin | Scores, rejected image follow-ups, normal-skin caveat and symptom escalation | |
| Individual medication requests | No personal prescription, dose or suitability determined from chat/photo | |
| Mixed or contradictory histories | Clarification, unknown answers, symptom denials and context reset | |
| Proposed expert-system rules | `data/expert_rules.json`; no rules are approved yet | |

Suggested structured case review (use fictional cases; reviewer assigns expected disposition): severe symptom escalation; a general question about red flags; negated breathing difficulty; worsening rash despite a normal-skin image match; unsupported disease; low image score; two possible conditions; medicine suitability request; a new rash after previous screening; dermatitis subtype image result; a photo followed by an unrelated condition question.

Review each frozen final-text failure and any image false-normal or accepted unsupported case once image data is available. Record disagreements and adjudicate without tuning the already consumed final sets. Material revisions require new review and a new independent final evaluation.

Overall decision: approved for specified educational prototype setting / revise and resubmit / rejected.

Approved scope and exclusions: __________
Unresolved risks: __________
Follow-up/review expiry: __________
Signature and date: __________

Do not mark this checklist complete until an actual qualified reviewer signs it. No review request has been sent automatically.
