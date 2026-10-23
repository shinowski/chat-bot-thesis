"""Run targeted software regressions and retain exact results."""
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT.parent
sys.path.insert(0,str(PROJECT))
OUT = ROOT/'reports/adviser-evaluation-2026-10-22'
OUT.mkdir(parents=True,exist_ok=True)
MODULES = [
    'test_adviser_uncertainty', 'test_image_integration', 'test_safety_and_reliability',
    'test_panel_readiness', 'test_photo_treatments', 'test_photo_topic_context',
    'test_conversation_boundaries', 'test_question_clarification', 'test_progress_uncertainty',
    'test_correction_progress', 'test_diagnosis_followups', 'test_followup_context',
    'test_conversation_followups', 'test_dialogue_intelligence', 'test_topic_switch',
    'test_course_questions', 'test_concise_care', 'test_disease_explanations',
    'test_chat_history', 'test_request_receipts', 'test_chat_training',
    'test_typo_and_care_questions', 'test_english_language_improvements', 'test_text_understanding',
    'test_adviser_image_metrics',
]
log = io.StringIO()
with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
report = {'evaluated_at':datetime.now(timezone.utc).isoformat(),
          'scope':'Software regressions, including simulated image classifications; not image or clinical accuracy.',
          'modules':MODULES,'tests_run':result.testsRun,
          'failures':[{'test':str(test),'traceback':tb} for test,tb in result.failures],
          'errors':[{'test':str(test),'traceback':tb} for test,tb in result.errors],
          'skipped':[{'test':str(test),'reason':reason} for test,reason in result.skipped],
          'successful':result.wasSuccessful()}
(OUT/'software-checks.log').write_text(log.getvalue(),encoding='utf-8')
(OUT/'software-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
