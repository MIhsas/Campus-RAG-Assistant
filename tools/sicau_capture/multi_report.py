"""Export a consistent, reviewable snapshot of the multi-site collection."""
import argparse
import hashlib
import html
import json
import sqlite3
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def dump_lines(path, rows):
    with path.open('w',encoding='utf8') as stream:
        for row in rows:
            stream.write(json.dumps(row,ensure_ascii=False)+'\n')


def generate(out, verify=False):
    out=Path(out).resolve()
    db=sqlite3.connect(out/'crawl.sqlite',timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('BEGIN')
    urls=[dict(r) for r in db.execute('SELECT * FROM urls ORDER BY id')]
    objects=[dict(r) for r in db.execute('SELECT * FROM objects ORDER BY path')]
    meta=dict(db.execute('SELECT key,value FROM meta'))
    db.close()
    config=json.loads((out/'sites.json').read_text('utf8'))
    sites={s['host']:s for s in config['sites']}
    states=Counter(r['status'] for r in urls)
    bysite=defaultdict(Counter)
    sources=defaultdict(list)
    records=[]
    for row in urls:
        bysite[row['site']][row['status']]+=1
        r=json.loads(row['result'] or '{}')
        r.update(url=row['url'],site=row['site'],status=row['status'],source_page=row['source'],link_text=row['label'],attempts=row['attempts'])
        records.append(r)
        if row['status']=='file':
            sources[r['sha256']].append(r)
    previous=out.parent/'sicau-jiaowu-2026-09-29'/'catalog.jsonl'
    old=set()
    if previous.exists():
        for line in previous.read_text('utf8').splitlines():
            r=json.loads(line)
            if r.get('sha256'): old.add(r['sha256'])
    catalog=[]
    for obj in objects:
        obj['sources']=sources[obj['sha256']]
        obj['already_in_jiaowu']=obj['sha256'] in old
        obj['version_status']='unreviewed'
        catalog.append(obj)
    pending=states['queued']+states['fetching']
    stopped=(out/'STOP').exists()
    pagination_path=out/'discovery'/'student-pagination'/'state.json'
    pagination={}
    if pagination_path.exists():
        try:pagination=json.loads(pagination_path.read_text('utf8'))
        except json.JSONDecodeError:pass
    run_label='采集已停止，队列已保存' if stopped else ('当前发现规则下队列耗尽' if not pending else '采集中／可恢复，尚未完成')
    if stopped and meta.get('run_status')=='network_blocked':
        run_label='网络连接失败，采集暂未恢复，队列已保存'
    captcha={}
    if (out/'captcha_status.json').exists():
        captcha=json.loads((out/'captcha_status.json').read_text('utf8'))
        phase={'running':'验证码附件持续采集中','stopped':'验证码附件采集已停止','finished':'验证码附件本轮已处理完毕','failed':'验证码附件后台进程异常退出'}.get(captcha.get('status'),'验证码附件采集')
        run_label=f"{phase}；未尝试 {captcha.get('remaining_unattempted',0)}，尝试未成功 {captcha.get('unsuccessful_urls',0)}（状态更新 {captcha.get('updated_at','')}）"
        if captcha.get('allowed_hosts'):
            run_label=captcha.get('scope_label','限定站点')+'：'+run_label+f"；仍可尝试 {captcha.get('remaining_attemptable',0)}，其他未成功链接 {captcha.get('other_unresolved_urls',0)}。其他站点已停止后续采集"
    summary={'snapshot_at':datetime.now(timezone.utc).isoformat(),'crawl_updated_at':meta.get('updated'),
        'configured_sites':len(sites),'college_sites':sum(s.get('group')=='college' for s in sites.values()),
        'states':dict(states),'pending':pending,'captcha_collection':captcha,'unique_files':len(objects),'bytes':sum(r['bytes'] for r in objects),
        'overlap_with_jiaowu':sum(r['already_in_jiaowu'] for r in catalog),
        'student_archive_lists_complete':sum(v.get('status')=='complete' for v in pagination.values()),
        'student_archive_pages':sum(v.get('pages',v.get('page',0)) for v in pagination.values()),
        'queue_exhausted':pending==0,'stopped':stopped,'coverage':'public links discovered by implemented HTML rules; not a complete website guarantee'}
    dump_lines(out/'catalog.jsonl',catalog)
    dump_lines(out/'url_status.jsonl',records)
    dump_lines(out/'accessible_pages.jsonl',(r for r in records if r['status'] in ('page','api_article')))
    dump_lines(out/'restricted_pages.jsonl',(r for r in records if r['status'] in ('captcha_required','login_required','access_challenge','blocked','blocked_host')))
    dump_lines(out/'pending.jsonl',(r for r in records if r['status'] in ('queued','fetching')))
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# 学工网与学院官网公开材料采集','',
        f"快照时间（UTC）：{summary['snapshot_at']}；最近采集更新：{meta.get('updated','未知')}。",'',
        f"状态：{run_label}。待处理 {pending} 个 URL。",'',
        f"范围：{len(sites)} 个入口，其中 {summary['college_sites']} 个学院官网；学院来源为学校官方机构目录。",'',
        f"已保存 {len(objects)} 份不同字节内容的附件，共 {summary['bytes']/1048576:.2f} MiB；成功附件 URL {states['file']} 个；公开 HTML 正文/栏目页面 {states['page']} 个，动态文章 {states['api_article']} 篇。",
        f"与首批教务网重合 {summary['overlap_with_jiaowu']} 份（SHA-256 比较）。正文页面数量包含栏目，不等同于政策文件数。",'',
        f"学工表单分页：{summary['student_archive_lists_complete']} 个列表已到末页，保存/处理的分页进度合计 {summary['student_archive_pages']} 页；原始响应和分页状态见 discovery/student-pagination。该数量不加进正文文章数。",'',
        '## 分站统计','', '| 站点 | 附件 URL | 正文/栏目 | 验证码 | 登录/访问限制 | 失败 | 待处理 |', '|---|---:|---:|---:|---:|---:|---:|']
    for host,site in sites.items():
        c=bysite[host]
        lines.append(f"| [{site['name']}]({site['url']}) | {c['file']} | {c['page']+c['api_article']} | {c['captcha_required']} | {c['login_required']+c['access_challenge']+c['blocked']+c['blocked_host']} | {c['failed']+c['soft_404']+c['unrecognized']+c['api_error']} | {c['queued']+c['fetching']} |")
    lines+=['','## 状态明细','']+[f'- `{k}`：{v}' for k,v in sorted(states.items())]
    lines+=['','## 使用与覆盖边界','',
        '- `index.html` 可按站点、标题、文件名搜索附件；各站 TXT 索引链接到正文快照。',
        '- `catalog.jsonl` 是按内容去重的文件清单，含 SHA-256、字节数、文件路径和成功 URL 来源；`url_status.jsonl` 是本次快照的权威状态，历史追加日志可能包含旧状态。',
        '- `restricted_pages.jsonl` 保留尚未成功下载的验证码、登录和访问限制来源。公开附件验证码表单使用本地 OCR 尝试，逐链接结果见 discovery/captcha-ocr-trial/results.json；未使用登录凭据。',
        '- `pending.jsonl` 中的地址尚未完成。不能把链接发现数、排队数、验证码页面数算成下载成功数。',
        '- 附件可能是图片、科研/活动材料或含个人信息的公示；当前只做公开资料收集，尚未逐份筛选、脱敏或确认政策是否有效。',
        '- 学工新旧入口存在重复内容；按字节去重，不能据标题相同认定为同一版本。网页 TXT 保留导航等原文，尚未做 RAG 正文清洗。',
        '- 新闻内嵌图片、头像、装饰资源、音视频、登录业务系统不作为文件库抓取；只下载明确链接的图片附件。',
        '- 无公开链接的文件无法枚举。动态站、表单分页、搜索和未解析的脚本链接需单独适配；目录耗尽不代表学校所有资料均已获得。',
        '- 产业创新学院在官方目录中没有有效官网链接，本批不猜测入口。继续教育学院使用官网 JavaScript 中公开的 GET 目录、分页和文章接口，API 原始 JSON 与 TXT 一起保存；仅目录/列表响应不计作文章。',
        '- 采集数据与正式 RAG 索引、评测集分离；未自动入库。',
        '', '## 断点续跑','', '在项目根目录执行：','', '```powershell',
        'python tools/sicau_capture/multi_capture.py --sites data/collections/sicau-student-colleges-2026-09-29/sites.json --output data/collections/sicau-student-colleges-2026-09-29 --workers 33',
        'python tools/sicau_capture/multi_report.py --output data/collections/sicau-student-colleges-2026-09-29 --verify', '```','',
        '不要同时启动两个采集写入进程。需要停止时在批次目录创建 STOP 文件；续跑前移除它。']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    esc=lambda value:html.escape(str(value),quote=True)
    link=lambda value:quote(str(value).replace('\\','/'),safe='/')
    head='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>川农公开材料</title><style>body{font:16px/1.6 system-ui;max-width:1250px;margin:32px auto;padding:0 20px;color:#17352c}a{color:#12654f}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #dce5df;text-align:left;word-break:break-word}input{padding:12px;width:90%;margin:16px 0}small{color:#56645d}details{margin:12px 0}</style>'
    content=[head,'<h1>川农学工与学院公开材料</h1>',f"<p>{len(objects)} 份唯一附件 · {summary['bytes']/1048576:.2f} MiB · {states['page']+states['api_article']} 个公开页面/文章 · 待处理 {pending} 个 URL</p>",
        '<p><strong>'+run_label+'</strong>。验证码、登录和失败记录不计入成功文件。</p>',
        f"<small>快照：{esc(summary['snapshot_at'])}（UTC）</small>",'<p><a href="report.md">逐站报告</a> · <a href="catalog.jsonl">文件元数据</a> · <a href="restricted_pages.jsonl">受限来源</a> · <a href="pending.jsonl">待处理清单</a></p>',
        '<input id="q" placeholder="搜索学院、文件名或来源标题" aria-label="搜索附件"><table><thead><tr><th>文件</th><th>站点与来源</th><th>大小</th></tr></thead><tbody id="rows">']
    for obj in catalog:
        refs=[]
        for r in obj['sources']:
            site=sites.get(r['site'],{}).get('name',r['site'])
            refs.append(f"{esc(site)}：<a href=\"{esc(r['source_page'] or r['url'])}\">{esc(r['link_text'] or '原始页面')}</a>")
        content.append(f'<tr><td><a href="{link(obj["path"])}">{esc(obj["name"])}</a></td><td>'+ '<br>'.join(refs)+f'</td><td>{obj["bytes"]/1024:.1f} KiB</td></tr>')
    content+=['</tbody></table><h2>各站公开页面（TXT）</h2><ul>']
    site_folder=out/'indexes';site_folder.mkdir(exist_ok=True)
    for host,site in sites.items():
        page_rows=[r for r in records if r['site']==host and r['status'] in ('page','api_article') and r.get('path')]
        content.append(f'<li><a href="indexes/{host}.html">{esc(site["name"])} · {len(page_rows)} 页</a></li>')
        body=[head,f'<h1>{esc(site["name"])}</h1><a href="../index.html">返回附件索引</a><ul>']
        for r in page_rows:
            txt=str(Path(r['path']).with_suffix('.txt')).replace('\\','/')
            body.append(f'<li><a href="../{link(txt)}">{esc(r.get("title") or r["url"])}</a> · <a href="{esc(r["url"])}">官网原文</a></li>')
        body.append('</ul></html>')
        (site_folder/(host+'.html')).write_text(''.join(body),encoding='utf8')
    content+=['</ul><script>document.getElementById("q").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("#rows tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))});</script></html>']
    (out/'index.html').write_text(''.join(content),encoding='utf8')
    if verify:
        problems=[]
        for obj in objects:
            path=out/obj['path']
            if not path.exists():problems.append({'path':obj['path'],'error':'missing'});continue
            data=path.read_bytes()
            if len(data)!=obj['bytes'] or hashlib.sha256(data).hexdigest()!=obj['sha256']:
                problems.append({'path':obj['path'],'error':'size_or_sha256'})
            if data.startswith(b'PK\x03\x04'):
                try:
                    with zipfile.ZipFile(path) as z:
                        bad=z.testzip()
                        if bad:problems.append({'path':obj['path'],'error':'zip_crc','entry':bad})
                except (OSError,zipfile.BadZipFile) as ex:problems.append({'path':obj['path'],'error':str(ex)})
        verification={'verified_at':datetime.now(timezone.utc).isoformat(),'files_checked':len(objects),'issues':problems,'snapshot_pending':pending}
        (out/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
        summary['verification_issues']=len(problems)
    print(json.dumps(summary,ensure_ascii=True),flush=True)
    return pending


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    while True:
        pending=generate(args.output,args.verify)
        if not args.watch or not pending or (Path(args.output)/'STOP').exists():break
        time.sleep(60)
