"""Astra independent saved-ranking rescore and default compatibility audit."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
backend = root / 'step2_code/backend'
sys.path.insert(0, str(backend / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.corpus.chunk import chunk_documents
from campus_assistant.retrieval.bm25 import BM25Index
from campus_assistant.retrieval.filters import compute_allowed_document_ids

data = root / 'data/evaluations/sicau-rag-overlap-v1'
experiment = json.loads((data/'experiment.json').read_text(encoding='utf-8'))
frozen = json.loads((data/'frozen-config.json').read_text(encoding='utf-8'))
qpath = root/'data/evaluations/sicau-rag-pilot-eval-v1/questions.json'
questions = json.loads(qpath.read_text(encoding='utf-8'))['questions']
by_q = {q['question_id']: q for q in questions}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(qpath) == frozen['questions_sha256']
pack = root/'data/corpora/sicau-rag-pilot-v1.1'
assert sha(pack/'manifest.json') == frozen['corpus_manifest_sha256']
for f, expected in frozen['implementation_sha256'].items():
    assert sha(backend/f) == expected, f
for f, expected in frozen['embedding_model']['identity_files_sha256'].items():
    assert sha(backend/'models/bge-small-zh-v1.5'/f) == expected, f

stored = {m: json.loads((root/f'data/evaluations/sicau-rag-pilot-eval-v1/results/{m}.json').read_text(encoding='utf-8')) for m in ('bm25','dense','hybrid')}
assert len(experiment['rows']) == 24
scored = {}
unchanged = 0
for row in experiment['rows']:
    q = by_q[row['question_id']]
    assert row['conditions'] == ({k:v for k,v in (q.get('conditions') or {}).items() if v is not None} or None)
    for mode, branches in row['modes'].items():
        for branch, record in branches.items():
            assert record is not None
            hits = [{'score': 1, 'chunk': dict(zip(('document_id','block_id','char_start','char_end'), k))} for k in record['hit_keys']]
            score = evaluate_question(q, hits, top_k=5)
            for field in ('recall','hit','mrr','covered_evidence_ids'):
                assert score[field] == record[field], (q['question_id'], mode, branch, field)
            scored.setdefault(f'{mode}/{branch}', []).append(score)
            if branch == 'baseline_stored':
                old = next(x for x in stored[mode]['per_question'] if x['question_id']==q['question_id'])
                seq = [[h[f] for f in ('document_id','block_id','char_start','char_end')] for h in old['hit_summary']]
                assert seq == record['hit_keys']
        if all(branches['baseline_stored'][f]==branches['candidate'][f] for f in ('recall','hit','mrr')):
            unchanged += 1
for key, rows in scored.items():
    assert compute_summary(rows) == experiment['aggregates'][key], key
assert unchanged == experiment['non_improvements_count'] == 65

parsed = parse_manifest(pack/'manifest.json', pack)
assert parsed['valid']
documents = parsed['documents']
blocks = {(d['document_id'],b['block_id']): b for d in documents for b in d['blocks']}
base = chunk_documents(documents)
candidate = chunk_documents(documents, overlap_chars=100)
old_source = subprocess.check_output(['git','show','HEAD:step2_code/backend/src/campus_assistant/corpus/chunk.py'],cwd=root, text=True,encoding='utf-8')
assert 'STRATEGY_OVERLAP' not in old_source
namespace = {'__name__': 'astra_old_chunk'}
exec(compile(old_source,'git-head-chunk.py','exec'),namespace)
assert base == namespace['chunk_documents'](documents)
for chunk in candidate:
    assert chunk['text']==blocks[(chunk['document_id'],chunk['block_id'])]['text'][chunk['char_start']:chunk['char_end']]
index=BM25Index(base)
for q in questions:
    allowed=compute_allowed_document_ids(documents,q.get('conditions') or None)['allowed_document_ids']
    hits=index.search(q['query'],top_k=5,allowed_document_ids=allowed)
    got=[[h['chunk'][f] for f in ('document_id','block_id','char_start','char_end')] for h in hits]
    row=next(x for x in experiment['rows'] if x['question_id']==q['question_id'])
    assert got==row['modes']['bm25']['baseline_stored']['hit_keys']
output={'saved_branches_rescored':144,'historical_rankings_matched':72,'default_chunks_equal_git_head':len(base),'candidate_verbatim_chunks':len(candidate),'bm25_baseline_rerun_matched':24,'unchanged_rows':unchanged,'metrics':experiment['aggregates']}
(root/'docs/collaboration/reviews/T034-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('AUDIT OK: 144 branches, 72 historical rankings, 24 BM25 reruns; default chunks identical; candidate spans verbatim')
