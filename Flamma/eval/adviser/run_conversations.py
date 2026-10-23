"""Real text model, authored development scenarios, simulated photo replies."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from time import perf_counter

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
os.environ['FLAMMA_INTENT_MODEL']=str(args.model.resolve())
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from model.semantic_chatbot import SemanticChatbot
from model.knowledge_base import management_style
from eval.check_english_chatbot import SCENARIOS
from eval.photo_treatment_browser_server import FixtureImages
from app import create_app
import numpy as np

started=perf_counter()
base=SemanticChatbot(image_classifier=FixtureImages())
load_seconds=perf_counter()-started
scenarios=[{'name':name,'turns':turns,'source':'core'} for name,turns in SCENARIOS]
files=['english_challenge_cases.json','followup_cases.json','diagnosis_followup_cases.json',
       'concise_care_cases.json','topic_switch_cases.json','correction_progress_cases.json',
       'progress_uncertainty_cases.json','vocabulary_cases.json','panel_readiness_cases.json',
       'photo_topic_context_cases.json','course_question_cases.json']
for name in files:
    cases=json.loads((PROJECT/'eval'/name).read_text(encoding='utf-8'))
    scenarios.extend(dict(case,source=name) for case in cases)
results=[]
for case in scenarios:
    bot=base.new_conversation()
    if case.get('initial_state'):
        bot.conversation.restore(case['initial_state'])
    for step,turn in enumerate(case['turns'],1):
        start=perf_counter()
        result=bot.reply(turn['text'])
        seconds=perf_counter()-start
        errors=[]
        if result['intent']!=turn['intent']:
            errors.append('intent '+result['intent']+' != '+turn['intent'])
        for key,value in turn.get('state',{}).items():
            if bot.conversation.get(key)!=value:
                errors.append('incorrect state: '+key)
        for key,value in turn.get('contains_state',{}).items():
            if value not in str(bot.conversation.get(key)):
                errors.append('missing state detail: '+key)
        if 'contains_topic' in turn:
            key=bot.conversation.get('knowledge_disease')
            expected=bot.knowledge.get(key,turn['contains_topic'])
            if turn['contains_topic']=='management' and management_style(turn['text']) in {'treatability','curability'}:
                expected=(bot.knowledge.treatment_info(key) or {}).get('brief_answers',{}).get(management_style(turn['text'])) or expected
            if not expected or expected not in result['reply']:
                errors.append('missing topic: '+turn['contains_topic'])
        contains=turn.get('contains',[])
        if isinstance(contains,str):
            contains=[contains]
        for phrase in contains:
            if phrase.lower() not in result['reply'].lower():
                errors.append('missing text: '+phrase)
        excludes=turn.get('excludes',[])
        if turn.get('not_contains'):
            excludes=[*excludes,turn['not_contains']]
        for phrase in excludes:
            if phrase.lower() in result['reply'].lower():
                errors.append('unexpected text: '+phrase)
        if len(result['reply'].split())>turn.get('max_words',float('inf')):
            errors.append('reply too long')
        results.append(dict(source=case['source'],scenario=case['name'],step=step,text=turn['text'],
                            expected=turn['intent'],intent=result['intent'],seconds=seconds,passed=not errors,errors=errors))

# Exercise actual Flask request handling with an isolated in-memory history.
app=create_app(base,history_path=':memory:')
client=app.test_client()
api=[]
for i,message in enumerate(['my skin is itchy','my left wrist','about two weeks','none',
                            'What is psoriasis?','and treatment?','Explain simply',
                            'Summarize our conversation','reset','banana']*3):
    start=perf_counter()
    response=client.post('/predict',json={'message':message,'conversation_id':f'perf-{i//10}'})
    api.append(dict(message=message,status=response.status_code,seconds=perf_counter()-start))
image_checks=[]
for label in ['atopic_dermatitis','contact_dermatitis','lichen_planus','normal_skin','psoriasis','rosacea','rejected']:
    response=client.post('/predict',data={'conversation_id':'fixture-'+label,'image':(io.BytesIO(b'fixture'),label+'.png')})
    data=response.get_json()
    expected='image_rejected' if label=='rejected' else 'image_classification'
    image_checks.append(dict(label=label,intent=data['intent'],passed=data['intent']==expected,
                             confidence_source=data.get('confidenceSource')))
app.extensions['chat_history'].db.close()
failures=[x for x in results if not x['passed']]
report={'evaluated_at':datetime.now(timezone.utc).isoformat(),'scope':__doc__,
        'model':str(args.model.resolve()),'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
        'scenarios':len(scenarios),'turns':len(results),'passed':len(results)-len(failures),'failures':failures,
        'load_seconds_excluding_module_imports':load_seconds,
        'text_reply_timing':{'samples':len(results),'median_seconds':float(np.median([r['seconds'] for r in results])),
                             'p95_seconds':float(np.percentile([r['seconds'] for r in results],95))},
        'api_in_process_timing':{'samples':len(api),'median_seconds':float(np.median([r['seconds'] for r in api])),
                                 'p95_seconds':float(np.percentile([r['seconds'] for r in api],95)),
                                 'non_200_responses':sum(r['status']!=200 for r in api)},
        'simulated_image_api_checks':image_checks,'results':results,'api_requests':api}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['results','api_requests']},indent=2))
raise SystemExit(1 if failures or not all(x['passed'] for x in image_checks) else 0)
