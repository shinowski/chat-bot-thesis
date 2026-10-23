"""Contextual quick replies shared with the browser, including older messages."""

import json
from pathlib import Path
import re


with (Path(__file__).resolve().parents[1] / 'static/reply-choices.json').open(encoding='utf-8') as file:
    POLICY = json.load(file)


def choice_context(result, question=None):
    intent = result.get('intent', '')
    if POLICY['intentContexts'].get(intent) == 'safety':
        return 'safety'
    if result.get('choiceContext') in POLICY['contexts']:
        return result['choiceContext']
    if question in POLICY['contexts']:
        return question
    if result.get('action') == 'upload_image':
        return 'upload'
    # Older saved messages lack question metadata. Recognize the question
    # actually asked instead of guessing from the user's preceding intent.
    text = result.get('reply') or result.get('text') or ''
    ending = re.split(r'\n\s*\n', text)[-1]
    if '?' in ending:
        for rule in POLICY['questionRules']:
            if re.search(rule['pattern'], ending, re.IGNORECASE):
                return rule['context']
    return POLICY['intentContexts'].get(intent, intent if intent in POLICY['contexts'] else 'default')


def with_reply_choices(result, question=None):
    if result.get('who') == 'user':
        return result
    context = choice_context(result, question)
    existing = result.get('followUps')
    existing = existing if isinstance(existing, list) else []
    # Warning replies offer care/support actions, never optional screening
    # answers or photo uploads that could obscure their existing guidance.
    if context == 'safety':
        existing = []
    choices, seen = [], set()

    def append(value):
        if isinstance(value, str) and value.strip() and value.strip().lower() not in seen:
            choices.append(value.strip())
            seen.add(value.strip().lower())

    if result.get('action') == 'upload_image' and context != 'safety':
        append(POLICY['photoChoice'])
    for value in existing:
        append(value)
    for value in [*POLICY['contexts'][context], *POLICY['contexts']['default']]:
        if len(choices) >= POLICY['minimum']:
            break
        append(value)
    return {**result, 'followUps': choices, 'choiceContext': context}
