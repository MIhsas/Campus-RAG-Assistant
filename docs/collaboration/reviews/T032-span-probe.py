"""Astra: focused completeness checks, independent of quote-substring validity."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
template = json.loads((root / 'data/procedures/sicau-transfer-2026-v1/procedures.json').read_text(encoding='utf-8'))
steps = {s['step_id']: s for s in template['procedures'][0]['steps']}
expected = {'t2': '按照必修课初修加权平均', 't8': '或后', 't12': '必须遵守学校'}
rows = []
for sid, phrase in expected.items():
    citations = steps[sid]['citations']
    rows.append({'step_id': sid, 'required_page_tail': phrase,
                 'present_in_citations': phrase in ''.join(c['quote'] for c in citations)})
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({'checks': rows, 'passed': all(r['present_in_citations'] for r in rows)}, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(r['present_in_citations'] for r in rows) else 1)
