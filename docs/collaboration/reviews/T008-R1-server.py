"""Review-only HTTP/JSON failure injection for search UI."""
from urllib.parse import urlparse, parse_qs
from fastapi.responses import JSONResponse, Response
from campus_assistant.demo import app
import uvicorn

seen = set()

@app.middleware('http')
async def fixture(request, call_next):
    if request.method == 'POST' and request.url.path == '/api/v1/search':
        scenario = parse_qs(urlparse(request.headers.get('referer','')).query).get('scenario',[''])[0]
        if scenario in ('once','json') and scenario not in seen:
            seen.add(scenario)
            if scenario == 'json':
                return Response('{invalid',media_type='application/json')
            return JSONResponse({'message':'合成失败'},status_code=500)
    return await call_next(request)

if __name__ == '__main__':
    uvicorn.run(app,host='127.0.0.1',port=0)
