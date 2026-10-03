"""Continue discovered public attachment requests with durable per-URL checkpoints."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from captcha_trial import run,validate_download,eligible_urls
from capture import now
from multi_report import generate


def save_json(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    tmp.replace(path)


def load_hosts(root,requested=None):
    path=Path(root)/'collection_scope.json'
    allowed=json.loads(path.read_text('utf8'))['allowed_hosts'] if path.exists() else None
    hosts=requested if requested is not None else allowed
    if hosts is not None:
        if not hosts or any(not re.fullmatch(r'[a-z0-9-]+\.sicau\.edu\.cn',h) for h in hosts):
            raise ValueError('scope_requires_explicit_school_hosts')
        if allowed is not None and not set(hosts)<=set(allowed):raise ValueError('requested_hosts_outside_saved_scope')
        return sorted(set(hosts))
    return None


def remaining_urls(db,records,hosts,max_attempts=1):
    query="SELECT url FROM urls WHERE status='captcha_required'"
    params=()
    if hosts is not None:
        query+=' AND host IN ('+','.join('?' for _ in hosts)+')';params=hosts
    query+=' ORDER BY rowid'
    return eligible_urls([u for u, in db.execute(query,params)],records,max_attempts)


def unresolved_record(host,url,status,result,attempt=None):
    data=json.loads(result or '{}');attempt=attempt or {}
    return {'host':host,'url':url,'status':status,'reason':attempt.get('reason') or data.get('reason'),
            'http_status':attempt.get('http_status',data.get('http_status')),
            'source_page':data.get('source_page'),'link_text':data.get('link_text')}


def import_record(root,record):
    if not record.get('success'):return False
    root=Path(root).resolve();source=(root/record['path']).resolve()
    if not source.is_relative_to(root):raise ValueError('path_outside_collection')
    data=source.read_bytes()
    if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
        raise ValueError('download_hash_or_size_mismatch')
    if not validate_download(200,data,'application/octet-stream',record['name'])[0]:
        raise ValueError('invalid_download_content')
    with closing(sqlite3.connect(root/'crawl.sqlite',timeout=30)) as db, db:
        row=db.execute('SELECT site,status FROM urls WHERE url=?',(record['url'],)).fetchone()
        if row is None:raise ValueError('unknown_source_url')
        if row[1]=='file':return False
        existing=db.execute('SELECT path FROM objects WHERE sha256=?',(record['sha256'],)).fetchone()
        if existing:relative=existing[0]
        else:
            name=Path(record['name']).name
            target=root/'files'/row[0]/(record['sha256'][:12]+'_'+name)
            target.parent.mkdir(parents=True,exist_ok=True)
            if source!=target:
                temp=target.with_suffix(target.suffix+'.part');shutil.copyfile(source,temp);temp.replace(target)
            relative=target.relative_to(root).as_posix()
            db.execute('INSERT INTO objects VALUES(?,?,?,?)',(record['sha256'],relative,record['bytes'],name))
        result={**record,'status':'file','path':relative,'site':row[0],
                'fetched_at':record.get('finished_at'),'version_status':'unreviewed',
                'capture_method':'public_attachment_form_ocr','duplicate_content':bool(existing)}
        db.execute("UPDATE urls SET status='file',result=? WHERE url=?",(json.dumps(result,ensure_ascii=False),record['url']))
    with (root/'manifest.jsonl').open('a',encoding='utf8') as stream:
        stream.write(json.dumps(result,ensure_ascii=False)+'\n')
    return True


def collect(root,batch_size=40,hosts=None,max_attempts=None):
    import msvcrt
    root=Path(root).resolve();trial=root/'discovery'/'captcha-ocr-trial'
    scope=load_hosts(root,hosts)
    config=json.loads((root/'collection_scope.json').read_text('utf8')) if (root/'collection_scope.json').exists() else {}
    max_attempts=max_attempts if max_attempts is not None else config.get('max_attempts_per_url',1)
    if not 1<=max_attempts<=3:raise ValueError('attempt_limit_must_be_1_to_3')
    trial.mkdir(parents=True,exist_ok=True)
    lock=(root/'captcha_collect.lock').open('a+b');lock.seek(0)
    if not lock.read(1):lock.write(b'0');lock.flush()
    lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:raise RuntimeError('another_captcha_collector_is_running')
    started=now();state={'pid':os.getpid(),'started_at':started,'status':'running','batch_size':batch_size,
                        'allowed_hosts':scope,'max_attempts_per_url':max_attempts,'scope_label':config.get('label','全部已发现站点')}
    def stopped():return (root/'STOP').exists() or (trial/'STOP').exists()
    def records():
        path=trial/'results.json'
        return json.loads(path.read_text('utf8')) if path.exists() else []
    def progress(status='running',last=None):
        all_records=records();rs=[r for r in all_records if scope is None or r['host'] in scope]
        latest={r['url']:r for r in rs}
        with closing(sqlite3.connect(root/'crawl.sqlite')) as db, db:
            remaining=len(remaining_urls(db,rs,scope,max_attempts))
            unattempted=len(remaining_urls(db,rs,scope,1))
            scoped=db.execute("SELECT host,url,status,result FROM urls WHERE status IN ('captcha_required','failed','blocked','blocked_host','login_required')").fetchall()
            scoped=[r for r in scoped if scope is None or r[0] in scope]
            files=db.execute('SELECT count(*) FROM objects').fetchone()[0]
            db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('run_status','captcha_'+status))
            db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('updated',now()))
        state.update(status=status,updated_at=now(),attempted=len(rs),successful_urls=sum(r['success'] for r in latest.values()),
                     unsuccessful_urls=sum(not r['success'] for r in latest.values()),remaining_unattempted=unattempted,
                     remaining_attemptable=remaining,remaining_captcha_urls=sum(r[2]=='captcha_required' for r in scoped),
                     other_unresolved_urls=sum(r[2]!='captcha_required' for r in scoped),unique_files=files,
                     all_sites_attempts=len(all_records))
        if last:state['last_result']={k:last.get(k) for k in ('url','success','reason','finished_at')}
        save_json(root/'captcha_status.json',state)
        if status in ('finished','stopped','failed'):
            unresolved=[]
            for host,url,url_status,result in scoped:
                unresolved.append(unresolved_record(host,url,url_status,result,latest.get(url)))
            save_json(root/'scoped_unresolved.json',unresolved)
        return remaining
    def captured(record):
        import_record(root,record);progress(last=record)
    try:
        for record in records():
            if scope is None or record['host'] in scope:import_record(root,record)
        progress();generate(root)
        while not stopped():
            if not progress():break
            with closing(sqlite3.connect(root/'crawl.sqlite')) as db:
                active_hosts=[h for h, in db.execute("SELECT DISTINCT host FROM urls WHERE status='captcha_required' ORDER BY host") if h.endswith('.sicau.edu.cn') and (scope is None or h in scope)]
            if not active_hosts:raise RuntimeError('remaining_urls_have_no_allowed_school_host')
            run(root,batch_size,active_hosts,on_record=captured,max_attempts=max_attempts)
            remaining=progress();generate(root)
            if not remaining:break
            summary=json.loads((trial/'summary.json').read_text('utf8'))
            if summary['stop_reason']=='three_consecutive_failures':
                state['cooldown_until_epoch']=time.time()+60;progress()
                for _ in range(60):
                    if stopped():break
                    time.sleep(1)
                state.pop('cooldown_until_epoch',None)
        progress('stopped' if stopped() else 'finished');generate(root,verify=True)
    except BaseException as error:
        state['error']=repr(error);progress('failed');raise
    finally:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True)
    parser.add_argument('--batch-size',type=int,default=40);parser.add_argument('--hosts',nargs='+')
    parser.add_argument('--max-attempts',type=int);args=parser.parse_args()
    if not 1<=args.batch_size<=100:parser.error('batch size must be 1..100')
    collect(args.root,args.batch_size,args.hosts,args.max_attempts)
