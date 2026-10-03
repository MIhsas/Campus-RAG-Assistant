"""Review-only scenarios; never modify the product or previous evidence."""
import asyncio
from urllib.parse import urlparse, parse_qs
import uvicorn
from fastapi.responses import JSONResponse
from campus_assistant.demo import app

seen = set()

@app.middleware('http')
async def scenarios(request, call_next):
    scenario = parse_qs(urlparse(request.headers.get('referer', '')).query).get('scenario', [''])[0]
    path = request.url.path
    if scenario == 'race' and path.endswith('/documents/syn-parse-txt-001'):
        await asyncio.sleep(10)
    fail = (scenario == 'status500' and path.endswith('/corpus/status')) or (scenario == 'detail500' and '/documents/' in path)
    if scenario == 'list-once' and path.endswith('/corpus/documents') and scenario not in seen:
        seen.add(scenario)
        fail = True
    if fail:
        return JSONResponse({'code': 'REVIEW_FAILURE', 'message': '合成验收错误'}, status_code=500)
    return await call_next(request)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=0)
