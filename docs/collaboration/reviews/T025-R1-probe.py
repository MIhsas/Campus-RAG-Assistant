"""Offline preflight check and loopback failure-audit probe; no external requests."""
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
backend = root / 'step2_code/backend'
spec = importlib.util.spec_from_file_location('t025_tests', backend / 'tests/test_live_smoke_planner.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

for url in ['http://127.0.0.1.example.invalid', 'http://localhost@example.invalid']:
    rows, *_ = m.smoke.preflight('mock', url)
    print(json.dumps({'url': url, 'preflight_accepted': all(r['pass'] is not False for r in rows)}))

mock = m.helpers.MockChatServer([{'content': '{}', 'finish_reason': 'length'}])
try:
    with m.helpers.TestClient(m.helpers._app(m.helpers._planner(mock))) as c:
        run = c.post('/api/v1/agent/plan/run', json=m.helpers._defer_body()).json()
        print(json.dumps({'status': run['status'], 'attempts': run['planner_http_attempts'],
                          'failed_audit': [e.get('audit') for e in run['events'] if e['kind'] == 'plan_error'],
                          'mock_sent_fields': ['id', 'model', 'usage', 'finish_reason=length']}))
finally:
    mock.close()
