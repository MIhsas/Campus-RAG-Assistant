"""Astra independent T030 audit. Read-only inputs; isolated altered freeze.

Run from any cwd with backend .venv Python. Exit 1 means freeze defect persists.
No embedding, network, product edits, or changes to submitted evidence.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'step2_code/backend'
DATA = ROOT / 'data/evaluations/sicau-rag-pilot-eval-v1'
CACHE = BACKEND / '.cache/astra-t030'
CACHE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary

fz = json.loads((DATA / 'freeze.json').read_text(encoding='utf-8'))
pack = Path(fz['corpus_pack']['path'])
pairs = [(DATA / 'questions.json', fz['dataset']['questions_sha256']),
         (pack / 'manifest.json', fz['corpus_pack']['manifest_sha256'])]
pairs += [(pack / p, h) for p, h in fz['corpus_pack']['files'].items()]
pairs += [(BACKEND / p, h) for p, h in fz['implementation_sha256'].items()]
pairs += [(BACKEND / fz['embedding_model']['dir'] / p, h)
          for p, h in fz['embedding_model']['identity_files_sha256'].items()]
hash_checks = [{'path': str(p.relative_to(ROOT)),
                'matches': hashlib.sha256(p.read_bytes()).hexdigest() == h}
               for p, h in pairs]
questions = json.loads((DATA / 'questions.json').read_text(encoding='utf-8'))['questions']
by_id = {q['question_id']: q for q in questions}
rescoring = {}
for mode in ('bm25', 'dense', 'hybrid'):
    r = json.loads((DATA / 'results' / f'{mode}.json').read_text(encoding='utf-8'))
    recalculated = []
    mismatches = []
    for q in r['per_question']:
        hits = [{'chunk': h, 'score': h['score']} for h in q['hit_summary']]
        v = evaluate_question(by_id[q['question_id']], hits, top_k=5)
        recalculated.append(v)
        if any(v[k] != q[k] for k in ('recall', 'hit', 'mrr', 'returned_count')):
            mismatches.append(q['question_id'])
    rescoring[mode] = {'count': len(recalculated), 'mismatches': mismatches,
                       'summary': compute_summary(recalculated)}

bad = copy.deepcopy(fz)
bad['dataset']['questions_sha256'] = '0' * 64
badpath = CACHE / 'freeze-wrong-questions-hash.json'
badpath.write_text(json.dumps(bad, ensure_ascii=False, indent=2), encoding='utf-8')
cli = [sys.executable, str(BACKEND / 'scripts/check-real-eval.py'),
       '--pack', str(pack), '--questions', str(DATA / 'questions.json'), '--freeze']
env = dict(os.environ, PYTHONIOENCODING='utf-8')
checks = {}
for name, path in [('submitted', DATA / 'freeze.json'), ('wrong_questions_hash', badpath)]:
    proc = subprocess.run(cli + [str(path)], cwd=BACKEND, capture_output=True,
                          text=True, encoding='utf-8', env=env)
    checks[name] = {'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
result = {'kind': 'independent local audit; saved-rank rescoring, not new retrieval',
          'hash_checks': hash_checks, 'rescoring': rescoring,
          'actual_checker_cli': checks,
          'wrong_hash_rejected': checks['wrong_questions_hash']['exit_code'] != 0}
# Historical T030-audit-v1.json is preserved; reruns write only a cache artifact.
out = CACHE / 'audit-latest.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('Independent hashes:', len(hash_checks), 'matched:', sum(x['matches'] for x in hash_checks))
print('Saved ranking scores:', {k: v['mismatches'] for k, v in rescoring.items()})
for k, v in checks.items():
    print(k, 'exit=', v['exit_code'], v['stdout'].strip())
print('wrong_hash_rejected=', result['wrong_hash_rejected'])
raise SystemExit(0 if result['wrong_hash_rejected'] else 1)
