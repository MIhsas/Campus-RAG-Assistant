"""Read actual parse cache from this review; never change submitted gold/ranks."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'step2_code/backend'
sys.path.insert(0, str(BACKEND / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question

parsed = json.loads((BACKEND / '.cache/astra-t030/parsed.json').read_text(encoding='utf-8'))
base = ROOT / 'data/evaluations/sicau-rag-pilot-eval-v1'
questions = json.loads((base / 'questions.json').read_text(encoding='utf-8'))['questions']
q = next(q for q in questions if q['question_id'] == 'q05')
d = next(d for d in parsed['documents'] if d['document_id'].startswith('c888'))
b = next(b for b in d['blocks'] if b['block_id'] == 'a6e7cb5f1538e074')
quote = '学生须在答辩前一周将毕业论文（设计）提交答辩小组'
start = b['text'].index(quote)
ev = dict(q['evidence'][0], evidence_id='astra-q05-docx',
          document_id=d['document_id'], document_sha256=d['metadata']['sha256'],
          parser_version=d['parser_version'], block_id=b['block_id'],
          char_start=start, char_end=start + len(quote), quote=quote)
adjusted = dict(q, evidence=q['evidence'] + [ev])
result = {'kind': 'counterfactual annotation probe, not a new official evaluation',
          'missing_alternative': ev, 'saved_rank_effect': {}, 'source_blocks': []}
for mode in ('bm25', 'dense', 'hybrid'):
    run = json.loads((base / 'results' / f'{mode}.json').read_text(encoding='utf-8'))
    old = next(p for p in run['per_question'] if p['question_id'] == 'q05')
    hits = [{'chunk': h, 'score': h['score']} for h in old['hit_summary']]
    new = evaluate_question(adjusted, hits)
    result['saved_rank_effect'][mode] = {'old_mrr': old['mrr'],
                                       'with_one_missing_alternative_mrr': new['mrr']}
for doc in parsed['documents']:
    for block in doc['blocks']:
        if block['block_id'] in {'9de19468b7427552', 'f74aff0841628203',
                                '43602ebd8cb36c00', '44392bef6f807d23',
                                '2e39739015cd2bb3', '29c7823193e4987d',
                                'a7824b29ba7a3900'}:
            result['source_blocks'].append(dict(document_id=doc['document_id'],
                                               block_id=block['block_id'],
                                               locator=block['locator'], text=block['text']))
# Keep the historical review evidence immutable on subsequent reruns.
(BACKEND / '.cache/astra-t030/semantic-audit-latest.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result['saved_rank_effect'], ensure_ascii=False))
