"""Supplement R4: malformed DOCX ordering/CLI and both ID fields."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from fastapi.testclient import TestClient
from campus_assistant.main import create_app
from campus_assistant.corpus.models import Document
from pydantic import ValidationError

evidence = json.loads(Path(__file__).with_name('T008-R4-audit-output.json').read_text(encoding='utf-8-sig'))
root = Path(evidence['wheel_non_source']['result']['module']).parents[2]
data = json.loads((root / 'bad-manifest.json').read_text(encoding='utf-8'))
for order in [(0, 1), (1, 0), (1,)]:
    manifest = root / ('order-' + ''.join(map(str, order)) + '.json')
    manifest.write_text(json.dumps({'schema_version':'1.0','documents':[data['documents'][i] for i in order]}), encoding='utf-8')
    p = subprocess.run([sys.executable,'-m','campus_assistant.corpus.parse','--manifest',str(manifest),'--corpus-root',str(root)],capture_output=True)
    result = json.loads(p.stdout.decode('utf-8'))
    assert p.returncode == 1 and b'Traceback' not in p.stderr
    assert [d['document_id'] for d in result['documents']] == (['good'] if 0 in order else [])
    assert result['errors'][0]['code'] == 'DOCUMENT_PARSE_ERROR'
    assert result['errors'][0]['document_id'] == 'bad'
    with TestClient(create_app(manifest,root)) as c:
        assert c.get('/api/v1/search/status').json()['status'] == ('partial' if 0 in order else 'failed')
        assert c.post('/api/v1/search',json={'query':'缓考'}).status_code == (200 if 0 in order else 503)
        assert c.get('/preview').status_code == 200
        assert c.get('/api/v1/health/live').status_code == 200
        assert c.get('/api/v1/health/ready').status_code == 503
for field in ['document_id','policy_group_id']:
    for val, valid in [('a',True),('a'*64,True),('a'*65,False),('good\n',False),('good\r\n',False),('go\nod',False),(' good ',False)]:
        item = copy.deepcopy(data['documents'][0]);item[field]=val
        try:
            Document.model_validate(item)
            assert valid, (field,repr(val))
        except ValidationError:
            assert not valid, (field,repr(val))
print('PASS: 3 malformed DOCX order/CLI/API cases, 14 strict ID boundary cases')
