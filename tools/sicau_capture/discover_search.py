"""Read-only POST search discovery from the site's observed public form."""
import hashlib
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_from_bytes
from bs4 import BeautifulSoup
from capture import decode_html, extract_links, append, now

OUT = Path('data/collections/sicau-jiaowu-2026-09-29')
URL = 'https://jiaowu.sicau.edu.cn/web/web/web/gwmore.asp'
folder = OUT/'search_pages'
folder.mkdir(exist_ok=True)
home = folder/'form.html'
subprocess.run(['curl.exe','-sS','--max-time','30',URL,'-o',str(home)],check=True)
soup = BeautifulSoup(decode_html(home.read_bytes()),'html.parser')
categories = [o.get('value') for o in soup.select('select[name=welcome_1] option') if o.get('value')]
queries = [(c,'') for c in categories] + [('',str(y)) for y in range(2000,2027)]
seeds = set()
for category, keyword in queries:
    fields = {'welcome_1':category,'welcome_2':keyword,'shou1':''}
    body = '&'.join(k+'='+quote_from_bytes(v.encode('gb18030')) for k,v in fields.items())
    key = hashlib.sha256(body.encode()).hexdigest()[:16]
    path = folder/(key+'.html')
    if path.exists():
        raw = path.read_bytes()
        status = 'cached'
    else:
        time.sleep(1)
        r = subprocess.run(['curl.exe','-sS','--connect-timeout','10','--max-time','30','-A','SicauResearchCapture/0.1','--data',body,URL,'-o',str(path),'-w','%{http_code}'],capture_output=True)
        status = r.stdout.decode('ascii','replace')
        if r.returncode or status != '200':
            append(OUT/'search_log.jsonl',{'category':category,'keyword':keyword,'status':status,'error':r.stderr.decode('utf8','replace'),'time':now()})
            continue
        raw = path.read_bytes()
    links = extract_links(decode_html(raw),URL)
    articles = {u for u,label in links if 'gwshenshow' in u}
    seeds.update(articles)
    append(OUT/'search_log.jsonl',{'category':category,'keyword':keyword,'status':status,'articles':len(articles),'possibly_truncated':len(articles)>=50,'path':str(path.relative_to(OUT)),'time':now()})
    with (OUT/'search_discovered_links.jsonl').open('a',encoding='utf8') as f:
        for u,label in links:
            if u in articles:
                f.write(json.dumps({'url':u,'label':label,'search_category':category,'search_keyword':keyword,'source_page':URL,'saved_search':str(path.relative_to(OUT))},ensure_ascii=False)+'\n')
    (OUT/'search_seeds.txt').write_text('\n'.join(sorted(seeds)),encoding='utf8')
    print(json.dumps({'query':keyword or category,'articles':len(articles),'unique_seeds':len(seeds)},ensure_ascii=True),flush=True)
