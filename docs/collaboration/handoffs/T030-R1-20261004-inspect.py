"""Handoff inventory; read-only hashes and saved-rank scoring, no retrieval."""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'step2_code/backend'
D = ROOT / 'data/evaluations/sicau-rag-pilot-eval-v1'
S = ROOT / 'docs/collaboration/submissions/T030'
sys.path.insert(0, str(B / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary
def read(p):
    return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
q, old, f = read(D / 'questions.json'), read(D / 'rev1/questions.json'), read(D / 'freeze.json')
qm = {x['question_id']: x for x in q['questions']}
om = {x['question_id']: x for x in old['questions']}
changed = [k for k in qm if any(qm[k].get(v) != om[k].get(v) for v in ('query', 'conditions'))]
pack = Path(f['corpus_pack']['path'])
pairs = [(D / 'questions.json', f['dataset']['questions_sha256']), (pack / 'manifest.json', f['corpus_pack']['manifest_sha256'])]
pairs += [(pack / p, h) for p, h in f['corpus_pack']['files'].items()]
pairs += [(B / p, h) for p, h in f['implementation_sha256'].items()]
pairs += [(B / f['embedding_model']['dir'] / p, h) for p, h in f['embedding_model']['identity_files_sha256'].items()]
pairs += [(ROOT / p, h) for p, h in f['annotation_files'].items()]
checks = [{'path': str(p.relative_to(ROOT)), 'matches': sha(p) == h} for p, h in pairs]
runs = {}
for mode in ('bm25', 'dense', 'hybrid'):
    current = read(D / 'results' / f'{mode}.json')
    orig = {x['question_id']: x for x in read(D / 'rev1/results' / f'{mode}.json')['per_question']}
    new = {x['question_id']: x for x in read(D / 'results/rerun' / f'{mode}.json')['per_question']}
    scores, bad_scores, bad_ranks = [], [], []
    for row in current['per_question']:
        key = row['question_id']
        v = evaluate_question(qm[key], [{'score': h['score'], 'chunk': h} for h in row['hit_summary']], top_k=5)
        scores.append(v)
        if any(v[k] != row[k] for k in ('recall', 'hit', 'mrr', 'returned_count')):
            bad_scores.append(key)
        if row['hit_summary'] != (new[key] if key in changed else orig[key])['hit_summary']:
            bad_ranks.append(key)
    runs[mode] = {'count': len(scores), 'rerun_count': len(new), 'score_mismatches': bad_scores,
                  'merged_rank_mismatches': bad_ranks, 'summary_matches': compute_summary(scores) == current['summary'],
                  'summary': current['summary'],
                  'recorded_rerun_exitcode': (D / 'results/rerun' / f'{mode}.exitcode.txt').read_text().strip()}
files = sorted({p for top in (D, S) for p in top.rglob('*') if p.is_file()} | {B / 'scripts/check-real-eval.py'})
result = {'date': '2026-10-04 Asia/Shanghai', 'purpose': 'handoff snapshot, not acceptance',
          'dataset_version': q['dataset_version'], 'questions_sha256': sha(D / 'questions.json'),
          'rev1_questions_sha256': sha(D / 'rev1/questions.json'), 'changed_query_or_conditions': changed,
          'freeze_checks': checks, 'runs': runs, 'submission_revision': read(S / 'submission.json')['submission_revision'],
          'submission_rev1_archive_files': [str(p.relative_to(S)) for p in (S / 'rev1').rglob('*') if p.is_file()],
          'inventory': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files],
          'not_verified': ['checker CLI/tests not rerun this turn', 'semantic acceptance of revised gold',
                           'chronology or previous execution count', 'fresh dense/hybrid retrieval']}
Path(__file__).with_name('T030-R1-20261004-state.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'hashes': len(checks), 'matched': sum(x['matches'] for x in checks), 'runs': runs, 'inventory_files': len(files)}, ensure_ascii=False))
