"""Astra revision 2 check: stored evidence only; no index/model/network calls."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'step2_code/backend/src'))
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary

def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

snap = load('docs/collaboration/handoffs/T039-R1-20261009-盘点.json')
for item in snap['readonly_snapshot_files'] + snap['rev1_submission_archive']:
    assert sha(item['path']) == item['sha256'], item['path']
partial_changes = [i['path'] for i in snap['partial_work_files'] if sha(i['path']) != i['sha256']]
assert set(partial_changes) == {
    'docs/collaboration/submissions/T039/verification.md',
    'docs/delivery/human-review-pending.md',
}, partial_changes
sub_dir = Path('docs/collaboration/submissions/T039')
sub = load(sub_dir / 'submission.json')
assert (sub['submission_revision'], sub['responds_to'], sub['status']) == (2, 'T039-R1', 'ready_for_review')
for name in sub['deliverables']:
    assert (ROOT / sub_dir / name).is_file(), name

hash_count = 0
def check_hashes(value):
    global hash_count
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            assert sha(value['path']) == value['sha256'], value['path']
            hash_count += 1
        for nested in value.values():
            check_hashes(nested)
    elif isinstance(value, list):
        for nested in value:
            check_hashes(nested)
check_hashes(load(sub_dir / 'changed-files.json'))
assert hash_count == 14, hash_count
assert sha(sub_dir / 'T039-audit-rev1-failed-preserved.json') == '41f043a2e069da806662d5f6ee2d7972611345ac2aafcc77cddb3ba97b4f6f4a'
audit = load('docs/collaboration/reviews/T039-audit.json')
assert audit['status'] == 'ok' and audit['submitted_diff_mismatches'] == []

v1 = Path('data/evaluations/sicau-rag-pilot-eval-v1')
v2 = Path('data/evaluations/sicau-rag-pilot-eval-v2')
old = {q['question_id']: q for q in load(v1 / 'questions.json')['questions']}
new = {q['question_id']: q for q in load(v2 / 'questions.json')['questions']}
actual = {qid: sorted(k for k in set(old[qid]) | set(q) if old[qid].get(k) != q.get(k)) for qid, q in new.items()}
submitted_diff = {r['question_id']: r['changed_fields'] for r in load(v2 / 'field-diff.json')['question_diffs']}
assert actual == submitted_diff
assert len([v for v in actual.values() if v]) == 6
agg = load(v2 / 'aggregate.json')
score_checks = common_checks = group_checks = 0
for mode in ('bm25', 'dense', 'hybrid'):
    run = load(v2 / 'results' / (mode + '.json'))
    rows = {r['question_id']: r for r in run['per_question']}
    old_rows = {r['question_id']: r for r in load(v1 / 'results' / (mode + '.json'))['per_question']}
    scored = []
    for qid, row in rows.items():
        hits = [{'score': h['score'], 'chunk': h, 'preview_url': h.get('preview_url', '')} for h in row['hit_summary']]
        fresh = evaluate_question(new[qid], hits, top_k=5)
        assert all(fresh[k] == row[k] for k in fresh), (mode, qid)
        scored.append(fresh)
        score_checks += 1
        if old[qid]['answerable']:
            assert row['hit_summary'] == old_rows[qid]['hit_summary']
            assert all(row[k] == old_rows[qid][k] for k in ('recall', 'hit', 'mrr'))
            common_checks += 1
    assert compute_summary(scored) == run['summary'] == agg['aggregates_n21'][mode]
    assert compute_summary([rows[q] for q in rows if old[q]['answerable']]) == agg['common_subset_n20'][mode]
    for key, value in agg['group_summary'].items():
        typ, m = key.split('|')
        if m == mode:
            group = [r for r in rows.values() if r['answerable'] and r['question_type'] == typ]
            assert value == {'n': len(group), 'recall_mean': sum(r['recall'] for r in group) / len(group)}
            group_checks += 1
    for field in ('summary_by_type', 'summary_by_filter_group'):
        for group in run[field].values():
            summary = compute_summary([rows[q] for q in group['question_ids']])
            assert {k: group[k] for k in summary} == summary
            group_checks += 1
result = {
    'status': 'ok', 'readonly_files_unchanged': 23, 'rev1_archive_unchanged': 7,
    'authorized_partial_changes': partial_changes, 'changed_file_hashes': hash_count,
    'deliverables_exist': len(sub['deliverables']), 'diff_mismatches': 0,
    'score_rows_recomputed': score_checks, 'common_full_rankings': common_checks,
    'group_checks': group_checks, 'new_retrieval_or_model_calls': 0,
    'quote_note': 'Supplement hash unchanged since Astra 8/8 real-parser quote check.',
    'nonblocking_note': '38-file zero-drift wording describes the earlier inventory; final two authorized document changes are explicit here.',
}
(ROOT / 'docs/collaboration/reviews/T039-rev2-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
