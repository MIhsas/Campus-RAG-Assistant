"""Independent synthetic acceptance probe; does not modify product files."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from campus_assistant.corpus.chunk import chunk_documents

sys.stdout.reconfigure(encoding='utf-8')

root = Path(__file__).resolve().parents[3]
doc = {'document_id':'review','parser_version':'1.0','metadata':{'sha256':'a'*64,'scope':{'campus':[]}},'warnings':[], 'blocks':[
    {'block_id':'b1','ordinal':1,'kind':'paragraph','text':'甲乙丙丁','locator':{'type':'lines','line_start':1,'line_end':1}}]}
before = copy.deepcopy(doc)
chunks = chunk_documents([doc],max_chars=2)
chunks[0]['metadata']['scope']['campus'].append('合成校区')
chunks[0]['locator']['line_start'] = 99
print(json.dumps({'sibling_metadata_changed':chunks[1]['metadata']['scope']['campus'], 'input_locator_changed':doc['blocks'][0]['locator']['line_start'], 'input_unchanged':doc == before},ensure_ascii=False))
order_doc = copy.deepcopy(before)
order_doc['blocks'] = [dict(before['blocks'][0], block_id='later',ordinal=2,text='后'),dict(before['blocks'][0],block_id='earlier',ordinal=1,text='前')]
print(json.dumps({'ordinal_order':[c['text'] for c in chunk_documents([order_doc])]},ensure_ascii=False))
for limit in ['500','0','10001']:
    p = subprocess.run([sys.executable,'-m','campus_assistant.corpus.chunk','--manifest',str(root/'step2_code/backend/examples/parse-corpus/manifest.json'),'--corpus-root',str(root/'step2_code/backend/examples/parse-corpus'),'--max-chars',limit],capture_output=True,encoding='utf-8')
    data = json.loads(p.stdout) if p.stdout else {}
    print(json.dumps({'max_chars':limit,'exit':p.returncode,'stdout_nonempty':bool(p.stdout),'valid':data.get('valid'),'chunk_count':data.get('chunk_count'),'error_codes':[e['code'] for e in data.get('errors',[])]}))
