// Dedicated CDP browser on port 9372; isolated fixture server on port 5010.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const out=fileURLToPath(new URL('../../../reports/adviser-evaluation-2026-10-22/',import.meta.url));
await mkdir(out,{recursive:true});
const target=await fetch('http://127.0.0.1:9372/json/new?http://127.0.0.1:5010/',{method:'PUT'}).then(r=>r.json());
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let id=0;const pending=new Map(),exceptions=[],checks=[],timings=[];
socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.method==='Runtime.exceptionThrown') exceptions.push(message.params);
  if(pending.has(message.id)){
    const {resolve,reject,timer}=pending.get(message.id);pending.delete(message.id);clearTimeout(timer);
    message.error?reject(new Error(JSON.stringify(message.error))):resolve(message.result);
  }
});
function command(method,params={}){return new Promise((resolve,reject)=>{
  const next=++id;const timer=setTimeout(()=>{pending.delete(next);reject(new Error(method+' timed out'));},30000);
  pending.set(next,{resolve,reject,timer});socket.send(JSON.stringify({id:next,method,params}));
});}
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function wait(expression){const end=Date.now()+30000;while(Date.now()<end){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,50));}throw new Error('Timed out: '+expression);}
const ready="!!document.querySelector('textarea') && !document.querySelector('textarea').disabled && document.querySelector('.composer').getAttribute('aria-busy') !== 'true'";
async function send(text){
  await wait(ready);const count=await evaluate("document.querySelectorAll('.row.bot').length");
  await evaluate("document.querySelector('textarea').focus()");await command('Input.insertText',{text});
  await wait("!document.querySelector('.send-btn').disabled");const start=performance.now();
  await evaluate("document.querySelector('.send-btn').click()");
  await wait(`document.querySelectorAll('.row.bot').length === ${count+1} && ${ready}`);
  timings.push({message:text,milliseconds:performance.now()-start});
  return evaluate("fetch('/api/conversations/'+localStorage.getItem('flamma.activeChat')).then(r=>r.json()).then(x=>x.messages.at(-1))");
}
async function screenshot(name){const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await writeFile(out+name+'.png',Buffer.from(r.data,'base64'));}
let failure=null;
try{
  await command('Page.enable');await command('Runtime.enable');await wait(ready);
  for(const [width,height] of [[360,800],[390,844],[768,1024],[1366,900]]){
    await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await command('Page.navigate',{url:'http://127.0.0.1:5010/'});await wait(ready);
    const layout=await evaluate(`(()=>{const e=document.querySelector('textarea'),s=document.querySelector('.send-btn');const r=e.getBoundingClientRect(),b=s.getBoundingClientRect();return {width:innerWidth,scroll:document.documentElement.scrollWidth,textareaVisible:r.width>0&&r.left>=0&&r.right<=innerWidth+1,sendVisible:b.width>0&&b.right<=innerWidth+1,accessibleName:!!e.getAttribute('aria-label')||!!e.getAttribute('placeholder')};})()`);
    assert.ok(layout.scroll<=width+1,'Horizontal overflow at '+width);assert.ok(layout.textareaVisible&&layout.sendVisible&&layout.accessibleName);
    if(width<600){await evaluate("document.querySelector('.menu-btn').click()");await wait("document.querySelector('.sidebar').classList.contains('open')");await evaluate("document.querySelector('.menu-btn').click()");}
    await screenshot('viewport-'+width);checks.push({check:'responsive layout and composer',width,passed:true,...layout});
  }
  await evaluate("document.querySelector('.new-chat').click()");await wait("document.querySelectorAll('.row.user').length===0 && "+ready);
  assert.equal((await send('my rash is itchy on my arm for two weeks')).intent,'location');
  await send('I used a cream for three days');
  assert.match((await send('summarize our conversation')).text,/two weeks/);
  await send('What is psoriasis?');assert.match((await send('and treatment?')).text,/Psoriasis/);
  await command('Page.reload');await wait(ready);assert.match((await send('and contagious?')).text,/not contagious/);
  assert.equal((await send('reset')).intent,'reset');assert.match((await send('summarize our conversation')).text,/not provided/);
  checks.push({check:'multi-turn, treatment context, persistence, reset',passed:true});
  const fallback=await send('banana');assert.ok(['clarification','unknown'].includes(fallback.intent));
  const emergency=await send('I cannot breathe');assert.equal(emergency.intent,'emergency');
  checks.push({check:'fallback and emergency routing',passed:true});
  for(const label of ['atopic_dermatitis','contact_dermatitis','lichen_planus','psoriasis','rosacea','normal_skin','rejected']){
    await evaluate("document.querySelector('.new-chat').click()");await wait("document.querySelectorAll('.row.user').length===0 && "+ready);
    const file=out+label+'.png';await writeFile(file,Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64'));
    const doc=await command('DOM.getDocument');const input=await command('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'input[type=file]'});
    await command('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[file]});await wait("!document.querySelector('.send-btn').disabled");
    await evaluate("document.querySelector('.send-btn').click()");await wait("document.querySelectorAll('.row.bot').length===1 && "+ready);
    const result=await evaluate("fetch('/api/conversations/'+localStorage.getItem('flamma.activeChat')).then(r=>r.json()).then(x=>x.messages.at(-1))");
    assert.equal(result.intent,label==='rejected'?'image_rejected':'image_classification');
    if(label!=='rejected'){assert.equal(result.treatmentInfo.condition_key,label);assert.match(result.text,/not a confirmed diagnosis/);}
    else assert.equal(result.confidence,null);
    checks.push({check:'real browser upload with simulated image result',label,passed:true});
  }
  assert.equal(exceptions.length,0);checks.push({check:'uncaught browser errors',count:exceptions.length,passed:true});
}catch(error){failure=String(error.stack||error);await screenshot('browser-failure').catch(()=>{});}
finally{
  const report={scope:'Chromium desktop/mobile emulation with real text model and simulated image responses; not human usability or image recognition.',evaluated_at:new Date().toISOString(),checks,reply_timings:timings,exceptions,failure,successful:!failure};
  await writeFile(out+'browser-checks.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));await command('Browser.close').catch(()=>{});socket.close();
}
if(failure)process.exitCode=1;
