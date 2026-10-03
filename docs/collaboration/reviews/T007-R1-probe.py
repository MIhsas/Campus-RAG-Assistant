"""Independent synthetic retrieval checks, no product changes."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from campus_assistant.retrieval.bm25 import BM25Index

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[3]
def chunk(cid, text):
    return {'chunk_id':cid,'text':text,'document_id':'d/a','block_id':'b#1','metadata':{'scope':{'campus':[]}}}
source = [chunk('z','apple'),chunk('a','apple'),chunk('empty','!!!')]
idx = BM25Index(source)
hits = idx.search('apple apple')
assert [h['chunk']['chunk_id'] for h in hits] == ['a','z']
assert all(math.isclose(h['score'],math.log(1.2)) for h in hits)
assert all(math.isclose(sum(t['contribution'] for t in h['matched_terms']),h['score']) for h in hits)
assert hits[0]['preview_url'] == '/preview#d%2Fa/b%231'
hits[0]['chunk']['metadata']['scope']['campus'].append('changed')
source[0]['text'] = 'banana'
assert idx.search('apple')[0]['chunk']['metadata']['scope']['campus'] == []
assert len(idx.search('apple')) == 2
print('arithmetic_tie_dedup_empty_exclusion_url_isolation=PASS')

cache = root/'step2_code/backend/.cache'
cache.mkdir(exist_ok=True)
folder = Path(tempfile.mkdtemp(prefix='astra-t007r1-',dir=cache))
base = json.loads((root/'step2_code/backend/examples/parse-corpus/manifest.json').read_text(encoding='utf-8'))
record = copy.deepcopy(base['documents'][0])
record['local_path'] = 'probe.txt'
record['document_id'] = 'synthetic-review'
for text in ['apple\n\n!!!','!!!']:
    (folder/'probe.txt').write_text(text,encoding='utf-8')
    record['sha256'] = hashlib.sha256((folder/'probe.txt').read_bytes()).hexdigest()
    (folder/'manifest.json').write_text(json.dumps({'schema_version':'1.0','documents':[record]},ensure_ascii=False),encoding='utf-8')
    p = subprocess.run([sys.executable,'-m','campus_assistant.retrieval.search','--manifest',str(folder/'manifest.json'),'--corpus-root',str(folder),'--query','apple'],capture_output=True)
    data = json.loads(p.stdout)
    print(json.dumps({'fixture':text,'exit':p.returncode,'chunks':data['chunk_count'],'indexed':data['indexed_chunk_count'],'hits':len(data['hits']),'expected_indexed':1 if 'apple' in text else 0}))
