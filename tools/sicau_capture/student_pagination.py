"""Discover public student-site archives through the observed ASP.NET next button."""
import argparse
import hashlib
import io
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlencode,quote
import pycurl
from bs4 import BeautifulSoup
from multi_capture import Downloader,discover,page_state,append
from capture import decode_html,now

HOSTS={'xggl.sicau.edu.cn','xgxt.sicau.edu.cn'}


def next_form(text,url):
    soup=BeautifulSoup(text,'html.parser')
    button=soup.select_one('#lbnNextPage[href]')
    if not button or 'aspNetDisabled' in button.get('class',[]):return None
    if not re.fullmatch(r"javascript:__doPostBack\('lbnNextPage',''\)",button['href']):
        raise ValueError('unexpected next-page event')
    form=button.find_parent('form')
    if not form:raise ValueError('next button has no form')
    action=urljoin(url,form.get('action') or url)
    if urlsplit(action).hostname!=urlsplit(url).hostname:raise ValueError('form action outside host')
    current=int(soup.select_one('#lblCurrentPage').get_text(strip=True))
    total=int(soup.select_one('#lblPageCount').get_text(strip=True))
    if current>=total:return None
    fields={el['name']:el.get('value','') for el in form.select('input[name]') if el.get('type','').lower()=='hidden'}
    fields.update(__EVENTTARGET='lbnNextPage',__EVENTARGUMENT='')
    return action,fields,current,total


def run(output):
    root=Path(output).resolve()
    out=root/'discovery'/'student-pagination'
    for name in ('pages','tmp','robots'):(out/name).mkdir(parents=True,exist_ok=True)
    state_path=out/'state.json'
    state=json.loads(state_path.read_text('utf8')) if state_path.exists() else {}
    policy=Downloader(out,HOSTS)
    client=pycurl.Curl()
    client.setopt(pycurl.COOKIEFILE,'')
    client.setopt(pycurl.SSL_VERIFYPEER,1)
    client.setopt(pycurl.SSL_VERIFYHOST,2)
    if 'Schannel' in pycurl.version:client.setopt(pycurl.SSL_OPTIONS,8)
    client.setopt(pycurl.USERAGENT,'SicauResearchCapture/0.2 (public-document academic collection)')
    client.setopt(pycurl.TIMEOUT,40)
    client.setopt(pycurl.CONNECTTIMEOUT,10)
    client.setopt(pycurl.ENCODING,'')
    client.setopt(pycurl.MAXFILESIZE_LARGE,5*1024*1024)
    (out/'RUNNING').write_text(now(),encoding='utf8')
    try:
        while not (root/'STOP').exists():
            db=sqlite3.connect(root/'crawl.sqlite')
            rows=db.execute("SELECT url FROM urls WHERE host IN ('xggl.sicau.edu.cn','xgxt.sicau.edu.cn') AND url LIKE '%NewsList%' AND status!='excluded' ORDER BY id").fetchall()
            db.close()
            lists=list(dict.fromkeys(urlsplit(r[0])._replace(scheme='https',query='',fragment='').geturl() for r in rows))
            remaining=[u for u in lists if state.get(u,{}).get('status') not in ('complete','blocked','failed')]
            if not remaining:break
            for seed in remaining:
                if (root/'STOP').exists():break
                host=urlsplit(seed).hostname
                rules=policy.policy(host)
                if rules is False or (rules and not rules.can_fetch('SicauResearchCapture',seed)):
                    state[seed]={'status':'blocked','reason':'robots_unavailable_or_disallow'}
                    continue
                url=seed;fields=None;seen=set();expected=1
                try:
                    while not (root/'STOP').exists():
                        if rules and not rules.can_fetch('SicauResearchCapture',url):raise ValueError('robots_disallow_action')
                        policy.pace(host)
                        buffer=io.BytesIO()
                        client.setopt(pycurl.URL,quote(url,safe=':/?&=%'))
                        client.setopt(pycurl.WRITEDATA,buffer)
                        if fields is None:client.setopt(pycurl.HTTPGET,1)
                        else:client.setopt(pycurl.POSTFIELDS,urlencode(fields))
                        client.perform()
                        code=client.getinfo(pycurl.RESPONSE_CODE)
                        if code!=200:
                            state[seed]={'status':'blocked' if code in (401,403,429) else 'failed','http_status':code,'page':expected};break
                        raw=buffer.getvalue();text=decode_html(raw)
                        evidence=out/'pages'/(hashlib.sha256(seed.encode()).hexdigest()[:16]+f'-{expected:04}.html')
                        evidence.write_bytes(raw)
                        status=page_state(text)
                        soup=BeautifulSoup(text,'html.parser')
                        current=soup.select_one('#lblCurrentPage')
                        if status!='page' or current is None or not current.get_text(strip=True).isdigit():
                            state[seed]={'status':'blocked','reason':status if status!='page' else 'missing_pager','page':expected,'evidence':str(evidence.relative_to(root)).replace('\\','/')};break
                        current=int(current.get_text(strip=True))
                        if current!=expected or current in seen:raise ValueError('pager_did_not_advance')
                        seen.add(current)
                        stem=hashlib.sha256(seed.encode()).hexdigest()[:16]+f'-{current:04}'
                        path=out/'pages'/(stem+'.html');path.write_bytes(raw)
                        links=discover(text,url)
                        record={'url':seed,'request_url':url,'page':current,'fetched_at':now(),'sha256':hashlib.sha256(raw).hexdigest(),'path':str(path.relative_to(root)).replace('\\','/'),'links_found':len(links)}
                        append(out/'pages.jsonl',record)
                        for target,label in links:
                            append(out/'seeds.jsonl',{'url':target,'source':seed,'label':label,'source_capture':record['path'],'page':current})
                        state[seed]={'status':'partial','page':current,'updated_at':now()}
                        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
                        step=next_form(text,url)
                        if step is None:
                            state[seed].update(status='complete',pages=current);break
                        url,fields,_,total=step
                        expected=current+1
                    print(json.dumps({'list':seed,'state':state.get(seed),'time':now()},ensure_ascii=True),flush=True)
                except Exception as ex:
                    state[seed]={'status':'failed','reason':type(ex).__name__+': '+str(ex)[:250],'page':expected}
                state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        client.close()
        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
        (out/'RUNNING').unlink(missing_ok=True)
    print(json.dumps({'finished':now(),'lists':len(state),'complete':sum(v['status']=='complete' for v in state.values()),'stopped':(root/'STOP').exists()}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
