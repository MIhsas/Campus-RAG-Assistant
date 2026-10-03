"""Independent public academic-affairs capture; not a RAG importer."""
import argparse
import concurrent.futures as futures
import hashlib
import json
import mimetypes
import re
import subprocess
import threading
import time
from collections import deque, Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, quote, unquote
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

HOST = 'jiaowu.sicau.edu.cn'
EXTS = {'.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.zip','.rar','.7z','.txt','.csv','.rtf','.wps','.et','.dps','.odt','.ods','.ofd','.gz','.tar','.mp4','.mp3','.jpg','.jpeg','.png','.gif'}
ASSETS = {'.css','.js','.ico','.woff','.woff2','.ttf','.svg'}
LOCK = threading.Lock()
LAST = 0.0


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize(base, href):
    href = href.strip().replace('\\', '/')
    p = urlsplit(urljoin(base, href))
    if p.scheme not in ('http', 'https') or p.username or p.password:
        return None
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))


def decode_html(raw):
    match = re.search(br'charset\s*=\s*["\x27]?([\w-]+)', raw[:8000], re.I)
    enc = match.group(1).decode('ascii') if match else 'utf-8'
    if enc.lower() in ('gb2312', 'gbk'):
        enc = 'gb18030'
    try:
        return raw.decode(enc)
    except (UnicodeError, LookupError):
        return raw.decode('gb18030', errors='replace')


def extract_links(text, base):
    soup = BeautifulSoup(text, 'html.parser')
    b = soup.find('base', href=True)
    if b:
        base = urljoin(base, b['href'])
    links = []
    for el in soup.select('a[href],iframe[src],frame[src],embed[src],object[data],area[href],option[value]'):
        raw = el.get('href') or el.get('src') or el.get('data') or el.get('value', '')
        label = el.get_text(' ', strip=True)[:250]
        if el.name == 'option' and not re.search(r'\.(?:asp|html?|pdf|docx?|xlsx?)(?:\?|$)', raw, re.I):
            continue
        if raw.lower().startswith('javascript:'):
            m = re.search(r"(?:open|location(?:\.href)?)\s*(?:\(|=)\s*['\"]([^'\"]+)['\"]", raw)
            raw = m.group(1) if m else ''
        if not raw or raw.startswith('#'):
            continue
        try:
            u = normalize(base, raw)
        except ValueError:
            continue
        if u:
            links.append((u, label))
    for el in soup.select('img[src]'):
        raw = el['src']
        if re.search(r'upload|fujian|/__local/', raw, re.I):
            u = normalize(base, raw)
            if u:
                links.append((u, el.get('alt', '正文图片')))
    return list(dict.fromkeys(links))


def classify(raw, content_type, url):
    head = raw[:1000].lstrip().lower()
    if b'<html' in head or b'<!doctype html' in head or b'<meta' in head or b'<script' in head:
        return 'html'
    if raw.startswith((b'%PDF-', b'PK\x03\x04', bytes.fromhex('D0CF11E0A1B11AE1'), b'Rar!', b'7z\xbc\xaf\x27\x1c', b'\x89PNG', b'\xff\xd8\xff', b'GIF8')):
        return 'file'
    if 'html' in content_type:
        return 'html'
    if Path(urlsplit(url).path).suffix.lower() in EXTS and raw:
        return 'file'
    return 'other'


def attachment_name(url, disposition):
    name = unquote(Path(urlsplit(url).path).name)
    star = re.search(r"filename\*\s*=\s*([^;]+)", disposition, re.I)
    plain = re.search(r'filename\s*=\s*"?([^";]+)', disposition, re.I)
    if star:
        value = star.group(1).strip().strip('"')
        name = unquote(value.split("''",1)[-1])
    elif plain:
        name = plain.group(1).strip()
        try:
            raw = name.encode('latin1')
            try:
                name = raw.decode('utf8')
            except UnicodeError:
                name = raw.decode('gb18030')
        except (UnicodeError, LookupError):
            pass
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .') or 'attachment'
    suffix = Path(name).suffix
    return name[:100] + suffix if len(name)>110 else name


def fetch(url, tmp, robots=None, allowed_hosts=None):
    global LAST
    original = url
    allowed_hosts = allowed_hosts or {HOST}
    # The same site's legacy HTTP links time out; its HTTPS origin is verified live.
    if urlsplit(url).hostname == HOST and url.startswith('http://'):
        url = 'https://' + url[len('http://'):]
    try:
        for hop in range(6):
            if urlsplit(url).hostname not in allowed_hosts:
                return {'url': original, 'status': 'excluded', 'reason': 'external_redirect', 'final_url': url}
            if robots and not robots.can_fetch('SicauResearchCapture', url):
                return {'url': original, 'status': 'blocked', 'reason': 'robots'}
            key = hashlib.sha256(url.encode()).hexdigest()
            target = tmp / (key + '.part')
            header = tmp / (key + '.headers')
            encoded = quote(url, safe=':/?&=%+#;,@!$\x27()*[]~-._')
            with LOCK:
                time.sleep(max(0, .5 - (time.monotonic() - LAST)))
                LAST = time.monotonic()
            result = subprocess.run(['curl.exe','-sS','--compressed','--connect-timeout','10','--max-time','35','--max-filesize','209715200','--retry','1','--retry-delay','2','--proto','=http,https','-A','SicauResearchCapture/0.1 (public-document academic collection)','-D',str(header),'-o',str(target),'-w','%{http_code}',encoded], capture_output=True)
            h = header.read_text('latin1') if header.exists() else ''
            headers = {}
            for line in h.splitlines():
                if ':' in line:
                    k,v = line.split(':',1)
                    headers[k.lower()] = v.strip()
            header.unlink(missing_ok=True)
            if result.returncode:
                target.unlink(missing_ok=True)
                return {'url': original, 'status': 'failed', 'reason': result.stderr.decode('utf8', 'replace')[:400], 'curl_code': result.returncode}
            code = int(result.stdout[-3:] or 0)
            if code in (301,302,303,307,308) and 'location' in headers:
                target.unlink(missing_ok=True)
                url = normalize(url, headers['location'])
                continue
            if code != 200:
                target.unlink(missing_ok=True)
                return {'url': original, 'final_url': url, 'status': 'blocked' if code in (401,403,429) else 'failed', 'http_status': code, 'reason': 'http_status'}
            return {'url': original, 'final_url': url, 'status': 'ok', 'http_status': code, 'content_type': headers.get('content-type',''), 'content_disposition': headers.get('content-disposition',''), 'temp': str(target)}
        return {'url': original, 'status': 'failed', 'reason': 'redirect_limit'}
    except Exception as ex:
        return {'url': original, 'status': 'failed', 'reason': type(ex).__name__ + ': ' + str(ex)[:300]}


def append(path, obj):
    with path.open('a', encoding='utf8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def dump(path, obj):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf8')
    temp.replace(path)


def run(args):
    out = Path(args.output).resolve()
    for sub in ('files','pages','tmp'):
        (out/sub).mkdir(parents=True, exist_ok=True)
    statefile = out/'state.json'
    state = json.loads(statefile.read_text('utf8')) if statefile.exists() else {'queue': [], 'seen': [], 'done': {}, 'objects': {}, 'started': now()}
    queue = deque(state['queue'])
    seen = set(state['seen'])
    done = state['done']
    objects = state['objects']
    def add(u, source='', label=''):
        if not u:
            return
        append(out/'links.jsonl', {'source': source, 'url': u, 'label': label})
        if u in seen:
            return
        seen.add(u)
        p = urlsplit(u)
        reason = None
        if p.hostname != HOST and not (p.hostname and p.hostname.endswith('.sicau.edu.cn') and Path(p.path).suffix.lower() in EXTS):
            reason = 'external_host'
        elif Path(p.path).suffix.lower() in ASSETS:
            reason = 'website_asset'
        elif '/js_kb_cha/' in p.path or p.path.endswith(('/tklist.asp','/jiaoshi_new.asp')):
            reason = 'interactive_timetable_not_document'
        elif re.search(r'login|logout|delete|checkuser', p.path, re.I) and Path(p.path).suffix.lower() not in EXTS:
            reason = 'interactive_system'
        if reason:
            append(out/'excluded.jsonl', {'url':u,'source':source,'reason':reason})
        else:
            queue.append({'url':u,'source':source,'label':label})
    if not statefile.exists():
        add('https://'+HOST+'/')
        add('https://'+HOST+'/sitemap.xml', label='standard sitemap probe')
    if args.seeds:
        for u in Path(args.seeds).read_text('utf8').splitlines():
            if u.strip():
                add(u.strip(), 'search_or_observed_seed', '')
    # Previous conservative filtering also excluded public admission pages.
    for u in list(seen):
        if '/jiaoshi/' in u and u not in done and not any(x['url'] == u for x in queue):
            seen.remove(u)
            add(u, 'scope_review', 'public page retry')
    for u in list(seen):
        p = urlsplit(u)
        if p.hostname != HOST and p.hostname and p.hostname.endswith('.sicau.edu.cn') and Path(p.path).suffix.lower() in EXTS and u not in done and not any(x['url']==u for x in queue):
            seen.remove(u)
            add(u,'scope_review','school-hosted attachment linked by academic-affairs website')
    def priority(entry):
        path = urlsplit(entry['url']).path
        if Path(path).suffix.lower() in EXTS or 'fujian_down.asp' in path:
            return 0
        if 'jihuaprintall' in path:
            return 2
        if 'kbjshi' in path:
            return 3
        return 1
    retained = []
    for entry in queue:
        path = urlsplit(entry['url']).path
        if '/js_kb_cha/' in path or path.endswith(('/tklist.asp','/jiaoshi_new.asp')):
            append(out/'excluded.jsonl',dict(entry,reason='interactive_timetable_not_document'))
        else:
            retained.append(entry)
    queue = deque(sorted(retained,key=priority))
    rr = fetch('https://'+HOST+'/robots.txt', out/'tmp')
    robots = None
    append(out/'robots.jsonl', {k:v for k,v in rr.items() if k != 'temp'})
    if rr['status'] == 'ok':
        rb = Path(rr['temp']).read_bytes()
        (out/'robots.txt').write_bytes(rb)
        Path(rr['temp']).unlink()
        if classify(rb,rr['content_type'],rr['url']) != 'html':
            robots = RobotFileParser()
            robots.parse(rb.decode('utf8','replace').splitlines())
            for s in robots.site_maps() or []:
                add(s, rr['url'], 'sitemap')
    elif rr.get('http_status') != 404:
        raise RuntimeError('robots unavailable: '+str(rr))
    robots_by_host = {HOST:robots}
    def scoped_fetch(url):
        host = urlsplit(url).hostname
        if host not in robots_by_host:
            # New hosts are discovered from direct school-hosted attachment links only.
            rb_result = fetch('https://'+host+'/robots.txt',out/'tmp',allowed_hosts={host})
            append(out/'robots.jsonl',{k:v for k,v in rb_result.items() if k!='temp'})
            if rb_result.get('http_status')==404:
                robots_by_host[host] = None
            elif rb_result['status']=='ok':
                rb_path = Path(rb_result['temp'])
                rb_raw = rb_path.read_bytes()
                rb_path.unlink()
                if classify(rb_raw,rb_result['content_type'],rb_result['url'])=='html':
                    return {'url':url,'status':'blocked','reason':'robots_unrecognized_html'}
                rp = RobotFileParser()
                rp.parse(rb_raw.decode('utf8','replace').splitlines())
                robots_by_host[host] = rp
            else:
                return {'url':url,'status':'blocked','reason':'robots_unavailable'}
        return fetch(url,out/'tmp',robots_by_host[host],allowed_hosts={HOST,host})
    count = 0
    with futures.ThreadPoolExecutor(max_workers=3) as pool:
        inflight = {}
        while (queue or inflight) and count < args.limit:
            while queue and len(inflight) < 3 and count + len(inflight) < args.limit:
                entry = queue.popleft()
                # Resolve robots before concurrent downloads to avoid shared probe files.
                host = urlsplit(entry['url']).hostname
                if host not in robots_by_host:
                    result = scoped_fetch(entry['url'])
                    completed = futures.Future()
                    completed.set_result(result)
                    inflight[completed] = entry
                else:
                    inflight[pool.submit(scoped_fetch,entry['url'])] = entry
            ready, _ = futures.wait(inflight, return_when=futures.FIRST_COMPLETED)
            jobs = [(inflight.pop(job),job) for job in ready]
            stop = False
            for entry,job in jobs:
                r = job.result()
                r.update({'source_page':entry['source'],'link_text':entry['label'],'fetched_at':now()})
                u = entry['url']
                count += 1
                if r['status'] != 'ok':
                    done[u] = r['status']
                    append(out/'failed.jsonl', r)
                    if r.get('http_status') in (429,503):
                        stop = True
                    continue
                temp = Path(r.pop('temp'))
                raw = temp.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                r.update({'sha256':digest,'bytes':len(raw)})
                kind = classify(raw,r['content_type'],r['final_url'])
                if kind == 'html':
                    txt = decode_html(raw)
                    soup = BeautifulSoup(txt,'html.parser')
                    r['title'] = soup.title.get_text(' ',strip=True) if soup.title else entry['label']
                    path = 'pages/'+hashlib.sha256(u.encode()).hexdigest()[:20]+'.html'
                    temp.replace(out/path)
                    r['path'] = path
                    for node in soup(['script','style','nav']):
                        node.decompose()
                    plain = soup.get_text('\n',strip=True)
                    (out/Path(path).with_suffix('.txt')).write_text(plain,encoding='utf8')
                    r['date_candidates'] = list(dict.fromkeys(re.findall(r'20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2}日?',plain)))[:20]
                    links = extract_links(txt,r['final_url'])
                    r['links_found'] = len(links)
                    r['expected_attachment'] = Path(urlsplit(u).path).suffix.lower() in EXTS
                    append(out/'pages.jsonl',r)
                    if urlsplit(r['final_url']).hostname == HOST:
                        for target,label in links:
                            add(target,r['final_url'],label)
                    # Download newly found attachments before further page traversal.
                    queue = deque(sorted(queue,key=priority))
                    done[u] = 'page'
                    if r['expected_attachment']:
                        append(out/'failed.jsonl', {'url':u,'source_page':entry['source'],'status':'failed','reason':'html_instead_of_attachment','saved_page':path})
                elif kind == 'file':
                    name = attachment_name(r['final_url'],r['content_disposition'])
                    if digest in objects:
                        temp.unlink()
                        path = objects[digest]
                        r['duplicate_content'] = True
                    else:
                        path = 'files/'+digest[:12]+'_'+name
                        temp.replace(out/path)
                        objects[digest] = path
                    r['path'] = path
                    r['version_status'] = 'unreviewed'
                    append(out/'manifest.jsonl',r)
                    done[u] = 'file'
                else:
                    if 'xml' in r['content_type'] or u.endswith('.xml'):
                        for loc in BeautifulSoup(raw,'xml').find_all('loc'):
                            add(normalize(r['final_url'],loc.get_text()),r['final_url'],'sitemap')
                    temp.unlink()
                    done[u] = 'other'
                    append(out/'excluded.jsonl',dict(r,reason='unrecognized_content'))
            state.update({'queue':list(inflight.values())+list(queue),'seen':list(seen),'done':done,'objects':objects,'updated':now()})
            dump(statefile,state)
            if count % 30 < 3 or not queue or stop:
                print(json.dumps({'processed':len(done),'pending':len(queue),'unique_files':len(objects),'statuses':dict(Counter(done.values()))}),flush=True)
            if stop:
                print('Stopped for server backoff',flush=True)
                break
    print(json.dumps({'finished':now(),'pending':len(queue),'unique_files':len(objects),'statuses':dict(Counter(done.values()))}),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    p.add_argument('--limit',type=int,default=10000)
    p.add_argument('--seeds')
    run(p.parse_args())
