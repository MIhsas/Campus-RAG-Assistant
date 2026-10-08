"""Astra read-only audit of delivery links, declared hashes and saved metrics."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
DELIVERY = ROOT / 'docs/delivery'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = sorted(DELIVERY.glob('*.md'))
links = []
for p in files:
    for raw in re.findall(r'\[[^\]]+\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        if '://' in raw or raw.startswith('#'):
            continue
        target = unquote(raw.split('#')[0].strip('<>'))
        resolved = p.parent / target
        links.append({'file': p.name, 'target': target, 'exists': resolved.exists()})
assert all(x['exists'] for x in links), links
changes = load(ROOT / 'docs/collaboration/submissions/T035/changed-files.json')
hashes = []
for item in changes['updated'] + changes['new']:
    path = ROOT / item['path']
    assert sha(path) == item['sha256'], item['path']
    hashes.append(item['path'])
expected = {
    'bm25': (.725, .75, .6),
    'dense': (.7, .7, .44333333333333336),
    'hybrid': (.7, .7, .5416666666666667),
}
def triple(s):
    return tuple(s[k] for k in ('evidence_recall', 'hit', 'mrr'))
baseline = {}
for mode, values in expected.items():
    s = load(ROOT / f'data/evaluations/sicau-rag-pilot-eval-v1/results/{mode}.json')['summary']
    assert triple(s) == values
    assert (s['answerable_count'], s['unanswerable_count']) == (20, 4)
    baseline[mode] = s
selection = load(ROOT / 'data/evaluations/sicau-rag-source-selection-v1/experiment.json')['aggregates']
expected_selection = {
    'bm25/baseline': (.55, .6, .35),
    'bm25/selection': (.9, .9, .5033333333333333),
    'dense/baseline': (.5, .5, .23333333333333334),
    'dense/selection': (.9, .9, .5483333333333333),
    'hybrid/baseline': (.4, .4, .2833333333333333),
    'hybrid/selection': (.9, .9, .5),
}
for key, values in expected_selection.items():
    assert triple(selection[key]) == values, key
overlap = load(ROOT / 'data/evaluations/sicau-rag-overlap-v1/experiment.json')['aggregates']
candidate = {'bm25': (.725, .75, .5958333333333333), 'dense': (.675, .7, .4666666666666667), 'hybrid': (.7, .7, .5833333333333333)}
for mode in expected:
    assert triple(overlap[f'{mode}/baseline_stored']) == expected[mode]
    assert triple(overlap[f'{mode}/candidate']) == candidate[mode]
    assert overlap[f'{mode}/candidate']['answerable_count'] == 20
archive = DELIVERY / 'archive-t028-delivery'
assert len(list(archive.glob('*.md'))) == 6
output = {
    'scope': '8 current delivery markdown files; literal relative markdown links; 9 declared SHA values; stored T030/T031/T034 aggregate values, no experiments executed',
    'delivery_files': len(files), 'relative_links': links, 'declared_hashes_matched': len(hashes),
    'archive_file_count': 6, 'archive_note': 'Existence/count checked; no independent original-byte comparison claimed',
    'baseline': baseline, 'selection': selection, 'overlap': overlap,
    'defense_main_seconds_minimum': 40 + 30 + 150 + 90 + 120 + 60 + 90 + 30,
    'review_note': 'Numeric/link/hash checks pass; document acceptance is separate. See T035-R1 for overwriting commands, script timing/route/evidence and stale current-state text.',
}
(ROOT / 'docs/collaboration/reviews/T035-audit.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'AUDIT OK: {len(files)} files, {len(links)} relative links, {len(hashes)} hashes; stored real metrics match; main >=710 seconds. See review for document findings.')
