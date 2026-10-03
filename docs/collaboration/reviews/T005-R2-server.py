"""Review-only latency and HTTP-error injection; no product files are modified."""
import asyncio
from urllib.parse import urlparse, parse_qs
import uvicorn
from fastapi.responses import JSONResponse
from campus_assistant.demo import app

@app.middleware('http')
async def review_scenarios(request, call_next):
    scenario=parse_qs(urlparse(request.headers.get('referer','')).query).get('scenario',[''])[0]
    if scenario=='race' and request.url.path.endswith('/documents/syn-parse-txt-001'):
        await asyncio.sleep(10)
    if scenario=='http500' and request.url.path=='/api/v1/corpus/documents':
        return JSONResponse({'code':'REVIEW_FAILURE','message':'合成验收错误'},status_code=500)
    return await call_next(request)

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=0)
