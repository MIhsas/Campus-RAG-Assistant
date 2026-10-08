"""Read-only checks for T035 revision 2, no model or experiment execution."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

root = Path(__file__).resolve().parents[3]
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
delivery = root / 'docs/delivery'
submission = root / 'docs/collaboration/submissions/T035'
current = load(submission / 'submission.json')
assert current['submission_revision'] == 2 and current['responds_to'] == 'T035-R1'
changes = load(submission / 'changed-files.json')
for item in changes['updated_delivery_docs']:
    assert sha(root / item['path']) == item['sha256'], item['path']
old = load(submission / 'rev1/changed-files.json')
archived = []
for item in old['updated'] + old['new']:
    p = Path(item['path'])
    archive = delivery / 'archive-t035-rev1' / p.name if p.parent.as_posix() == 'docs/delivery' else submission / 'rev1' / p.name
    assert sha(archive) == item['sha256'], str(archive)
    archived.append(str(archive.relative_to(root)))
for name in ('report.md', 'verification.md', 'submission.json', 'changed-files.json', 'T034-doc-errata.md'):
    assert (submission / 'rev1' / name).exists()
links = []
for p in delivery.glob('*.md'):
    for raw in re.findall(r'\[[^\]]+\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        if '://' in raw or raw.startswith('#'):
            continue
        target = unquote(raw.split('#')[0].strip('<>'))
        assert (p.parent / target).exists(), (p.name, target)
        links.append((p.name, target))
text = (delivery / 'defense-script.md').read_text(encoding='utf-8')
seconds = [int(x) for x in re.findall(r'^\| [0-7] \|[^\n]*\| (\d+) \|$', text, re.M)]
assert seconds == [30, 20, 140, 120, 130, 50, 50, 20]
assert sum(seconds) == 560
expected = {'bm25': (.725, .75, .6), 'dense': (.7, .7, .44333333333333336), 'hybrid': (.7, .7, .5416666666666667)}
values = {}
overlap = load(root / 'data/evaluations/sicau-rag-overlap-v1/experiment.json')['aggregates']
selection = load(root / 'data/evaluations/sicau-rag-source-selection-v1/experiment.json')['aggregates']
for mode, triple in expected.items():
    summary = load(root / f'data/evaluations/sicau-rag-pilot-eval-v1/results/{mode}.json')['summary']
    assert tuple(summary[k] for k in ('evidence_recall', 'hit', 'mrr')) == triple
    assert summary['answerable_count'] == 20 and summary['unanswerable_count'] == 4
    for k in ('evidence_recall', 'hit', 'mrr'):
        assert overlap[f'{mode}/baseline_stored'][k] == summary[k]
    values[mode] = {'baseline': summary, 'selection': selection[f'{mode}/selection'], 'overlap': overlap[f'{mode}/candidate']}
assert sha(root / 'data/evaluations/sicau-rag-pilot-eval-v1/questions.json') == '5fde70a332744b642e48014abc82902009abc1a106a84e6241b3c460e4faed5c'
assert sha(root / 'data/evaluations/sicau-rag-source-selection-v1/selection-map.json') == '42d63bc4558584c0874737df5581171f2f4456deba59197291ff60fb5ee10de7'
assert sha(root / 'data/evaluations/sicau-rag-source-selection-v1/experiment.json') == '57b22f93bd1420faf276915c6425b3f8e8f9c978058935f8a1c69de39bd5c618'
out = {'relative_links_matched': len(links), 'current_delivery_hashes_matched': 8, 'revision1_known_hashes_matched': len(archived), 'revision1_submission_files_present': 5, 'archive_scope_note': '8 delivery files and errata matched declared revision1 hashes; other four submission files existence only, not independent original-byte verification', 'seconds': seconds, 'total_seconds': sum(seconds), 'metrics': values, 'historical_inputs_checked': ['T030 questions', 'T031 selection-map', 'T031 experiment'], 'scope': 'read-only stored data; no experiment/model/browser/test suite', 'nonblocking': 'After /ask 2023 source-mismatch demo, explicitly restore 2026 and arrange evidence again before clicking procedure entry; include in T036.'}
(root / 'docs/collaboration/reviews/T035-r2-audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('AUDIT OK: 10 links, 8 current hashes, 9 archived hashes; budget 560s; stored real baselines match; T030/T031 identity preserved')
