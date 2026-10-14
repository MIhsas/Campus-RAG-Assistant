"""Astra independent read-only T038 audit; run from repository root."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'step2_code/backend/src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.retrieval.filters import compute_allowed_document_ids
from campus_assistant.main import create_app
from fastapi.testclient import TestClient

def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

old = Path('data/corpora/sicau-rag-pilot-v1.1')
new = Path('data/corpora/sicau-rag-pilot-v1.2')
historical = {
    str(old / 'manifest.json'): '34e182f18178c8a8dc3f3bbfcb151150272f0c86579236191ed1e754298b1108',
    'data/evaluations/sicau-rag-pilot-eval-v1/questions.json': '5fde70a332744b642e48014abc82902009abc1a106a84e6241b3c460e4faed5c',
    'data/procedures/sicau-transfer-2026-v1/procedures.json': '78f1c1d9f839c41da2fc5b13fdb67014826bdde93d57a5f872c33a79f47b7cfa',
    'data/evaluations/sicau-rag-source-selection-v1/experiment.json': '57b22f93bd1420faf276915c6425b3f8e8f9c978058935f8a1c69de39bd5c618',
    'data/evaluations/sicau-rag-overlap-v1/experiment.json': 'cef9f162f1eb164adbb65b1c9acc1634ee24e985edcc197fae09a6ac07dd2d95',
    'data/reviews/T036-user-review-20261008/human-review-record.json': '2e1af1493846efd76f2ec593ac248c31df5dc725e77a1abe845e980e3efc5791',
}
for path, expected in historical.items():
    assert sha(path) == expected, path
assert sha(new / 'manifest.json') == 'b05c37557675f02c045e01e9fd776c539954c43172d5e0b07d0704da4e352b4a'
m1, m2 = load(old / 'manifest.json'), load(new / 'manifest.json')
assert set(m1) == set(m2)
assert {k: v for k, v in m1.items() if k != 'documents'} == {k: v for k, v in m2.items() if k != 'documents'}
docs1 = {d['document_id']: d for d in m1['documents']}
docs2 = {d['document_id']: d for d in m2['documents']}
assert set(docs1) == set(docs2) and len(docs2) == 20
changes = []
for doc_id, d1 in docs1.items():
    d2 = docs2[doc_id]
    assert set(d1) == set(d2)
    assert (ROOT / old / d1['local_path']).read_bytes() == (ROOT / new / d2['local_path']).read_bytes()
    assert sha(new / d2['local_path']) == d2['sha256'] == d1['sha256']
    for key in d1:
        if d1[key] != d2[key]:
            changes.append({'document_id': doc_id, 'field': key, 'old': d1[key], 'new': d2[key]})
assert len(changes) == 2
assert {c['field'] for c in changes} == {'published_at', 'effective_from'}
assert all(c['document_id'].startswith('bed3ac') and c['old'] is None and c['new'] == '2019-11-07' for c in changes)
parsed1 = parse_manifest(ROOT / old / 'manifest.json', ROOT / old)
parsed2 = parse_manifest(ROOT / new / 'manifest.json', ROOT / new)
for parsed in (parsed1, parsed2):
    assert parsed['valid'] and not parsed['errors'] and len(parsed['documents']) == 20
blocks = lambda parsed: {(d['document_id'], b['block_id']): b for d in parsed['documents'] for b in d['blocks']}
b1, b2 = blocks(parsed1), blocks(parsed2)
assert b1 == b2
bed = next(k for k in docs2 if k.startswith('bed3ac'))
db = next(k for k in docs2 if k.startswith('db05e0'))
guide = next(k for k in docs2 if k.startswith('83eb'))
date_refs = []
for prefix, expected in [('f3cdb912', '2019年11月7日'), ('a3536032', '2019年11月7日印'), ('c641f172', '本办法自发文之日起执行')]:
    block = next(v for (d, k), v in b2.items() if d == bed and k.startswith(prefix))
    assert expected in block['text']
    start = block['text'].index(expected)
    date_refs.append({'block_id': block['block_id'], 'char_start': start, 'char_end': start+len(expected), 'quote': expected, 'locator': block.get('locator')})
f = {'as_of_date': '2026-10-03'}
s1 = compute_allowed_document_ids(parsed1['documents'], f)
s2 = compute_allowed_document_ids(parsed2['documents'], f)
assert (s1['allowed_count'], s2['allowed_count']) == (4, 5)
assert s2['allowed_document_ids'] - s1['allowed_document_ids'] == {bed}
assert db not in s2['allowed_document_ids']

class CountingProvider:
    def __init__(self):
        self.calls = 0
    def generate(self, **kwargs):
        self.calls += 1
        raise AssertionError('This audit must not invoke generation')

provider = CountingProvider()
app = create_app(manifest_path=ROOT / new / 'manifest.json', corpus_root=ROOT / new, answer_provider=provider)
with TestClient(app) as client:
    query = {'query': '学籍基本信息有误去哪里办理', 'mode': 'bm25', 'top_k': 5, 'filters': {'student_type': '本科'}}
    strict_before = client.post('/api/v1/search', json=query)
    ask_before = client.post('/api/v1/ask', json=query)
    cand = client.post('/api/v1/search/candidates', json={**query, 'uncertainty_dimensions': ['student_type']})
    assert strict_before.status_code == ask_before.status_code == cand.status_code == 200
    cd = cand.json()
    assert cd['candidate_summary']['candidate_document_count'] == 2
    assert guide in {h['chunk']['document_id'] for h in cd['hits']}
    assert all(h['chunk']['document_id'] != guide for h in strict_before.json()['hits'])
    assert all(e['document_id'] != guide for e in ask_before.json()['evidence'])
    strict_after = client.post('/api/v1/search', json=query).json()
    ask_after = client.post('/api/v1/ask', json=query).json()
    assert strict_before.json()['hits'] == strict_after['hits']
    assert ask_before.json()['evidence'] == ask_after['evidence']
    assert provider.calls == 0
    strict_docs = {h['chunk']['document_id'] for h in strict_after['hits']}
    cand_docs = {h['chunk']['document_id'] for h in cd['hits']}
    assert strict_docs.isdisjoint(cand_docs)
    for hit in cd['hits']:
        chunk = hit['chunk']
        block = b2[(chunk['document_id'], chunk['block_id'])]
        assert block['text'][chunk['char_start']:chunk['char_end']] == chunk['text']

out = {'manifest_changes': changes, 'original_files_equal': 20, 'blocks_equal': len(b2),
       'date_citations': date_refs, 'date_admission_old_new': [4, 5],
       'historical_hashes': historical, 'candidate_document_count': 2,
       'strict_hits_count': len(strict_after['hits']), 'strict_evidence_count': len(ask_after['evidence']),
       'strict_before_after_unchanged': True, 'generation_calls': provider.calls,
       'candidate_source_spans_verified': len(cd['hits']),
       'not_verified': ['current policy validity', 'live generated quality', 'human withdrawal of open opinions']}
(ROOT / 'docs/collaboration/reviews/T038-audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('T038 AUDIT OK: 20 original files,', len(b2), 'blocks; exactly 2 date fields changed; 6 historical hashes intact; admission 4 -> 5; candidate isolation; provider calls 0')
