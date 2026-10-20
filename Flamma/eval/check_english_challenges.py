"""Authored development conversations; not independent clinical validation."""

import argparse
import hashlib
import json
from pathlib import Path

from model.config import PROJECT_DIR
from model.semantic_chatbot import SemanticChatbot
from model.knowledge_base import management_style


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=PROJECT_DIR / 'eval/english_challenge_cases.json')
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    base = SemanticChatbot()
    results = []
    for case in cases:
        bot = base.new_conversation()
        if case.get('initial_state'):
            bot.conversation.restore(case['initial_state'])
        for step, turn in enumerate(case['turns'], 1):
            reply = bot.reply(turn['text'])
            errors = []
            if reply['intent'] != turn['intent']:
                errors.append(f"intent {reply['intent']} != {turn['intent']}")
            for key, value in turn.get('state', {}).items():
                if bot.conversation.get(key) != value:
                    errors.append('incorrect state: ' + key)
            if 'contains_topic' in turn:
                key = bot.conversation.get('knowledge_disease')
                expected = bot.knowledge.get(key, turn['contains_topic'])
                if turn['contains_topic'] == 'management' and management_style(turn['text']) in {'treatability', 'curability'}:
                    info = bot.knowledge.treatment_info(key) or {}
                    expected = info.get('brief_answers', {}).get(management_style(turn['text'])) or expected
                if not expected or expected not in reply['reply']:
                    errors.append('missing requested topic: ' + turn['contains_topic'])
            for phrase in turn.get('contains', []):
                if phrase not in reply['reply']:
                    errors.append('missing reply phrase: ' + phrase)
            for phrase in turn.get('excludes', []):
                if phrase in reply['reply']:
                    errors.append('unexpected reply phrase: ' + phrase)
            if len(reply['reply'].split()) > turn.get('max_words', float('inf')):
                errors.append('reply exceeds requested word limit')
            results.append(dict(scenario=case['name'], step=step, text=turn['text'], expected=turn['intent'],
                                intent=reply['intent'], predicted=reply.get('predictedIntent'),
                                confidence=reply.get('modelConfidence'), errors=errors, passed=not errors))
    failed = [result for result in results if not result['passed']]
    report = dict(scope='authored_english_development_conversations_not_medical_accuracy',
                  model_path=str(base.classifier.model_path),
                  model_sha256=hashlib.sha256(base.classifier.model_path.read_bytes()).hexdigest(),
                  scenarios=len(cases), turns=len(results), passed=len(results)-len(failed), failures=failed, results=results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['scenarios', 'turns', 'passed', 'failures']}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
