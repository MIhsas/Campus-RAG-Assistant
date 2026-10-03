"""Independent delayed response fixture; no product changes."""
import asyncio
import uvicorn
from campus_assistant.demo import app

@app.middleware('http')
async def delay_search(request, call_next):
    if request.method == 'POST' and request.url.path == '/api/v1/search':
        await asyncio.sleep(12)
    return await call_next(request)

if __name__ == '__main__':
    uvicorn.run(app,host='127.0.0.1',port=0)
