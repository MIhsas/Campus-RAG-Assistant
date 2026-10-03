import os, json, time
from pathlib import Path
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from campus_assistant.evaluation.run import _run_eval
root=Path.cwd()
out={}
for mode in ['bm25','dense','hybrid']:
    start=time.perf_counter()
    r=_run_eval(root/'examples/parse-corpus/manifest.json', root/'examples/parse-corpus', root/'examples/evaluation/questions.json',5,mode,str(root/'models/bge-small-zh-v1.5'))
    (root/f'.cache/astra-t010-{mode}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    out[mode]={'valid':r['valid'],'summary':r['summary'],'errors':r['errors'],'seconds':round(time.perf_counter()-start,3)}
    print(json.dumps({mode:out[mode]},ensure_ascii=True),flush=True)
from campus_assistant.main import create_app
from fastapi.testclient import TestClient
start=time.perf_counter()
app=create_app(manifest_path=root/'examples/parse-corpus/manifest.json',corpus_root=root/'examples/parse-corpus',embedding_model_path=str(root/'models/bge-small-zh-v1.5'))
with TestClient(app) as client:
    print('STATUS',json.dumps(client.get('/api/v1/search/status').json(),ensure_ascii=True),flush=True)
    for mode in ['bm25','dense','hybrid']:
        t=time.perf_counter()
        r=client.post('/api/v1/search',json={'query':'缓考申请','mode':mode,'top_k':5})
        print('API',mode,r.status_code,round(time.perf_counter()-t,3),json.dumps(r.json(),ensure_ascii=True),flush=True)
(root/'.cache/astra-t010-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
