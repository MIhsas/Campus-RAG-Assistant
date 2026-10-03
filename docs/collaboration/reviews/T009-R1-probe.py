"""Independent acceptance probes; product files remain unchanged."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid
from campus_assistant.corpus.parse import parse_manifest

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[3]
backend = root / 'step2_code/backend'
corpus = backend / 'examples/parse-corpus'
manifest = corpus / 'manifest.json'
questions = backend / 'examples/evaluation/questions.json'
temp = backend / '.cache' / ('astra-t009-' + uuid.uuid4().hex)
temp.mkdir(parents=True)
original = json.loads(questions.read_text(encoding='utf-8'))
parsed = parse_manifest(manifest, corpus)
docs = {d['document_id']: d for d in parsed['documents']}
output = {'example_annotations': [], 'cases': {}}
for q in original['questions']:
    for ev in q['evidence']:
        doc = docs[ev['document_id']]
        block = next(b for b in doc['blocks'] if b['block_id'] == ev['block_id'])
        text = block['text']
        actual = text[ev['char_start']:ev['char_end']]
        output['example_annotations'].append({'question_id':q['question_id'],'evidence_id':ev['evidence_id'],
            'block_length':len(text),'start':ev['char_start'],'end':ev['char_end'],
            'quote_matches':actual==ev['quote'],'bounds_valid':0<=ev['char_start']<ev['char_end']<=len(text),
            'actual_slice':actual,'quote_found_at':text.find(ev['quote'])})

def run(name, data):
    p = temp / (name + '.json')
    p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    cmd = [sys.executable,'-m','campus_assistant.evaluation.run','--manifest',str(manifest),
           '--corpus-root',str(corpus),'--questions',str(p)]
    proc = subprocess.run(cmd,capture_output=True,cwd=temp)
    result = json.loads(proc.stdout.decode('utf-8'))
    output['cases'][name] = {'exit':proc.returncode,'valid':result['valid'],'summary':result['summary'],
        'errors':result['errors'],'split':result['split'],'is_synthetic':result['is_synthetic']}

run('submitted_example',original)
base = copy.deepcopy(original)
base['questions'] = base['questions'][:1]
ev = base['questions'][0]['evidence'][0]
block = next(b for b in docs[ev['document_id']]['blocks'] if b['block_id']==ev['block_id'])
ev.update(char_start=0,char_end=len(block['text']),quote=block['text'])
run('valid_control',base)
for field,value in [('block_id','missing'),('parser_version','999'),('char_end',9999),('quote','not the source')]:
    data = copy.deepcopy(base);data['questions'][0]['evidence'][0][field]=value
    run('bad_'+field,data)
for name,same_id in [('duplicate_id',True),('duplicate_span',False)]:
    data = copy.deepcopy(base);new = copy.deepcopy(data['questions'][0]['evidence'][0])
    if not same_id:new['evidence_id']='other'
    data['questions'][0]['evidence'].append(new);run(name,data)
for name,field,val in [('synthetic_string','is_synthetic','true'),('synthetic_number','is_synthetic',1),('test_split','split','test')]:
    data=copy.deepcopy(base);data[field]=val;run(name,data)
for name,value in [('root_list',[]),('root_null',None),('root_number',3)]:run(name,value)
print(json.dumps(output,ensure_ascii=False,indent=2))
