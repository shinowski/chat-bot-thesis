"""Exercise the actual selected classifier through multi-turn chatbot behavior."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from model.config import PROJECT_DIR
from model.semantic_chatbot import SemanticChatbot


SCENARIOS = [
    ('ambiguous_conditions_keep_requested_topic', [
        {'text': 'Could it be eczema or psoriasis? How do I treat it?', 'intent': 'condition_clarification', 'state': {'classification': None, 'knowledge_disease': None}},
        {'text': 'second one', 'intent': 'knowledge_question', 'state': {'knowledge_disease': 'psoriasis', 'last_knowledge_topics': ['management']}},
        {'text': 'What is the difference between eczema and psoriasis?', 'intent': 'condition_comparison'},
        {'text': 'and treatment?', 'intent': 'condition_clarification'},
        {'text': 'Dermatitis', 'intent': 'knowledge_question', 'state': {'knowledge_disease': 'dermatitis'}},
    ]),
    ('product_questions_are_not_usage_reports', [
        {'text': 'Can I use this cream for psoriasis?', 'intent': 'product_clarification', 'state': {'medication': None, 'classification': None}},
        {'text': 'hydrocortisone', 'intent': 'product_information', 'state': {'medication': None}},
        {'text': 'is this okay?', 'intent': 'question_clarification'},
    ]),
    ('conflicting_screening_answers', [
        {'text': 'my skin is itchy', 'intent': 'symptom'},
        {'text': 'maybe my arm or my leg', 'intent': 'location_clarification', 'state': {'location': None}},
        {'text': 'both my arm and leg', 'intent': 'location'},
        {'text': 'maybe two days or two months', 'intent': 'duration_clarification', 'state': {'duration': None}},
        {'text': 'three days', 'intent': 'duration', 'state': {'duration': 'three days'}},
    ]),
    ('separate_skin_concerns', [
        {'text': 'my rash is itchy on my arm for two weeks', 'intent': 'location'},
        {'text': 'I used a cream', 'intent': 'medication'},
        {'text': 'I have a new rash on my leg', 'intent': 'new_concern', 'state': {'duration': None, 'medication': None, 'classification': None, 'pending_question': 'duration'}},
        {'text': 'three days', 'intent': 'duration'},
    ]),
    ('symptom_denials_are_not_positive_symptoms', [
        {'text': 'I have no rash or itching', 'intent': 'symptom_denial', 'state': {'symptoms': [], 'denied_symptoms': ['I have no rash or itching']}},
        {'text': 'summarize our conversation', 'intent': 'conversation_summary', 'contains': "Symptoms you've denied"},
        {'text': 'I have no rash but my skin is dry', 'intent': 'symptom'},
    ]),
    ('general_care_questions_and_typos', [
        {'text': 'When should I see a doctor?', 'intent': 'knowledge_question', 'contains': 'Seek medical care promptly if', 'state': {'symptoms': [], 'classification': None, 'screening_paused': False}},
        {'text': 'wen shud i see a docter?', 'intent': 'knowledge_question'},
        {'text': 'whn shld i c a dr?', 'intent': 'knowledge_question'},
    ]),
    ('typos_through_a_conversation', [
        {'text': 'myskin is ithcy on my elbwo', 'intent': 'location', 'state': {'pending_question': 'duration'}},
        {'text': 'sicne 3dasy', 'intent': 'duration'},
        {'text': 'I have been using oinment for 2dasy', 'intent': 'medication', 'contains_state': {'duration': '3dasy', 'medication': 'oinment'}},
        {'text': 'whta is psorisis?', 'intent': 'knowledge_question', 'state': {'knowledge_disease': 'psoriasis', 'classification': None}},
        {'text': 'and treatmnt?', 'intent': 'knowledge_question', 'contains': 'General information about Psoriasis'},
        {'text': 'When should I see a doctor?', 'intent': 'knowledge_question', 'contains': 'For Psoriasis:'},
    ]),
    ('warning_signs_with_typos', [
        {'text': 'wen shud i see a docter? my lips are swolen', 'intent': 'emergency'},
        {'text': 'i dnt have truble brething', 'intent': 'safety_information'},
        {'text': 'my thorat is swolen and i cant brethe', 'intent': 'emergency'},
    ]),
    ('courtesy_and_answers', [
        {'text': 'my skin is itchy', 'intent': 'symptom', 'state': {'pending_question': 'location'}},
        {'text': 'thanks', 'intent': 'thanks', 'state': {'pending_question': 'location'}},
        {'text': 'my left wrist', 'intent': 'location', 'state': {'pending_question': 'duration'}},
        {'text': 'yes', 'intent': 'confirmation', 'state': {'duration': None, 'pending_question': 'duration'}},
        {'text': 'last winter', 'intent': 'duration', 'state': {'pending_question': 'medication'}},
        {'text': "No, I haven't", 'intent': 'medication', 'state': {'medication': 'none'}},
    ]),
    ('medication_is_not_rash_duration', [
        {'text': 'my rash is itchy on my arm for four weeks', 'intent': 'location'},
        {'text': "I've been applying a cream on my leg for five days", 'intent': 'medication', 'contains_state': {'duration': 'four weeks', 'location': 'arm'}},
        {'text': "Actually, I've been using a lotion on my face for three days", 'intent': 'correction', 'contains_state': {'duration': 'four weeks', 'location': 'arm', 'medication': 'lotion'}},
    ]),
    ('named_information_without_diagnosis', [
        {'text': 'I think I have psoriasis', 'intent': 'knowledge_question', 'state': {'classification': None, 'knowledge_disease': 'psoriasis', 'image_uploaded': False}},
        {'text': 'and treatment?', 'intent': 'knowledge_question', 'contains': 'General information about Psoriasis'},
        {'text': 'explain simply', 'intent': 'simple_explanation'},
    ]),
    ('unrelated_questions_do_not_change_skin_context', [
        {'text': 'what is rosacea?', 'intent': 'knowledge_question'},
        {'text': 'Debug my JavaScript', 'intent': 'out_of_scope', 'state': {'knowledge_disease': 'rosacea', 'classification': None}},
        {'text': 'and treatment?', 'intent': 'knowledge_question', 'contains': 'General information about Rosacea'},
    ]),
    ('corrections_replace_explicit_details', [
        {'text': 'my rash is itchy on my arm for two weeks', 'intent': 'location'},
        {'text': 'actually my left leg for three weeks, not my arm', 'intent': 'correction', 'state': {'location': 'left leg', 'duration': 'three weeks'}},
        {'text': 'summarize our conversation', 'intent': 'conversation_summary', 'contains': 'left leg'},
    ]),
    ('unknown_after_information_is_not_a_patient_fact', [
        {'text': 'what is contact dermatitis?', 'intent': 'knowledge_question'},
        {'text': 'idk', 'intent': 'uncertain_answer', 'state': {'location': None, 'duration': None, 'medication': None}},
        {'text': 'what causes it?', 'intent': 'knowledge_question', 'contains': 'General information about Contact Dermatitis'},
    ]),
    ('text_only_conversation', [
        {'text': 'text only please', 'intent': 'image_declined', 'state': {'image_declined': True}},
        {'text': 'my skin is itchy on my arm for two weeks', 'intent': 'location'},
        {'text': 'none', 'intent': 'medication', 'state': {'medication': 'none', 'pending_question': None}, 'not_contains': 'upload'},
        {'text': 'what is atopic dermatitis?', 'intent': 'knowledge_question', 'state': {'classification': None}},
    ]),
    ('capabilities_privacy_and_training', [
        {'text': 'What can you do?', 'intent': 'bot_identity', 'contains': 'summarize'},
        {'text': 'Is my information private?', 'intent': 'bot_identity', 'contains': 'saved on the Flamma server'},
        {'text': 'Do you learn from my messages?', 'intent': 'bot_identity', 'contains': 'does not automatically train'},
    ]),
    ('metaphorical_body_words_are_not_symptoms', [
        {'text': 'My face ID is not working on my phone', 'intent': 'out_of_scope', 'state': {'location': None, 'symptoms': []}},
        {'text': 'Where can I buy a cream-colored sofa?', 'intent': 'out_of_scope', 'state': {'medication': None}},
        {'text': 'My car dashboard has a red warning light', 'intent': 'out_of_scope', 'state': {'symptoms': []}},
    ]),
    ('anxiety_without_diagnosis', [
        {'text': "I'm worried about this", 'intent': 'emotional_support', 'state': {'classification': None}},
        {'text': 'my skin is dry', 'intent': 'symptom'},
    ]),
    ('warning_priority_and_negation', [
        {'text': 'My rash is spreading rapidly and blistering', 'intent': 'medical_attention'},
        {'text': 'I am not having trouble breathing', 'intent': 'safety_information'},
        {'text': 'My tongue is swollen and I cannot swallow', 'intent': 'emergency'},
    ]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=PROJECT_DIR / 'eval/results/english-conversations.json')
    args = parser.parse_args()
    os.environ['FLAMMA_INTENT_MODEL'] = str(args.model.resolve())
    base = SemanticChatbot()
    results, failures = [], []
    for name, turns in SCENARIOS:
        bot = base.new_conversation()
        for step, case in enumerate(turns, 1):
            result = bot.reply(case['text'])
            errors = []
            if result['intent'] != case['intent']:
                errors.append(f"Intent: {result['intent']} != {case['intent']}")
            for key, expected in case.get('state', {}).items():
                if bot.conversation.get(key) != expected:
                    errors.append(f'Incorrect state: {key}')
            for key, expected in case.get('contains_state', {}).items():
                if expected not in str(bot.conversation.get(key)):
                    errors.append(f'Missing state detail: {key}')
            if case.get('contains') and case['contains'].lower() not in result['reply'].lower():
                errors.append('Missing explanation')
            if case.get('not_contains') and case['not_contains'] in result['reply'].lower():
                errors.append('Unwanted reply content')
            record = dict(scenario=name, step=step, text=case['text'], intent=result['intent'], passed=not errors, errors=errors)
            results.append(record)
            if errors:
                failures.append(record)
    report = dict(scope='scripted_english_conversation_regressions_not_medical_accuracy',
                  model_path=str(args.model.resolve()), model_sha256=hashlib.sha256(args.model.read_bytes()).hexdigest(),
                  scenarios=len(SCENARIOS), turns=len(results), passed=len(results)-len(failures), failures=failures, results=results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['scenarios', 'turns', 'passed', 'failures']}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
