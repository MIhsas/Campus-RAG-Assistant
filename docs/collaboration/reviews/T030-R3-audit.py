"""Independent final hashes, saved-score, rank provenance and group audit."""
from pathlib import Path
import json, hashlib, sys
ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'step2_code/backend'
D = ROOT / 'data/evaluations/sicau-rag-pilot-eval-v1'
sys.path.insert(0, str(B / 'src'))
sys.stdout.reconfigure(encoding='utf-8')
from campus_assistant.evaluation.metrics import evaluate_question, compute_summary
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
ds = read(D / 'questions.json'); qs = {q['question_id']: q for q in ds['questions']}
f = read(D / 'freeze.json'); pack = Path(f['corpus_pack']['path'])
pairs = [(D/'questions.json', f['dataset']['questions_sha256']), (pack/'manifest.json',f['corpus_pack']['manifest_sha256'])]
pairs += [(pack/p,h) for p,h in f['corpus_pack']['files'].items()]
pairs += [(B/p,h) for p,h in f['implementation_sha256'].items()]
pairs += [(B/f['embedding_model']['dir']/p,h) for p,h in f['embedding_model']['identity_files_sha256'].items()]
pairs += [(ROOT/p,h) for p,h in f['annotation_files'].items()]
errors = [str(p) for p,h in pairs if sha(p)!=h]; results = {}
for mode in ['bm25','dense','hybrid']:
    run=read(D/'results'/f'{mode}.json')
    old={q['question_id']:q for q in read(D/'archive-v1_2-rev2base/results'/f'{mode}.json')['per_question']}
    rerun=read(D/'results/rerun-v13'/f'{mode}.json')['per_question'][0]
    recalculated=[]; bt={}; bf={}; diffs=[]
    for row in run['per_question']:
        id=row['question_id']; v=evaluate_question(qs[id],[{'chunk':h,'score':h['score']} for h in row['hit_summary']])
        recalculated.append(v)
        for k in ['recall','hit','mrr','returned_count']:
            if v[k]!=row[k]: errors.append(f'{mode}/{id}/{k}')
        source=rerun if id=='q13' else old[id]
        if row['hit_summary']!=source['hit_summary']:errors.append(f'{mode}/{id}/rank')
        if any(row[k]!=old[id][k] for k in ['recall','hit','mrr']):diffs.append(id)
        bt.setdefault(row.get('question_type') or 'untyped',[]).append(row)
        cond=row.get('conditions');active=bool(cond and any(cond.get(k) is not None for k in ['campus','student_type','admission_year','as_of_date']))
        key=(row['group_id']+'|filtered') if row.get('group_id') and active else ('filtered' if active else 'no_filter')
        bf.setdefault(key,[]).append(row)
    if compute_summary(recalculated)!=run['summary']:errors.append(mode+'/summary')
    for field, groups in [('summary_by_type',bt),('summary_by_filter_group',bf)]:
        for key,rows in groups.items():
            expected=compute_summary(rows);expected['question_count']=len(rows)
            for k,v in expected.items():
                if run[field][key].get(k)!=v:errors.append(f'{mode}/{field}/{key}/{k}')
    results[mode]={'summary':run['summary'],'score_changed_from_v12':diffs}
assert read(D/'archive-v1_2-rev2base/freeze.json')['dataset']['questions_sha256']==sha(D/'archive-v1_2-rev2base/questions.json')
out={'dataset_version':ds['dataset_version'],'questions_sha256':sha(D/'questions.json'),'hash_count':len(pairs),
     'results':results,'errors':errors,'scope':'38 hashes,72 saved scores/rank sources,group summaries; no new retrieval'}
Path(__file__).with_name('T030-audit-v3.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False));raise SystemExit(bool(errors))
