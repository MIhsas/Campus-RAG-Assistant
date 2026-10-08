"""Read-only revision3 identity and generated-page checks; no model loading."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
base = root / 'step2_code/backend/.cache/human-review'
submission = root / 'docs/collaboration/submissions/T036'
assert load(submission / 'submission.json')['submission_revision'] == 3
pack_path = base / 'T036-v3/pack.json'
assert pack_path.read_bytes() == (base / 'T036-v1/pack.json').read_bytes() == (base / 'T036-v2/pack.json').read_bytes()
pack = load(pack_path)
for item in pack['pack_meta']['inputs'].values():
    assert sha(root / item['path']) == item['sha256']
assert pack['pack_meta']['human_review_status'] == 'unreviewed'
assert pack['pack_meta']['counts'] == {'questions': 24, 'answerable': 20, 'unanswerable': 4, 'evidence': 57, 'template_steps': 13, 'template_citations': 20, 'verified_refs': 77}
changes = load(submission / 'changed-files.json')
for item in changes['modified']:
    assert sha(root / item['path']) == item['sha256']
old = load(submission / 'rev1/changed-files.json')
builder = old['new_code'][0]
assert sha(root / builder['path']) == builder['sha256']
assert sha(base / 'T036-v1/review.html') == 'f557f3e751c5f14f6604aea7c5c740868abd1565eafa3880b7e57af081baf0f3'
assert sha(base / 'T036-v2/review.html') == '7c82cf0daf832ea0668d6a8b15274407358510c085ffd608d9ec295b28570d01'
template = (root / 'step2_code/backend/scripts/human-review-pack.html').read_text(encoding='utf-8')
assert template.replace('/*__PACK_DATA__*/null', json.dumps(pack, ensure_ascii=False)) == (base / 'T036-v3/review.html').read_text(encoding='utf-8')
doc = (root / 'docs/delivery/human-review-pending.md').read_text(encoding='utf-8')
assert 'T036-v3/review.html' in doc and 'T036-v3-simulated-export.json' in doc
assert sha(root / 'data/evaluations/sicau-rag-pilot-eval-v1/questions.json') == '5fde70a332744b642e48014abc82902009abc1a106a84e6241b3c460e4faed5c'
result = {'pack_data_equal_versions': [1, 2, 3], 'builder_unchanged': True, 'modified_declared_hashes_matched': 2, 'historical_html_hashes_matched': 2, 'generated_v3_matches_template_and_pack': True, 'input_shas_match': True, 'counts': pack['pack_meta']['counts'], 'human_review_status': 'unreviewed', 'current_doc_entry': 'T036-v3', 'review_html_sha256': sha(base / 'T036-v3/review.html'), 'scope': 'read-only identity audit; no browser/model/parser/experiment rerun'}
(root / 'docs/collaboration/reviews/T036-r3-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('AUDIT OK: v1/v2/v3 data equal; inputs/builder/historical HTML preserved; v3 generated page and current entry match')
