"""Multi-site public attachment collection with a durable SQLite queue."""
import argparse
import concurrent.futures as futures
import hashlib
import json
import re
import sqlite3
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urljoin, quote
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from capture import normalize, decode_html, classify, attachment_name, now
from cnzx_adapter import is_api, parse_api
try:
    import pycurl
except ImportError:
    pycurl=None

DOCS = {'.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.zip','.rar','.7z','.txt','.csv','.rtf','.wps','.et','.dps','.odt','.ods','.ofd','.gz','.tar'}
IMAGES = {'.png','.jpg','.jpeg','.gif','.bmp','.tif','.tiff'}
PAGES = {'','.htm','.html','.asp','.aspx','.jsp','.php'}
# Direct attachment host published by the official cnzx article API (53099).
ATTACHMENT_HOSTS = {'web.cnzx.info'}


def candidate(url, hosts):
    p = urlsplit(url)
    ext = Path(p.path).suffix.lower()
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        return 'excluded'
    if is_api(url):
        return 'api'
    school = p.hostname.endswith('.sicau.edu.cn') or p.hostname in hosts or p.hostname in ATTACHMENT_HOSTS
    if school and (ext in DOCS or re.search(r'/(?:download|fujian_down)\.(?:jsp|aspx?|php)$',p.path,re.I)):
        return 'file'
    if school and ext in IMAGES:
        return 'image'
    if p.hostname not in hosts or ext not in PAGES:
        return 'excluded'
    if re.search(r'login|logout|signin|signout|delete|/admin/|/cas/|/system/resource/|/system/_owners/',p.path,re.I):
        return 'interactive'
    return 'page'


def discover(text, base):
    soup = BeautifulSoup(text,'html.parser')
    base_el = soup.find('base',href=True)
    if base_el:
        base = urljoin(base,base_el['href'])
    result=[]
    # Deliberately exclude embedded news photos, logos, scripts, CSS and fonts.
    for el in soup.select('a[href],area[href],iframe[src],frame[src],embed[src],object[data],option[value]'):
        val=el.get('href') or el.get('src') or el.get('data') or el.get('value','')
        if el.name=='option' and not re.search(r'\.(htm|html|aspx?|jsp|php|pdf)(\?|$)',val,re.I):
            continue
        if val.lower().startswith('javascript:'):
            m=re.search(r"(?:open|location(?:\.href)?)\s*(?:\(|=)\s*['\"]([^'\"]+)['\"]",val)
            val=m.group(1) if m else ''
        if not val or val.startswith('#'):
            continue
        try:
            url=normalize(base,val)
        except ValueError:
            continue
        if url:
            result.append((url,el.get_text(' ',strip=True)[:300]))
    for script in soup.select('script:not([src])'):
        for raw in re.findall(r"(?:window\.)?location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]",script.get_text()):
            u=normalize(base,raw)
            if u:
                result.append((u,'script_redirect'))
    return list(dict.fromkeys(result))


def page_state(text):
    if '请输入验证码下载附件' in text or '请输入验证码后下载' in text:
        return 'captcha_required'
    if ('该项信息查询未授权' in text and 'window.history.go(-1)' in text) or re.search(r'<title[^>]*>\s*(?:用户登录|统一身份认证|登录|Login)',text,re.I):
        return 'login_required'
    if re.search(r'<title[^>]*>[^<]*(?:访问验证|访问受限|安全验证|人机验证)',text,re.I):
        return 'access_challenge'
    if re.search(r'<title[^>]*>\s*(?:404|页面不存在|找不到网页)',text,re.I):
        return 'soft_404'
    return 'page'


def append(path,data):
    with path.open('a',encoding='utf8') as f:
        f.write(json.dumps(data,ensure_ascii=False)+'\n')


class Downloader:
    def __init__(self,out,hosts):
        self.out=out
        self.hosts=set(hosts)
        self.policies={}
        self.gates={}
        self.last={}
        self.guard=threading.Lock()
        self.log_lock=threading.Lock()
        self.global_gate=threading.Lock()
        self.global_last=0
        self.local=threading.local()

    def pace(self,host):
        with self.guard:
            gate=self.gates.setdefault(host,threading.Lock())
        with gate:
            time.sleep(max(0,.8-(time.monotonic()-self.last.get(host,0))))
            self.last[host]=time.monotonic()
        with self.global_gate:
            time.sleep(max(0,.2-(time.monotonic()-self.global_last)))
            self.global_last=time.monotonic()

    def raw(self,url):
        self.pace(urlsplit(url).hostname)
        key=hashlib.sha256(url.encode()).hexdigest()
        target=self.out/'tmp'/(key+'.part')
        header=self.out/'tmp'/(key+'.hdr')
        request_url=quote(url,safe=':/?&=%+#;,@!$\x27()*[]~-._')
        if pycurl:
            client=getattr(self.local,'client',None)
            if client is None:
                client=pycurl.Curl()
                self.local.client=client
            client.reset()
            headers={}
            def receive_header(line):
                if line.startswith(b'HTTP/'):
                    headers.clear()
                elif b':' in line:
                    k,v=line.decode('latin1').split(':',1)
                    headers[k.lower()]=v.strip()
            written=0
            try:
                with target.open('wb') as stream:
                    def receive_body(data):
                        nonlocal written
                        written+=len(data)
                        if written>209715200:
                            return 0
                        return stream.write(data)
                    client.setopt(pycurl.URL,request_url)
                    client.setopt(pycurl.USERAGENT,'SicauResearchCapture/0.2 (public-document academic collection)')
                    client.setopt(pycurl.ENCODING,'')
                    client.setopt(pycurl.CONNECTTIMEOUT,10)
                    client.setopt(pycurl.TIMEOUT,70)
                    client.setopt(pycurl.MAXFILESIZE_LARGE,209715200)
                    client.setopt(pycurl.PROTOCOLS,pycurl.PROTO_HTTP|pycurl.PROTO_HTTPS)
                    client.setopt(pycurl.SSL_VERIFYPEER,1)
                    client.setopt(pycurl.SSL_VERIFYHOST,2)
                    # CURLSSLOPT_REVOKE_BEST_EFFORT = 1 << 3 (libcurl >=7.70).
                    # This PycURL build does not export the named macro.
                    if 'Schannel' in pycurl.version:
                        client.setopt(pycurl.SSL_OPTIONS,8)
                    client.setopt(pycurl.HEADERFUNCTION,receive_header)
                    client.setopt(pycurl.WRITEFUNCTION,receive_body)
                    client.perform()
                return {'status':'response','http_status':client.getinfo(pycurl.RESPONSE_CODE),'headers':headers,'temp':str(target)}
            except pycurl.error as ex:
                target.unlink(missing_ok=True)
                return {'status':'failed','error':str(ex)[:400],'curl_code':ex.args[0]}
        r=subprocess.run(['curl.exe','-sS','--ssl-revoke-best-effort','--compressed','--connect-timeout','10','--max-time','70','--max-filesize','209715200','--proto','=http,https','-A','SicauResearchCapture/0.2 (public-document academic collection)','-D',str(header),'-o',str(target),'-w','%{http_code}',request_url],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        headers={}
        if header.exists():
            for line in header.read_text('latin1').splitlines():
                if ':' in line:
                    k,v=line.split(':',1)
                    headers[k.lower()]=v.strip()
            header.unlink()
        if r.returncode:
            target.unlink(missing_ok=True)
            return {'status':'failed','error':r.stderr.decode('utf8','replace')[:400],'curl_code':r.returncode}
        return {'status':'response','http_status':int(r.stdout[-3:] or 0),'headers':headers,'temp':str(target)}

    def policy(self,host):
        if host in self.policies:
            return self.policies[host]
        url='https://'+host+'/robots.txt'
        r=self.raw(url)
        policy=None
        decision='unavailable'
        if r.get('http_status')==404:
            decision='not_found'
        elif r.get('http_status')==200:
            raw=Path(r['temp']).read_bytes()
            path=self.out/'robots'/(host+'.txt')
            path.write_bytes(raw)
            policy=RobotFileParser()
            policy.parse(raw.decode('utf8','replace').splitlines())
            decision='parsed'
        elif r.get('http_status') in (301,302,307,308):
            # Do not silently infer robots policy from a login/home redirect.
            decision='robots_redirect_unresolved'
            policy=False
        else:
            policy=False
        if r.get('temp'):
            Path(r['temp']).unlink(missing_ok=True)
        self.policies[host]=policy
        with self.log_lock:
            append(self.out/'robots_log.jsonl',{'host':host,'decision':decision,'http_status':r.get('http_status'),'error':r.get('error'),'time':now()})
        return policy

    def __call__(self,url):
        initial=url
        if url.startswith('http://') and urlsplit(url).hostname in self.hosts:
            url='https://'+url[len('http://'):]
        for hop in range(6):
            p=urlsplit(url)
            if p.hostname not in self.hosts and not (p.hostname and (p.hostname.endswith('.sicau.edu.cn') or p.hostname in ATTACHMENT_HOSTS) and candidate(url,self.hosts) in ('file','image')):
                return {'status':'excluded','reason':'redirect_outside_scope','final_url':url}
            policy=self.policy(p.hostname)
            if policy is False:
                return {'status':'blocked','reason':'robots_unavailable','final_url':url}
            if policy and not policy.can_fetch('SicauResearchCapture',url):
                return {'status':'blocked','reason':'robots_disallow','final_url':url}
            r=self.raw(url)
            if r['status']=='failed':
                return dict(r,final_url=url)
            code=r['http_status']
            if code in (301,302,303,307,308) and 'location' in r['headers']:
                Path(r['temp']).unlink(missing_ok=True)
                url=normalize(url,r['headers']['location'])
                continue
            if code!=200:
                Path(r['temp']).unlink(missing_ok=True)
                return {'status':'blocked' if code in (401,403,429) else 'failed','http_status':code,'reason':'http_status','final_url':url}
            return {'status':'ok','final_url':url,'http_status':code,'temp':r['temp'],'content_type':r['headers'].get('content-type',''),'content_disposition':r['headers'].get('content-disposition','')}
        return {'status':'failed','reason':'redirect_limit','final_url':url}


def connect(out):
    db=sqlite3.connect(out/'crawl.sqlite')
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS urls(id INTEGER PRIMARY KEY,url TEXT UNIQUE,host TEXT,site TEXT,status TEXT,priority INTEGER,depth INTEGER,label TEXT,source TEXT,attempts INTEGER DEFAULT 0,result TEXT);
    CREATE INDEX IF NOT EXISTS queue ON urls(status,priority,id);
    CREATE INDEX IF NOT EXISTS host_queue ON urls(host,status,priority,id);
    CREATE TABLE IF NOT EXISTS edges(source TEXT,url TEXT,label TEXT,UNIQUE(source,url,label));
    CREATE TABLE IF NOT EXISTS objects(sha256 TEXT PRIMARY KEY,path TEXT,bytes INTEGER,name TEXT);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
    ''')
    return db


def next_candidates(db):
    # One best candidate per host: a large archive cannot hide another site.
    hosts=[r[0] for r in db.execute("SELECT DISTINCT host FROM urls WHERE status='queued'")]
    rows=[db.execute("SELECT * FROM urls WHERE status='queued' AND host=? ORDER BY priority,id LIMIT 1",(host,)).fetchone() for host in hosts]
    return sorted(rows,key=lambda r:(r['priority'],r['id']))


def run(args):
    out=Path(args.output).resolve()
    if (out/'STOP').exists():
        print('STOP exists: collection stays stopped. Remove it only when resuming is requested.',flush=True)
        return
    for part in ('files','pages','tmp','robots'):
        (out/part).mkdir(parents=True,exist_ok=True)
    config=json.loads(Path(args.sites).read_text('utf8'))
    sites={s['host']:s for s in config['sites']}
    hosts=set(sites)
    db=connect(out)
    db.execute("UPDATE urls SET status='queued' WHERE status='fetching'")
    db.execute("INSERT OR IGNORE INTO meta VALUES('started',?)",(now(),))
    def add(url,source='',label='',depth=0,site=None):
        if not url:
            return
        try:
            url=normalize(source or url,url)
            p=urlsplit(url)
            if p.hostname=='www.cnzx.info' and re.fullmatch(r'/article/(?:\d+/)*\d+',p.path):
                url='https://www.cnzx.info/Net/interface/GetXinWenXiangQing.ashx?XinWenID='+p.path.split('/')[-1]
                p=urlsplit(url)
        except (ValueError,TypeError):
            return
        kind=candidate(url,hosts)
        db.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?)',(source,url,label))
        owner=p.hostname if p.hostname in hosts else (site or urlsplit(source).hostname or 'external')
        if kind in ('excluded','interactive'):
            status='excluded'
        else:
            status='queued'
        priority=0 if kind in ('file','image') else 10+min(depth,30)
        if kind=='page' and re.search('制度|办法|下载|表格|教学|学生|奖|资助|办事|培养|通知',label):
            priority=5+min(depth,30)
        if depth==0:
            priority=-10
        db.execute('INSERT OR IGNORE INTO urls(url,host,site,status,priority,depth,label,source) VALUES(?,?,?,?,?,?,?,?)',(url,p.hostname,owner,status,priority,depth,label,source))
    for host,site in sites.items():
        add(site['url'],site['source'],site['name'],0,host)
    if 'www.cnzx.info' in hosts:
        add('https://www.cnzx.info/moren.json','https://www.cnzx.info/','公开栏目配置',0,'www.cnzx.info')
    db.execute('UPDATE urls SET priority=-10 WHERE depth=0')
    for attachment_host in ATTACHMENT_HOSTS:
        for row in db.execute("SELECT id,url FROM urls WHERE host=? AND status='excluded'",(attachment_host,)).fetchall():
            if candidate(row['url'],hosts) in ('file','image'):
                db.execute("UPDATE urls SET status='queued',priority=0 WHERE id=?",(row['id'],))
    if args.retry:
        db.execute("UPDATE urls SET status='queued' WHERE status='failed' AND attempts<2")
    db.commit()
    down=Downloader(out,hosts)
    count=0
    last_progress=0
    seed_position=0
    seed_file=out/'discovery'/'student-pagination'/'seeds.jsonl'
    def import_seeds():
        nonlocal seed_position
        if not seed_file.exists():return
        with seed_file.open('rb') as stream:
            stream.seek(seed_position)
            while True:
                start=stream.tell()
                line=stream.readline()
                if not line or not line.endswith(b'\n'):break
                item=json.loads(line.decode('utf8'))
                add(item['url'],item['source'],item.get('label',''),2)
                seed_position=stream.tell()
        db.commit()
    import_seeds()
    last_seed_import=time.monotonic()
    cooldown={}
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        active={}
        stop_announced=False
        while count<args.max_urls or active:
            stopping=(out/'STOP').exists() or count>=args.max_urls
            if not stopping and time.monotonic()-last_seed_import>=30:
                import_seeds()
                last_seed_import=time.monotonic()
            active_hosts={entry['host'] for entry in active.values()}
            candidates=[] if stopping else next_candidates(db)
            for entry in candidates:
                if len(active)>=args.workers or count+len(active)>=args.max_urls:
                    break
                host=entry['host']
                if host in active_hosts or cooldown.get(host,0)>time.time():
                    continue
                db.execute("UPDATE urls SET status='fetching',attempts=attempts+1 WHERE id=?",(entry['id'],))
                active[pool.submit(down,entry['url'])]=entry
                active_hosts.add(host)
            db.commit()
            if not active:
                if stopping:
                    break
                if not candidates:
                    import_seeds()
                    if db.execute("SELECT 1 FROM urls WHERE status='queued' LIMIT 1").fetchone():continue
                    if (seed_file.parent/'RUNNING').exists():
                        time.sleep(2)
                        continue
                    break
                future_times=[v for v in cooldown.values() if v>time.time()]
                if future_times:
                    time.sleep(min(5,max(0,min(future_times)-time.time())))
                    continue
                break
            ready,_=futures.wait(active,timeout=5,return_when=futures.FIRST_COMPLETED)
            for job in ready:
                entry=active.pop(job)
                try:
                    r=job.result()
                except Exception as ex:
                    r={'status':'failed','reason':type(ex).__name__+': '+str(ex)[:300]}
                r.update({'url':entry['url'],'source_page':entry['source'],'link_text':entry['label'],'site':entry['site'],'fetched_at':now()})
                count+=1
                status=r['status']
                if status=='ok':
                    temp=Path(r.pop('temp'))
                    raw=temp.read_bytes()
                    digest=hashlib.sha256(raw).hexdigest()
                    r.update({'sha256':digest,'bytes':len(raw)})
                    name=attachment_name(r['final_url'],r.get('content_disposition',''))
                    kind=classify(raw,r['content_type'],name if r.get('content_disposition') else r['final_url'])
                    if is_api(r['final_url']):
                        folder=out/'pages'/entry['site']
                        folder.mkdir(exist_ok=True)
                        path=str((folder/(hashlib.sha256(entry['url'].encode()).hexdigest()[:20]+'.json')).relative_to(out)).replace('\\','/')
                        temp.replace(out/path)
                        try:
                            data=json.loads(raw.decode('utf-8-sig'))
                            status,title,body,links=parse_api(data,r['final_url'])
                            r.update({'status':status,'title':title,'path':path,'links_found':len(links)})
                            (out/Path(path).with_suffix('.txt')).write_text(BeautifulSoup(body,'html.parser').get_text('\n',strip=True) or json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
                            for u,label in links:
                                add(u,r['final_url'],label,entry['depth']+1,entry['site'])
                        except (ValueError,TypeError,KeyError) as ex:
                            status='api_error'
                            r.update({'status':status,'path':path,'reason':str(ex)[:200]})
                        append(out/'pages.jsonl',r)
                    elif kind=='file':
                        obj=db.execute('SELECT path FROM objects WHERE sha256=?',(digest,)).fetchone()
                        if obj:
                            path=obj['path']
                            temp.unlink()
                            r['duplicate_content']=True
                        else:
                            site_dir=out/'files'/entry['site']
                            site_dir.mkdir(exist_ok=True)
                            path=str((site_dir/(digest[:12]+'_'+name)).relative_to(out)).replace('\\','/')
                            temp.replace(out/path)
                            db.execute('INSERT INTO objects VALUES(?,?,?,?)',(digest,path,len(raw),name))
                        r.update({'status':'file','path':path,'version_status':'unreviewed'})
                        append(out/'manifest.jsonl',r)
                        status='file'
                    elif kind=='html':
                        text=decode_html(raw)
                        status=page_state(text)
                        soup=BeautifulSoup(text,'html.parser')
                        title=soup.title.get_text(' ',strip=True) if soup.title else entry['label']
                        heading=soup.select_one('h1')
                        if heading and len(heading.get_text(strip=True))>4:
                            title=heading.get_text(' ',strip=True)
                        folder=out/'pages'/entry['site']
                        folder.mkdir(exist_ok=True)
                        path=str((folder/(hashlib.sha256(entry['url'].encode()).hexdigest()[:20]+'.html')).relative_to(out)).replace('\\','/')
                        temp.replace(out/path)
                        links=discover(text,r['final_url']) if status=='page' else []
                        r.update({'status':status,'title':title,'path':path,'links_found':len(links)})
                        for node in soup(['script','style']):
                            node.decompose()
                        plain=soup.get_text('\n',strip=True)
                        (out/Path(path).with_suffix('.txt')).write_text(plain,encoding='utf8')
                        if candidate(entry['url'],hosts) in ('file','image') and status=='page':
                            status='attachment_landing'
                            r['status']=status
                        append(out/'pages.jsonl',r)
                        if status in ('page','attachment_landing') and urlsplit(r['final_url']).hostname in hosts:
                            for u,label in links:
                                add(u,r['final_url'],label,entry['depth']+1,entry['site'])
                    else:
                        temp.unlink()
                        status='unrecognized'
                        r['status']=status
                        append(out/'failed.jsonl',r)
                else:
                    append(out/'failed.jsonl',r)
                    if r.get('reason')=='robots_unavailable':
                        db.execute("UPDATE urls SET status='blocked_host',result=? WHERE host=? AND status='queued'",(json.dumps(r,ensure_ascii=False),entry['host']))
                    if r.get('http_status') in (429,503):
                        cooldown[entry['host']]=time.time()+60
                db.execute('UPDATE urls SET status=?,result=? WHERE id=?',(status,json.dumps(r,ensure_ascii=False),entry['id']))
            db.execute("INSERT OR REPLACE INTO meta VALUES('updated',?)",(now(),))
            db.commit()
            if time.monotonic()-last_progress>30:
                stats=dict(db.execute('SELECT status,count(*) FROM urls GROUP BY status').fetchall())
                obj=db.execute('SELECT count(*),coalesce(sum(bytes),0) FROM objects').fetchone()
                print(json.dumps({'time':now(),'states':stats,'unique_files':obj[0],'MiB':round(obj[1]/1048576,2),'inflight':len(active)}),flush=True)
                last_progress=time.monotonic()
            if (out/'STOP').exists() and not stop_announced:
                print('STOP requested; draining active requests and preserving the remaining queue',flush=True)
                stop_announced=True
    print(json.dumps({'finished':now(),'states':dict(db.execute('SELECT status,count(*) FROM urls GROUP BY status').fetchall()),'unique_files':db.execute('SELECT count(*) FROM objects').fetchone()[0]}),flush=True)
    db.close()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--sites',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--workers',type=int,default=12)
    p.add_argument('--max-urls',type=int,default=200000)
    p.add_argument('--retry',action='store_true')
    run(p.parse_args())
