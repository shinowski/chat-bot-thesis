"""Synthetic transport/timing smoke using the active image weights, not accuracy."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import base64
from pathlib import Path
import sys
from threading import Thread
from time import perf_counter

PROJECT=Path(__file__).resolve().parents[2]
BACKEND=PROJECT.parent/'Image/thesis-backend'
OUT=PROJECT.parent/'reports'/('image-integration-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
sys.path.insert(0,str(BACKEND))
start=perf_counter()
spec=importlib.util.spec_from_file_location('adviser_image_backend',BACKEND/'app.py')
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
startup_seconds=perf_counter()-start
from werkzeug.serving import make_server
from werkzeug.datastructures import FileStorage
from PIL import Image
import numpy as np
server=make_server('127.0.0.1',0,backend.app)
thread=Thread(target=server.serve_forever,daemon=True)
thread.start()
sys.path.insert(0,str(PROJECT))
from model.image_classifier import ImageClassifier
from model.semantic_chatbot import SemanticChatbot
from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.knowledge_base import KnowledgeBase

# get_image_response does not need text inference; use the real integration
# method with real state/knowledge and the actual HTTP image service.
bot=SemanticChatbot.__new__(SemanticChatbot)
bot.conversation=Conversation()
bot.knowledge=KnowledgeBase(PROJECT/'data/knowledge_base.json')
bot.flow=FlowManager()
bot.image_classifier=ImageClassifier(url=f'http://127.0.0.1:{server.server_port}/api/predict')
results=[]
try:
    rng=np.random.default_rng(42)
    arrays=[('skin_color_flat',np.full((224,224,3),[190,135,110],dtype=np.uint8)),
            ('skin_color_noise',np.clip(rng.normal([190,135,110],18,(224,224,3)),0,255).astype(np.uint8)),
            ('blue_flat',np.full((224,224,3),[0,0,255],dtype=np.uint8)),
            ('random_pixels',rng.integers(0,256,(224,224,3),dtype=np.uint8))]
    for repeat in range(3):
        for name,array in arrays:
            data=io.BytesIO();Image.fromarray(array).save(data,format='PNG');data.seek(0)
            started=perf_counter()
            result=bot.get_image_response(FileStorage(stream=data,filename=name+'.png'))
            seconds=perf_counter()-started
            valid=result['intent'] in {'image_rejected','image_classification'}
            if result['intent']=='image_classification':
                valid=valid and 'not a confirmed diagnosis' in result['reply'] and result['confidence']>=.55
            else:
                valid=valid and bot.conversation.get('classification') is None
            results.append(dict(fixture=name,repeat=repeat,intent=result['intent'],
                                reason=result.get('imageResult',{}).get('reason'),seconds=seconds,
                                passed=bool(valid)))
finally:
    server.shutdown();thread.join(timeout=5);server.server_close()

# Exercise the real checkpoint's backward pass and stitched PNG output even
# when the screening gates correctly reject every synthetic pixel fixture.
# This is an explanation-code check, not an accepted disease prediction.
from inference import classifier as loaded
from inference.gradcam import stitch_cams, create_gradcam_overlay
heatmap_started=perf_counter()
heatmap_image=Image.fromarray(arrays[1][1])
tensor=loaded._cam_transform(heatmap_image).unsqueeze(0).to(loaded.DEVICE)
with backend.prediction_lock:
    cam=loaded._gradcam.generate(tensor, class_idx=0, normalize=False)
stitched,covered=stitch_cams([cam],[(0,0,*heatmap_image.size)],heatmap_image.size)
overlay=create_gradcam_overlay(heatmap_image,stitched,covered)
assert np.isfinite(stitched).all()
png=base64.b64decode(loaded._gradcam_to_base64(overlay))
with Image.open(io.BytesIO(png)) as rendered:
    assert rendered.format=='PNG' and rendered.size==heatmap_image.size
heatmap_check={'passed':True,'seconds':perf_counter()-heatmap_started,
               'scope':'Direct Grad-CAM++ backward pass and stitched PNG on synthetic pixels; not an accepted screening result.'}
timings=[r['seconds'] for r in results]
report={'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Active image model through HTTP adapter and chatbot response mapping, using synthetic pixel images. These are not labeled clinical images; no accuracy measured.',
        'model':backend.MODEL_INFO,
        'checkpoint_sha256':backend.MODEL_INFO['sha256'],
        'startup_seconds_including_imports':startup_seconds,
        'samples':len(results),'median_seconds':float(np.median(timings)),
        'p95_seconds':float(np.percentile(timings,95)),
        'timing_scope':'HTTP upload, blur/skin checks, crop-averaged classifier, OOD/normal gates and Grad-CAM++ when accepted, chatbot mapping. No text-model inference or browser rendering.',
        'accepted':sum(r['intent']=='image_classification' for r in results),
        'heatmap_check':heatmap_check,
        'successful':all(r['passed'] for r in results) and heatmap_check['passed'],'results':results}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'real-image-integration-smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['successful'] else 1)
