"""Astra local-only completion probe. --serve exposes search->finish mock for UI review."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'step2_code' / 'backend'
spec = importlib.util.spec_from_file_location('t024_tests', BACKEND / 'tests/test_deepseek_planner.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

if '--serve' in sys.argv:
    import uvicorn
    mock = m.MockChatServer([m.act_call('search_policy', {}), m.act_finish('【模拟】全部办理工作已完成')])
    try:
        uvicorn.run(m._app(m._planner(mock)), host='127.0.0.1', port=18839, log_level='warning')
    finally:
        mock.close()
else:
    rows = []
    for name, script in [
        ('finish_without_tools', [m.act_finish('【模拟】全部办理工作已完成')]),
        ('search_then_finish', [m.act_call('search_policy', {}), m.act_finish('【模拟】全部办理工作已完成')]),
    ]:
        mock = m.MockChatServer(script)
        try:
            with m.TestClient(m._app(m._planner(mock))) as client:
                result = client.post('/api/v1/agent/plan/run', json=m._defer_body()).json()
                rows.append(dict(case=name, status=result['status'], message=result['message'],
                                 calls=result['tool_calls_used'], draft=result['results']['draft'],
                                 http_attempts=result['planner_http_attempts']))
        finally:
            mock.close()
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    sys.exit(1 if any(r['status'] == 'completed' and r['draft'] is None for r in rows) else 0)
