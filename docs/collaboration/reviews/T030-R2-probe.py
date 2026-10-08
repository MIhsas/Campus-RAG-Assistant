"""Read-only semantic regression: a partial alternative must not satisfy full f1."""
from pathlib import Path
import copy
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'step2_code/backend'
sys.path.insert(0, str(B / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.evaluation.metrics import evaluate_question
D = ROOT / 'data/evaluations/sicau-rag-pilot-eval-v1'
pack = ROOT / 'data/corpora/sicau-rag-pilot-v1.1'
parsed = parse_manifest(pack / 'manifest.json', pack)
assert parsed['valid']
blocks = {(d['document_id'], b['block_id']): b for d in parsed['documents'] for b in d['blocks']}
q = next(q for q in json.loads((D / 'questions.json').read_text(encoding='utf-8'))['questions'] if q['question_id'] == 'q10')
records = []
for prefix in ['cc25a92b', 'bb8ba97c']:
    ev = next(e for e in q['evidence'] if e['fact_id'] == 'f1' and e['document_id'].startswith(prefix))
    text = blocks[(ev['document_id'], ev['block_id'])]['text']
    end = text.index('答辩成绩（50%）', ev['char_start']) + len('答辩成绩（50%）')
    teacher_end = text.index('导师评定成绩（50%）', ev['char_start']) + len('导师评定成绩（50%）')
    hit = {'score': 1, 'chunk': dict(ev, char_end=teacher_end)}
    got = evaluate_question(q, [hit])
    amended = copy.deepcopy(q)
    for e in amended['evidence']:
        if e['evidence_id'] == ev['evidence_id'] and e['document_id'] == ev['document_id']:
            e['char_end'] = end
            e['quote'] = text[e['char_start']:end]
    counter = evaluate_question(amended, [hit])
    records.append({'document_prefix': prefix, 'block_id': ev['block_id'],
                    'submitted_quote': ev['quote'], 'complete_fact_same_block': text[ev['char_start']:end],
                    'teacher_only_hit_recall': got['recall'], 'counterfactual_complete_gold_recall': counter['recall'],
                    'defect_present': got['recall'] > 0})
q13context = [dict(block_id=b['block_id'], text=b['text']) for d in parsed['documents']
              if d['document_id'].startswith('92049') for b in d['blocks'][:2]]
out = {'kind': 'actual parse and minimal single-hit scoring, not new retrieval', 'q10': records, 'q13_context': q13context}
cache = B / '.cache/astra-t030'
cache.mkdir(exist_ok=True, parents=True)
(cache / 'r2-semantic-probe-latest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(records, ensure_ascii=False, indent=2))
raise SystemExit(1 if any(r['defect_present'] for r in records) else 0)
