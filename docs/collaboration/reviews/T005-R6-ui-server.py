"""Review-only synthetic mixed metadata and unconfigured UI fixtures."""
from urllib.parse import urlparse, parse_qs
import uvicorn
from fastapi.responses import JSONResponse
from campus_assistant.demo import app

# Synthetic metadata toggles exercise UI branches; no real school documents.
app.state.corpus_data[1]['metadata']['is_synthetic'] = False
app.state.corpus_data[0]['warnings'] = ['合成验收提示：正文标签必须按文本显示']
app.state.corpus_data[0]['blocks'][0]['text'] = '<img src=x onerror="alert(1)"> 合成标签正文'

@app.middleware('http')
async def scenarios(request, call_next):
    scenario = parse_qs(urlparse(request.headers.get('referer','')).query).get('scenario',[''])[0]
    if scenario == 'unconfigured' and request.url.path.startswith('/api/v1/corpus/'):
        if request.url.path.endswith('/status'):
            return JSONResponse({'status':'unconfigured','document_count':0,'parsed_count':0,'errors':[],'request_id':'review'})
        return JSONResponse({'code':'CORPUS_NOT_CONFIGURED','message':'语料未配置','request_id':'review'},status_code=503)
    return await call_next(request)

if __name__ == '__main__':
    uvicorn.run(app,host='127.0.0.1',port=0)
