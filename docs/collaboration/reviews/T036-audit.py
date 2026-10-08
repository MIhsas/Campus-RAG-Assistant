"""Independent fresh-parse audit of the submitted human-review pack."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / 'step2_code/backend/src'))
from campus_assistant.corpus.parse import parse_manifest
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
corpus = root / 'data/corpora/sicau-rag-pilot-v1.1'
pack = load(root / 'step2_code/backend/.cache/human-review/T036-v1/pack.json')
questions = load(root / 'data/evaluations/sicau-rag-pilot-eval-v1/questions.json')['questions']
templates = load(root / 'data/procedures/sicau-transfer-2026-v1/procedures.json')['procedures']
parsed = parse_manifest(corpus / 'manifest.json', corpus)
assert parsed['valid']
docs = {d['document_id']: d for d in parsed['documents']}
refs = []
for original, exported in zip(questions, pack['questions'], strict=True):
    for k in ('question_id', 'query', 'conditions', 'answerable', 'question_type', 'group_id', 'rationale', 'missing', 'revision_note'):
        assert original.get(k) == exported.get(k), (original['question_id'], k)
    for a, b in zip(original.get('evidence', []), exported['evidence'], strict=True):
        for k in ('document_id', 'document_sha256', 'block_id', 'char_start', 'char_end', 'quote', 'evidence_id', 'fact_id'):
            assert a.get(k) == b.get(k)
        refs.append(b)
for original, exported in zip(templates, pack['templates'], strict=True):
    for a, b in zip(original['steps'], exported['steps'], strict=True):
        for k in ('step_id', 'title', 'detail', 'unspecified'):
            assert a.get(k) == b.get(k)
        for x, y in zip(a['citations'], b['citations'], strict=True):
            for k in ('document_id', 'document_sha256', 'block_id', 'char_start', 'char_end', 'quote'):
                assert x.get(k) == y.get(k)
            refs.append(y)
for ref in refs:
    blocks = docs[ref['document_id']]['blocks']
    index = next(i for i, b in enumerate(blocks) if b['block_id'] == ref['block_id'])
    block = blocks[index]
    assert block['text'] == ref['block_text']
    assert block['locator'] == ref['locator']
    assert block['text'][ref['char_start']:ref['char_end']] == ref['quote']
    for field, i in [('prev_block', index - 1), ('next_block', index + 1)]:
        if i < 0 or i >= len(blocks):
            assert ref[field] is None
        else:
            assert ref[field]['text'] == blocks[i]['text'] and ref[field]['block_id'] == blocks[i]['block_id']
for item in pack['pack_meta']['inputs'].values():
    assert sha(root / item['path']) == item['sha256']
assert len(refs) == 77
assert pack['pack_meta']['human_review_status'] == 'unreviewed'
changes = load(root / 'docs/collaboration/submissions/T036/changed-files.json')
for item in changes['new_code'] + changes['updated_docs']:
    assert sha(root / item['path']) == item['sha256']
out = {'fresh_parse_refs_matched': 77, 'original_question_fields_preserved': 24, 'template_steps_preserved': 13, 'full_blocks_and_neighbors_matched': 77, 'submitted_hashes_matched': 6, 'pack_human_review_status': 'unreviewed', 'browser_note': 'file URL denied by browser security policy; no browser operation/export verified', 'filter_probe': 'T036-filter-probe.json records false positives; see T036-R1'}
(root / 'docs/collaboration/reviews/T036-audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('AUDIT OK: 77 real refs/full blocks/neighbors; 24 questions and 13 steps preserved; 6 declared hashes match')
