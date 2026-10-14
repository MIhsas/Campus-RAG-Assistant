"""Astra focused artifact and real local API/message audit; no model requests."""
import hashlib
import json
from pathlib import Path
import httpx
from campus_assistant.qa.deepseek import build_messages

ROOT = Path(__file__).resolve().parents[3]
rows = []
def check(name, condition, detail=None):
    rows.append(dict(name=name, pass_=bool(condition), detail=detail))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

listing = json.loads((ROOT/'docs/collaboration/submissions/T043/changed-files.json').read_text(encoding='utf-8'))
for section in ('code_modified','tests_new','delivery_docs','submissions'):
    for item in listing[section]:
        if item.get('sha256'):
            actual = sha(ROOT/item['path'])
            check('submitted SHA: '+item['path'], actual == item['sha256'], actual)
frozen = {
 'data/reviews/T042-user-review-20261014/targeted-review-record.json':'7a0c6ec4a685f4a1a0904d793d35434e776426f8528d17ed6998ddad20c51133',
 'docs/delivery/generation-casebook.md':'6ef5215d190d694d47bd4780e73f947049c8eb275aac491fa9ec480be05c11c8',
 'data/evaluations/sicau-rag-pilot-eval-v2/questions.json':'4e39229eb3b31dc9ccd5dc157e2d63203514ce70069450adca6b78c24b65c103',
 'data/evaluations/sicau-rag-pilot-eval-v2/freeze.json':'8c289b2ae7f00b39be80f02f850cf2820d8cc6de90f6f7245c634ddd2a9b5a26',
 'data/corpora/sicau-rag-pilot-v1.2/manifest.json':'b05c37557675f02c045e01e9fd776c539954c43172d5e0b07d0704da4e352b4a',
 'docs/collaboration/submissions/T040/live-results.json':'e607654b34a51f6361215c9e804c496e864905ab24a9e7bbf1bfb46063784072',
 'docs/collaboration/submissions/T040/live-answers-full.json':'9641695095912d3f6de19f9194beecf35fb2691f90afdad76f7323f46686cc4e',
}
for name, expected in frozen.items():
    check('preserved: '+name, sha(ROOT/name)==expected)

query = '学籍基本信息有误需要更正时，学生本人去哪里办理？'
doc = '83eb3948386df27ddc8db35591dbab6c97dd795b92c8b003f2f524339cec2f31'
with httpx.Client(base_url='http://127.0.0.1:18764',trust_env=False,timeout=30) as client:
    results = {}
    for admit in (False,True):
        r = client.post('/api/v1/ask',json=dict(query=query,mode='bm25',answer_mode='extractive',
            filters={'student_type':'本科'},include_unknown_student_type=admit))
        check('extractive HTTP '+str(admit),r.status_code==200)
        results[admit]=r.json()
    strict, ref = results[False], results[True]
    reference_e = [e for e in ref['evidence'] if e['document_id']==doc]
    check('strict excludes unknown source',not any(e['document_id']==doc for e in strict['evidence']))
    check('reference mode sends location evidence',any('105' in e['text'] and '217' in e['text'] for e in reference_e))
    check('reference status on actual E',bool(reference_e) and all(e['student_type_status']=='学生类型未标注，适用范围尚未核实' for e in reference_e))
    messages=build_messages(query=query,evidence=ref['evidence'],filters=ref['filters'])
    user=messages[-1]['content']
    check('actual E warning and unmodified quote in messages',all(
        f"【{e['evidence_id']}】（{e['student_type_status']}）\n{e['text']}" in user for e in reference_e))
    check('generator remains off',not client.get('/api/v1/ask/status').json()['generator_configured'])
    no_filter = client.post('/api/v1/search',json={'query':query}).json()
    # Record semantics for a nonblocking documentation/statistics clarification.
    counters_without_type = {k:no_filter['filter_summary'].get(k) for k in
        ('active','confirmed_count','reference_count','allowed_count')}

out=dict(scope='hashes + actual local extractive API + build_messages; no model HTTP',rows=rows,
    checks=len(rows), failures=sum(not r['pass_'] for r in rows),
    statistics_without_student_type_filter=counters_without_type)
(ROOT/'docs/collaboration/reviews/T043-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='rows'},ensure_ascii=False))
raise SystemExit(bool(out['failures']))
