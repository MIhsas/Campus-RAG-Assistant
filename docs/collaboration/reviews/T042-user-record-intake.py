"""Read-only validation of the user's exported record against the accepted pack."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path('C:/Users/liu33/Downloads/targeted-review-record.json')
ARCHIVE = ROOT / 'data/reviews/T042-user-review-20261014/targeted-review-record.json'
PACK = ROOT / 'step2_code/backend/.cache/human-review/T042-v1/pack.json'
def load(p):
    return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
r = load(ARCHIVE)
p = load(PACK)
checks = []
def check(label, ok):
    checks.append({'label': label, 'pass': bool(ok)})
check('copied raw bytes', sha(SOURCE) == sha(ARCHIVE))
check('record type/scope', r['record_type'] == 'targeted_review_record' and r['review_scope'] == p['pack_meta']['review_scope'])
check('not simulated label', '模拟' not in r['record_title'] and '模拟' not in r['reviewer'])
expected = {c['card_id']: c for c in p['cards']}
check('eight unique IDs', len(r['items']) == 8 and len({i['id'] for i in r['items']}) == 8 and set(expected) == {i['id'] for i in r['items']})
tally = {s: 0 for s in ('未复核', '确认', '需修订', '未确认')}
for item in r['items']:
    card = expected[item['id']]
    check(item['id'], item['object_type'] == card['object_type'] and item['question_id'] == card['question_id'] and item['opinion'] in tally and isinstance(item['comment'], str))
    tally[item['opinion']] += 1
check('tally derived from items', tally == r['tally'])
check('input fields match accepted pack', r['pack_identity']['inputs'] == p['pack_meta']['inputs'])
for name, identity in p['pack_meta']['inputs'].items():
    check('current known input: ' + name, sha(Path(identity['path'])) == identity['sha256'])
check('counts/declaration', r['pack_identity']['counts'] == p['pack_meta']['counts'] and r['pack_identity']['declaration'] == p['pack_meta']['declaration'])
out = {'source': str(SOURCE), 'archive': str(ARCHIVE), 'sha256': sha(ARCHIVE), 'checks': checks, 'pass': all(c['pass'] for c in checks), 'tally': tally, 'exported_at': r['exported_at'], 'reviewer': r['reviewer'], 'review_date': r['review_date'], 'items': r['items'],
       'chat_clarifications': {'u04': '用户选择：让正式答案也采用范围未知的资料。此次针对u04学生类型未知；保留范围未核实标识，已知冲突不纳入。', 'u03': '用户选择：保留已核实的日期，不再额外补充来源。'},
       'boundary': 'User review of these8 items, unsigned; not teacher/current-policy certification or product change. Raw record/comments preserved; chat clarifications recorded separately.'}
Path(__file__).with_suffix('.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': out['pass'], 'checks': len(checks), 'sha256': out['sha256'], 'tally': tally, 'unsigned': r['reviewer'] == '' and r['review_date'] == ''}))
raise SystemExit(0 if out['pass'] else 1)
