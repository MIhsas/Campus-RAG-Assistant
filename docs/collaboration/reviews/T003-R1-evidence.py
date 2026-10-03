"""Astra independent probes. Run with the backend .venv Python from project root."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid

root = Path(__file__).resolve().parents[3]
backend = root / 'step2_code/backend'
corpus = backend / 'examples/synthetic-corpus'
baseline = json.loads((corpus / 'manifest.json').read_text(encoding='utf-8'))
scratch = backend / '.cache' / ('astra-probes-' + uuid.uuid4().hex)
scratch.mkdir(parents=True)

def run(name, change=None, raw=None):
    data = copy.deepcopy(baseline)
    if change:
        change(data)
    path = scratch / (name + '.json')
    if raw is None:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    else:
        path.write_bytes(raw)
    proc = subprocess.run([sys.executable, '-m', 'campus_assistant.corpus.validate',
        '--manifest', str(path), '--corpus-root', str(corpus)],
        cwd=backend, capture_output=True, encoding='utf-8', errors='replace')
    try:
        out = json.loads(proc.stdout)
        result = {'valid': out['valid'], 'document_count': out['document_count'],
                  'errors': [{'code': e['code'], 'field': e['field']} for e in out['errors']]}
    except ValueError:
        result = {'json_output': False, 'stderr_last_line': proc.stderr.strip().splitlines()[-1:]}
    print(json.dumps({'case': name, 'exit': proc.returncode, **result}, ensure_ascii=True))

def field(key, value):
    return lambda m: m['documents'][0].__setitem__(key, value)

run('baseline')
run('boolean_string', field('is_synthetic', 'false'))
run('impossible_date', field('published_at', '2024-13-01'))
run('non_leap_day', field('published_at', '2025-02-29'))
run('missing_scope', lambda m: m['documents'][0].pop('scope'))
run('missing_date', lambda m: m['documents'][0].pop('published_at'))
run('empty_scope_object', field('scope', {}))
run('bad_years', field('scope', {'campus': [], 'student_type': [], 'admission_years': [1899, 2101, '2024', True]}))
run('blank_campus', field('scope', {'campus': ['  '], 'student_type': [], 'admission_years': []}))
run('campus_string', field('scope', {'campus': 'abc', 'student_type': [], 'admission_years': []}))
run('no_url_host', field('source_url', 'https://?query'))
run('null_campus', field('scope', {'campus': None, 'student_type': [], 'admission_years': []}))
run('invalid_utf8', raw=b'\xff')
run('bad_hash_count', field('sha256', '0' * 64))
run('duplicate_and_bad_hash', lambda m: (m['documents'][1].__setitem__('document_id', m['documents'][0]['document_id']), m['documents'][0].__setitem__('sha256', '0' * 64)))
run('masked_boolean_test', lambda m: (m['documents'][0].__setitem__('is_synthetic', 'false'), m['documents'][0].__setitem__('sha256', '')))
