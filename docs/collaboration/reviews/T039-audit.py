"""Astra read-only T039 audit; own outputs only, no vector or cloud calls."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'step2_code/backend'
sys.path.insert(0, str(BACKEND / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary
from campus_assistant.evaluation.run import _run_eval

def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

old = Path('data/evaluations/sicau-rag-pilot-eval-v1')
new = Path('data/evaluations/sicau-rag-pilot-eval-v2')
out = ROOT / 'docs/collaboration/reviews/T039-audit.json'
historical = load('docs/collaboration/reviews/T038-audit.json')['historical_hashes']
for path, expected in historical.items():
    assert sha(path) == expected, path
q1 = load(old / 'questions.json')
q2 = load(new / 'questions.json')
oldq = {q['question_id']: q for q in q1['questions']}
newq = {q['question_id']: q for q in q2['questions']}
assert set(oldq) == set(newq) and len(newq) == 24
allowed = {q: {'rationale', 'revision_note'} for q in ('q08', 'q10')}
allowed.update({q: {'rationale', 'missing', 'revision_note'} for q in ('u01', 'u02', 'u04')})
allowed['u03'] = {'answerable', 'evidence', 'question_type', 'rationale', 'missing', 'revision_note'}
diff = {}
for qid in newq:
    a, b = oldq[qid], newq[qid]
    fields = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if fields:
        diff[qid] = fields
    assert set(fields) <= allowed.get(qid, set()), (qid, fields)
    assert a['query'] == b['query'] and a['conditions'] == b['conditions']
    if qid != 'u03':
        assert a['evidence'] == b['evidence'] and a['answerable'] == b['answerable']
assert sum(q['answerable'] for q in newq.values()) == 21
assert sum(len(q['evidence']) for q in newq.values()) == 58
assert newq['u03']['evidence'][0]['document_id'].startswith('bed3ac')
assert newq['u03']['evidence'][0]['quote'] == next(e['quote'] for e in oldq['q09']['evidence'] if e['document_id'].startswith('bed3ac'))
submitted = {r['question_id']: r['changed_fields'] for r in load(new / 'field-diff.json')['question_diffs']}
assert set(submitted) == set(newq)
diff_mismatches = [{'question_id': qid, 'expected': diff.get(qid, []), 'submitted': submitted.get(qid)} for qid in newq if diff.get(qid, []) != sorted(submitted[qid])]

agg = load(new / 'aggregate.json')
runs = {m: load(new / 'results' / (m+'.json')) for m in ('bm25', 'dense', 'hybrid')}
old_runs = {m: load(old / 'results' / (m+'.json')) for m in runs}
recomputed = {}
common_checks = 0
group_checks = 0
manual = {}
for mode, run in runs.items():
    assert run['valid'] and run['question_count'] == 24
    assert run['manifest_sha256'] == sha('data/corpora/sicau-rag-pilot-v1.2/manifest.json')
    assert run['questions_sha256'] == sha(new / 'questions.json')
    assert (ROOT / new / 'results' / (mode+'.exitcode.txt')).read_text().strip() == '0'
    rows = {r['question_id']: r for r in run['per_question']}
    old_rows = {r['question_id']: r for r in old_runs[mode]['per_question']}
    assert set(rows) == set(newq)
    scored = []
    for qid, row in rows.items():
        hits = [{'score': h['score'], 'chunk': h, 'preview_url': h.get('preview_url', '')} for h in row['hit_summary']]
        fresh = evaluate_question(newq[qid], hits, top_k=5)
        for key in fresh:
            assert fresh[key] == row[key], (mode, qid, key)
        scored.append(fresh)
        if oldq[qid]['answerable']:
            assert row['hit_summary'] == old_rows[qid]['hit_summary'], (mode, qid, 'rankings')
            for key in ('recall', 'hit', 'mrr', 'covered_evidence_ids', 'fact_count', 'covered_fact_count'):
                assert row[key] == old_rows[qid][key], (mode, qid, key)
            common_checks += 1
    summary = compute_summary(scored)
    assert summary == run['summary'] == agg['aggregates_n21'][mode]
    common = compute_summary([rows[qid] for qid in rows if oldq[qid]['answerable']])
    assert common == agg['common_subset_n20'][mode]
    recomputed[mode] = summary
    for key, value in agg['group_summary'].items():
        typ, m = key.split('|')
        if m != mode:
            continue
        group = [row for row in rows.values() if row['answerable'] and row['question_type'] == typ]
        assert value == {'n': len(group), 'recall_mean': sum(r['recall'] for r in group)/len(group)}
        group_checks += 1
    for field in ('summary_by_type', 'summary_by_filter_group'):
        for group in run[field].values():
            assert {k: group[k] for k in summary} == compute_summary([rows[q] for q in group['question_ids']])
            assert group['question_count'] == len(group['question_ids'])
            group_checks += 1
    # Direct manual interval checks for the two reported examples, independent of evaluator calls.
    manual[mode] = {}
    for qid in ('u03', 'q10'):
        facts = {}
        for ev in newq[qid]['evidence']:
            cursor = ev['char_start']
            intervals = sorted((h['char_start'], h['char_end']) for h in rows[qid]['hit_summary'] if h['document_id'] == ev['document_id'] and h['block_id'] == ev['block_id'])
            for start, end in intervals:
                if start <= cursor:
                    cursor = max(cursor, end)
            facts.setdefault(ev['fact_id'], []).append(cursor >= ev['char_end'])
        covered = sum(any(v) for v in facts.values())
        expected_recall = covered/len(facts)
        assert rows[qid]['recall'] == expected_recall == 1.0
        assert rows[qid]['mrr'] == 1.0
        manual[mode][qid] = {'fact_count': len(facts), 'covered_facts': covered, 'recall': expected_recall, 'mrr': 1.0}

fresh_bm25 = _run_eval(ROOT / 'data/corpora/sicau-rag-pilot-v1.2/manifest.json', ROOT / 'data/corpora/sicau-rag-pilot-v1.2', ROOT / new / 'questions.json', 5, 'bm25', None)
assert fresh_bm25['valid'] and fresh_bm25['summary'] == runs['bm25']['summary']
for a, b in zip(fresh_bm25['per_question'], runs['bm25']['per_question']):
    for key in ('question_id', 'hit_summary', 'recall', 'hit', 'mrr'):
        assert a[key] == b[key], (a['question_id'], key)
(ROOT / 'docs/collaboration/reviews/T039-bm25-fresh.json').write_text(json.dumps(fresh_bm25, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
result = {'question_count': 24, 'evidence_count': 58, 'expected_question_diffs': diff,
          'submitted_diff_mismatches': diff_mismatches, 'score_rows_recomputed': 72,
          'common_ranking_and_score_checks': common_checks, 'aggregate_and_group_checks': group_checks,
          'aggregates': recomputed, 'manual_examples': manual, 'fresh_bm25_rows_equal': 24,
          'historical_hashes_verified': historical,
          'status': 'evidence_error' if diff_mismatches else 'ok'}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('SCORES OK: 72 rows; common rankings/scores', common_checks, '; fresh BM25 24 rows; group checks', group_checks)
print('EXPECTED CHANGES:', json.dumps(diff, ensure_ascii=False))
print('SUBMITTED DIFF MISMATCHES:', len(diff_mismatches))
sys.exit(1 if diff_mismatches else 0)
