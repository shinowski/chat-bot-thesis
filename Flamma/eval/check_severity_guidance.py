"""Verify severity discussion without reusing the consumed final text set."""
import argparse
import ast
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def run(suite):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    return {
        'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
        'failures': [{'test': str(test), 'traceback': tb} for test, tb in result.failures],
        'errors': [{'test': str(test), 'traceback': tb} for test, tb in result.errors],
        'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
    }, log.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=PROJECT.parent/'reports/severity-guidance-2026-10-22')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tree = ast.parse((PROJECT/'eval/adviser/run_checks.py').read_text())
    modules = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'MODULES' for target in node.targets))
    modules.append('test_severity_guidance')
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    report, log = run(suite)
    report.update(scope='Software regressions with simulated image outputs; not clinical validation.', modules=modules,
                  evaluated_at=datetime.now(timezone.utc).isoformat())
    (args.output_dir/'software-checks.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (args.output_dir/'software-checks.log').write_text(log, encoding='utf-8')
    if args.real_model:
        from model.semantic_chatbot import SemanticChatbot
        from test_image_integration import FakeImageClassifier
        base = SemanticChatbot(image_classifier=FakeImageClassifier())
        def make_real_bot():
            bot = base.new_conversation()
            bot.image_classifier = FakeImageClassifier()
            return bot
        with patch('test_severity_guidance.make_bot', side_effect=make_real_bot):
            real, real_log = run(unittest.defaultTestLoader.loadTestsFromName('test_severity_guidance'))
        real.update(scope='Actual configured text classifier; simulated photo outputs; not clinical validation.',
                    model=str(base.classifier.model_path), model_sha256=base.classifier.model_sha256,
                    evaluated_at=datetime.now(timezone.utc).isoformat())
        (args.output_dir/'real-model-checks.json').write_text(json.dumps(real, indent=2)+'\n', encoding='utf-8')
        (args.output_dir/'real-model-checks.log').write_text(real_log, encoding='utf-8')
        bot = make_real_bot()
        transcript = []
        for message in ['how can i know how severe my psoriasis is', 'Both elbows',
                        'about two handprints', 'It affects my sleep', 'No joint symptoms']:
            reply = bot.reply(message)
            transcript.append(dict(user=message, **reply))
        (args.output_dir/'example-conversation.json').write_text(json.dumps(transcript, indent=2)+'\n', encoding='utf-8')
        (args.output_dir/'example-conversation.txt').write_text('\n\n'.join('You: '+turn['user']+'\nFlamma: '+turn['reply'] for turn in transcript)+'\n', encoding='utf-8')
        detail_answers = {
            'type': 'No known type or trigger', 'flares': 'It comes and goes in flares',
            'exposure': 'A new soap touched the area', 'special_sites': 'No scalp hair loss or nail changes',
            'eyes': 'No eye symptoms', 'pattern': 'A welt fades within hours; new welts for two weeks',
            'joints': 'No joint symptoms',
        }
        condition_examples = {}
        for disease, data in base.knowledge.data.items():
            example = make_real_bot()
            messages = ['How severe is my '+data['name']+'?', 'My arms', 'a few small patches', 'No effect on daily activities']
            entry = base.knowledge.severities.get(disease, {})
            messages.extend(detail_answers[field] for field in entry.get('fields', []) if field in detail_answers)
            condition_examples[disease] = [dict(user=message, **example.reply(message)) for message in messages]
        (args.output_dir/'all-condition-examples.json').write_text(json.dumps(condition_examples, indent=2)+'\n', encoding='utf-8')
        report['real_model_checks'] = real
    paths = [PROJECT/'model/severity_support.py', PROJECT/'model/knowledge_base.py',
             PROJECT/'model/semantic_chatbot.py', PROJECT/'model/context_intent.py',
             PROJECT/'model/conversation.py', PROJECT/'model/safety.py',
             PROJECT/'data/severity_guidance.json', PROJECT/'frontend/src/intents.js']
    (args.output_dir/'source-snapshot.json').write_text(json.dumps({
        'scope': 'New severity feature snapshot; earlier adviser reports remain historical evidence for the earlier application source.',
        'consumed_final_set_reused': False,
        'sources': {str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
    }, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['successful'] and report.get('real_model_checks', {}).get('successful', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
