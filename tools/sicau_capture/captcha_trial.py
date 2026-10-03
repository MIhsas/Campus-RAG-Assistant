"""Bounded, resumable OCR trials for the observed public attachment form."""
import argparse
import hashlib
import io
import json
import re
import sqlite3
import time
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit,urljoin,quote
import pycurl
from bs4 import BeautifulSoup
from capture import attachment_name,classify,decode_html,now
from multi_capture import Downloader


def valid_answer(value):
    return isinstance(value,str) and re.fullmatch('[0-9]{4}',value) is not None


def validate_download(status,data,content_type,name):
    if status!=200:return False,'http_'+str(status)
    if classify(data,content_type,name)!='file':return False,'not_a_file'
    if data.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if archive.testzip():return False,'zip_crc_failure'
        except (zipfile.BadZipFile,OSError):return False,'invalid_zip'
    return True,'file_validated'


def eligible_urls(urls,records,max_attempts=1):
    attempts=Counter(r['url'] for r in records)
    successful={r['url'] for r in records if r.get('success')}
    return sorted((u for u in urls if u not in successful and attempts[u]<max_attempts),key=lambda u:attempts[u])


def run(root,limit,hosts,on_record=None,max_attempts=1):
    import ddddocr
    root=Path(root).resolve();out=root/'discovery'/'captcha-ocr-trial'
    for part in ('files','images','responses','tmp','robots'):(out/part).mkdir(parents=True,exist_ok=True)
    statepath=out/'results.json';records=json.loads(statepath.read_text('utf8')) if statepath.exists() else []
    db=sqlite3.connect(root/'crawl.sqlite');db.row_factory=sqlite3.Row
    perhost=[]
    for host in hosts:
        rows={r['url']:dict(r) for r in db.execute("SELECT url,source,label FROM urls WHERE host=? AND status='captcha_required' ORDER BY id",(host,))}
        perhost.append([rows[u] for u in eligible_urls(rows,records,max_attempts)])
    db.close();selected=[]
    for i in range(max([len(x) for x in perhost] or [0])):
        for rows in perhost:
            if i<len(rows):selected.append(rows[i])
            if len(selected)>=limit:break
        if len(selected)>=limit:break
    ocr=ddddocr.DdddOcr(show_ad=False);policies=Downloader(out,set(hosts));clients={};last_request=0
    def fetch(url):
        nonlocal last_request
        host=urlsplit(url).hostname
        policy=policies.policy(host)
        if policy is False or (policy and not policy.can_fetch('SicauResearchCapture',url)):raise RuntimeError('robots_unavailable_or_disallow')
        c=clients.get(host)
        if c is None:
            c=pycurl.Curl();clients[host]=c;c.setopt(c.COOKIEFILE,'');c.setopt(c.SSL_VERIFYPEER,1);c.setopt(c.SSL_VERIFYHOST,2)
            if 'Schannel' in pycurl.version:c.setopt(c.SSL_OPTIONS,8)
            c.setopt(c.TIMEOUT,60);c.setopt(c.CONNECTTIMEOUT,10);c.setopt(c.MAXFILESIZE_LARGE,104857600)
            c.setopt(c.USERAGENT,'SicauResearchCapture/0.3 (public-document academic collection)')
        time.sleep(max(0,1-(time.monotonic()-last_request)));last_request=time.monotonic()
        data=io.BytesIO();headers={}
        def header(line):
            if line.startswith(b'HTTP/'):headers.clear()
            elif b':' in line:
                k,v=line.decode('latin1').split(':',1);headers[k.lower()]=v.strip()
        c.setopt(c.URL,quote(url,safe=':/?&=%'));c.setopt(c.HEADERFUNCTION,header);c.setopt(c.WRITEDATA,data);c.perform()
        return c.getinfo(c.RESPONSE_CODE),data.getvalue(),headers
    consecutive=0;stop_reason='sample_limit_or_no_more_selected_urls'
    try:
        for item in selected:
            if (root/'STOP').exists() or (out/'STOP').exists():stop_reason='stop_requested';break
            url=item['url'];host=urlsplit(url).hostname;key=hashlib.sha256(url.encode()).hexdigest()[:20]
            r={'url':url,'source_page':item['source'],'link_text':item['label'],'host':host,'started_at':now(),'success':False}
            try:
                code,data,headers=fetch(url)
                if code!=200:raise RuntimeError('landing_http_'+str(code))
                soup=BeautifulSoup(decode_html(data),'html.parser')
                (out/'responses'/(key+'-landing.html')).write_bytes(data)
                if not soup.select_one('input#codeValue') or '/system/resource/js/filedownload/createimage.jsp' not in str(soup):raise RuntimeError('unexpected_challenge_form')
                imageurl='https://'+host+'/system/resource/js/filedownload/createimage.jsp?randnum='+str(int(time.time()*1000))
                code,image,headers=fetch(imageurl)
                if code!=200 or not headers.get('content-type','').startswith('image/'):raise RuntimeError('challenge_image_failed')
                imagepath=out/'images'/(key+'.jpg');imagepath.write_bytes(image)
                reading=ocr.classification(image);r.update(image_path=str(imagepath.relative_to(root)),reading=reading)
                if not valid_answer(reading):raise RuntimeError('ocr_not_four_digits')
                target=url+'&codeValue='+reading;code,data,headers=fetch(target)
                for _ in range(3):
                    if code not in (301,302,303,307,308):break
                    target=urljoin(target,headers.get('location',''))
                    if urlsplit(target).hostname!=host:raise RuntimeError('redirect_outside_sample_host')
                    code,data,headers=fetch(target)
                name=attachment_name(target,headers.get('content-disposition',''))
                ok,reason=validate_download(code,data,headers.get('content-type',''),name)
                r.update(http_status=code,success=ok,reason=reason,bytes=len(data))
                if ok:
                    digest=hashlib.sha256(data).hexdigest();path=out/'files'/(digest[:12]+'_'+name);path.write_bytes(data)
                    r.update(sha256=digest,path=str(path.relative_to(root)),name=name)
                else:(out/'responses'/(key+'-rejected.html')).write_bytes(data)
            except Exception as ex:r['reason']=type(ex).__name__+': '+str(ex)[:250]
            r['finished_at']=now();records.append(r)
            checkpoint=statepath.with_suffix('.json.tmp')
            checkpoint.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8');checkpoint.replace(statepath)
            if on_record is not None:on_record(r)
            print(json.dumps(r,ensure_ascii=True),flush=True)
            consecutive=0 if r['success'] else consecutive+1
            if consecutive>=3:stop_reason='three_consecutive_failures';break
    finally:
        for c in clients.values():c.close()
    summary={'finished_at':now(),'attempted':len(records),'successful_downloads':sum(r['success'] for r in records),'unique_file_hashes':len({r['sha256'] for r in records if r['success']}),'by_host':{h:dict(Counter('success' if r['success'] else 'failure' for r in records if r['host']==h)) for h in hosts},'stop_reason':stop_reason,'automatic_retries_per_url':max_attempts-1,'global_minimum_request_interval_seconds':1,'main_collection_modified':on_record is not None}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--limit',type=int,default=30);parser.add_argument('--hosts',nargs='+',default=['cgst.sicau.edu.cn','dky.sicau.edu.cn','dyy.sicau.edu.cn']);args=parser.parse_args()
    if not 1<=args.limit<=100:parser.error('trial limit must be 1..100')
    if any(not h.endswith('.sicau.edu.cn') for h in args.hosts):parser.error('trial hosts must be school domains')
    run(args.root,args.limit,args.hosts)
