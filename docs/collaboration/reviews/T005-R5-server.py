"""Synthetic response fixtures for independent browser acceptance."""
import asyncio
from collections import Counter
from urllib.parse import urlparse, parse_qs
import uvicorn
from fastapi.responses import JSONResponse, Response
from campus_assistant.demo import app

counts = Counter()

@app.middleware('http')
async def scenarios(request, call_next):
    scenario = parse_qs(urlparse(request.headers.get('referer', '')).query).get('scenario', [''])[0]
    path = request.url.path
    key = (scenario, path)
    counts[key] += 1
    n = counts[key]
    kind = 'status' if path.endswith('/corpus/status') else 'list' if path.endswith('/corpus/documents') else 'detail' if '/documents/' in path else ''
    if scenario == 'race' and path.endswith('/documents/syn-parse-txt-001'):
        await asyncio.sleep(10)
    if scenario == 'status-race' and kind == 'status' and n <= 2:
        if n == 2:
            await asyncio.sleep(10)
        return JSONResponse({'code': 'REVIEW_FAILURE'}, status_code=500)
    if scenario in (kind + '-once', kind + '-json') and n == 1:
        if scenario.endswith('-json'):
            return Response('{broken', media_type='application/json')
        return JSONResponse({'code': 'REVIEW_FAILURE'}, status_code=500)
    if scenario == 'partial' and kind == 'status':
        return JSONResponse({'status':'partial','document_count':3,'parsed_count':2,'errors':[{'document_id':'synthetic-bad','message':'合成解析失败，必须保留'}],'request_id':'review'})
    if scenario == 'partial' and kind == 'list':
        await asyncio.sleep(3)
    return await call_next(request)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=0)
