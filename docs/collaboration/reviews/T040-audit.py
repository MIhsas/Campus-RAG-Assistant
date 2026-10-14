"""Astra A-stage material audit. No provider, network, or model calls."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'step2_code/backend/src'))
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.retrieval.filters import compute_allowed_document_ids
from campus_assistant.qa.deepseek import build_messages

def load(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

SUB = Path('docs/collaboration/submissions/T040')
raw = load(SUB / 'dry-run.json')
fresh = load('docs/collaboration/reviews/T040-Astra-dry-run/dry-run.json')
frozen = {q['question_id']: q for q in load('data/evaluations/sicau-rag-pilot-eval-v2/questions.json')['questions']}
corpus = ROOT / 'data/corpora/sicau-rag-pilot-v1.2'
parsed = parse_manifest(corpus / 'manifest.json', corpus)
documents = parsed['documents']
blocks = {(d['document_id'], b['block_id']): b for d in documents for b in d['blocks']}
hash_checks = 0
def walk(value):
    global hash_checks
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            assert sha(value['path']) == value['sha256'], value['path']
            hash_checks += 1
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)
walk(load(SUB / 'changed-files.json'))
snap = load('docs/collaboration/handoffs/T039-R1-20261009-盘点.json')
for item in snap['readonly_snapshot_files'] + snap['rev1_submission_archive']:
    assert sha(item['path']) == item['sha256'], item['path']
sub = load(SUB / 'submission.json')
assert sub['stage'] == 'A_ready_for_review' and sub['external_model_calls'] == 0 and not sub['live_verified']
assert all((ROOT / SUB / name).is_file() for name in sub['deliverables'])
for name in ('dry-run.json', 'input-hashes.json', 'generation-review-sheet.md', 'live-smoke-plan.md'):
    assert (ROOT / SUB / name).read_bytes() == (ROOT / 'step2_code/backend/.cache/real-qa-smoke/T040-A' / name).read_bytes()

assert raw['external_requests'] == fresh['external_requests'] == 0
assert not fresh['app_identity']['generator_configured']
evidence_checks = 0
for qid in ('q08', 'q10', 'u03', 'u04'):
    a, b, q = raw['questions'][qid], fresh['questions'][qid], frozen[qid]
    for key in ('frozen_query', 'frozen_conditions', 'request_body', 'future_messages', 'checks', 'gold_coverage_offline', 'plan'):
        assert a[key] == b[key], (qid, key)
    assert a['frozen_query'] == q['query'] and a['frozen_conditions'] == q['conditions']
    for key in ('status', 'evidence_state', 'evidence', 'budget', 'filter_summary', 'source_selection'):
        assert a['api_result'][key] == b['api_result'][key], (qid, key)
    result = compute_allowed_document_ids(documents, q['conditions'])
    allowed = result['allowed_document_ids']
    evidence = a['api_result']['evidence']
    assert len(evidence) == 5
    for ev in evidence:
        assert allowed is None or ev['document_id'] in allowed, (qid, ev['evidence_id'])
        blk = blocks[(ev['document_id'], ev['block_id'])]
        assert blk['text'][ev['char_start']:ev['char_end']] == ev['text']
        assert not ev['is_synthetic']
        evidence_checks += 1
    assert a['future_messages'] == build_messages(query=q['query'], evidence=evidence, filters=q['conditions'])
    content = ''.join(m['content'] for m in a['future_messages'])
    assert 'F:\\Collage Paper' not in content and 'F:/Collage Paper' not in content
assert raw['questions']['q08']['gold_coverage_offline']['gap_fact_ids'] == ['f1']
assert raw['questions']['q10']['gold_coverage_offline']['gap_fact_ids'] == []
assert raw['questions']['u03']['gold_coverage_offline']['gap_fact_ids'] == []
result = {
    'status': 'ok', 'material_hash_checks': hash_checks, 'readonly_files_unchanged': 23,
    'archive_files_unchanged': 7, 'deliverables': len(sub['deliverables']),
    'fresh_cases_equal': 4, 'admitted_verbatim_evidence_checks': evidence_checks,
    'messages_equal_to_current_builder': 4, 'new_external_calls': 0,
    'q08_gold_gap_preserved': True,
    'interpretation': 'Nonempty evidence is not proof of answer support; q08 insufficient response can be appropriate.',
}
(ROOT / 'docs/collaboration/reviews/T040-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
