"""Verify local captures and produce an offline, searchable catalog."""
import hashlib
import html
import json
import zipfile
from capture import decode_html
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, unquote, quote
from datetime import datetime, timezone

ROOT = Path('data/collections/sicau-jiaowu-2026-09-29')


def read(name):
    path = ROOT/name
    return [json.loads(line) for line in path.read_text('utf8').splitlines() if line.strip()] if path.exists() else []


def run():
    state = json.loads((ROOT/'state.json').read_text('utf8'))
    files = list({r['url']:r for r in read('manifest.jsonl')}.values())
    all_pages = list({r['url']:r for r in read('pages.jsonl')}.values())
    restricted = []
    non_document_pages = []
    pages = []
    for r in all_pages:
        txt = decode_html((ROOT/r['path']).read_bytes())
        if '该项信息查询未授权' in txt and 'window.history.go(-1)' in txt:
            restricted.append(dict(r,reason='login_required_http_200',status='blocked'))
        elif '/js_kb_cha/' in urlsplit(r['url']).path or urlsplit(r['url']).path.endswith(('/tklist.asp','/jiaoshi_new.asp')):
            non_document_pages.append(r)
        else:
            pages.append(r)
    (ROOT/'restricted_pages.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in restricted),encoding='utf8')
    (ROOT/'non_document_pages.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in non_document_pages),encoding='utf8')
    unique = {r['sha256']:r for r in files}
    errors = []
    tracked = {r['path'].replace('\\','/') for r in unique.values()}
    actual = {str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'files').iterdir() if p.is_file()}
    untracked_files = sorted(actual-tracked)
    missing_files = sorted(tracked-actual)
    errors.extend(missing_files)
    formats = Counter()
    total = 0
    checks = []
    for r in unique.values():
        path = ROOT/r['path']
        raw = path.read_bytes()
        ext = path.suffix.lower()
        formats[ext] += 1
        total += len(raw)
        valid = len(raw) == r['bytes'] and hashlib.sha256(raw).hexdigest() == r['sha256']
        container = 'not_checked'
        if ext in ('.zip','.docx','.xlsx','.pptx'):
            try:
                with zipfile.ZipFile(path) as z:
                    damaged = z.testzip()
                    expected = {'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}.get(ext)
                    valid = valid and damaged is None and (expected is None or expected in z.namelist())
                    container = 'zip_crc_ok' if valid else 'invalid_zip_or_office'
            except zipfile.BadZipFile:
                valid = False
                container = 'invalid_zip'
        elif ext == '.pdf':
            valid = valid and raw.startswith(b'%PDF-')
            container = 'pdf_signature_only'
        elif ext in ('.doc','.xls','.ppt'):
            # Legacy Office may also be XML/HTML/RTF exported with an Office extension.
            container = 'ole_signature' if raw.startswith(bytes.fromhex('D0CF11E0A1B11AE1')) else 'legacy_non_ole_review'
            if raw.startswith(b'PK\x03\x04'):
                with zipfile.ZipFile(path) as z:
                    valid = valid and z.testzip() is None
                    container = 'zip_crc_ok_extension_mismatch'
        checks.append({'path':r['path'],'bytes':len(raw),'sha256_matches':hashlib.sha256(raw).hexdigest()==r['sha256'],'valid':valid,'format_check':container})
        if not valid:
            errors.append(r['path'])
    for r in all_pages:
        p = ROOT/r['path']
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:
            errors.append(r['path'])
    source_edges = defaultdict(list)
    for r in read('links.jsonl'):
        edge = {'source':r['source'],'label':r.get('label','')}
        if edge not in source_edges[r['url']]:
            source_edges[r['url']].append(edge)
    search_labels = {r['url']:r.get('label','') for r in read('search_discovered_links.jsonl')}
    enriched = []
    for r in files:
        sources = source_edges[r['url']]
        origin = next((s['source'] for s in sources if s['source'].startswith(('https://','http://'))),None)
        enriched.append(dict(r,source_page=origin,discovery_context=r['source_page'],sources=sources))
    (ROOT/'catalog.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in enriched),encoding='utf8')
    for r in pages:
        label = search_labels.get(r['url']) or r.get('link_text') or r.get('title') or r['url']
        if 'jihuaprintall_new.asp' in r['url']:
            lines = (ROOT/Path(r['path']).with_suffix('.txt')).read_text('utf8').splitlines()
            if len(lines)>1:
                label = lines[1]+' 人才培养方案'
        r['display_title'] = label
    (ROOT/'accessible_pages.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in pages),encoding='utf8')
    (ROOT/'verification.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'unique_files':len(unique),'pages':len(all_pages),'bytes':total,'errors':errors,'untracked_files':untracked_files,'checks':checks},ensure_ascii=False,indent=2),encoding='utf8')
    failures = read('failed.jsonl')
    unresolved = {r['url']:r for r in failures if state['done'].get(r['url']) in ('failed','blocked') or r.get('reason')=='html_instead_of_attachment'}
    # A later successful file capture resolves an earlier failure for the same URL.
    unresolved = {u:r for u,r in unresolved.items() if state['done'].get(u)!='file'}
    for r in restricted:
        unresolved[r['url']] = r
    (ROOT/'unresolved.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in unresolved.values()),encoding='utf8')
    searches = read('search_log.jsonl')
    rows = []
    for r in unique.values():
        name = Path(r['path']).name[13:]
        labels = ' '.join(s['label'] for s in source_edges[r['url']] if s['label'])
        origin = next((s['source'] for s in source_edges[r['url']] if s['source'].startswith(('https://','http://'))),r['url'])
        rows.append('<tr><td>附件</td><td><a href="'+html.escape(quote(r['path'],safe='/'),quote=True)+'">'+html.escape(name)+'</a><small>'+html.escape(labels[:300])+'</small></td><td>'+html.escape(Path(r['path']).suffix.lower())+'</td><td>'+str(round(r['bytes']/1024,1))+' KB</td><td><a href="'+html.escape(origin,quote=True)+'">来源</a></td></tr>')
    for r in pages:
        label = r['display_title']
        rows.append('<tr><td>网页</td><td><a href="'+html.escape(str(Path(r['path']).with_suffix('.txt')).replace('\\','/'),quote=True)+'">'+html.escape(label)+'</a><small>'+html.escape(r['url'])+'</small></td><td>TXT / <a href="'+r['path']+'">HTML</a></td><td>'+str(round(r['bytes']/1024,1))+' KB</td><td><a href="'+html.escape(r['url'],quote=True)+'">来源</a></td></tr>')
    index = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>川农大教务网 · 本地资料目录</title><style>body{font:16px/1.6 system-ui,sans-serif;margin:40px auto;padding:0 24px;max-width:1400px;background:#f7f8fa;color:#17252d}h1{font-size:30px}input{font:inherit;padding:12px;width:min(700px,90%);border:1px solid #abb9c0;border-radius:6px}table{border-collapse:collapse;width:100%;background:white;margin:24px 0}td,th{padding:12px;border-bottom:1px solid #dce2e6;text-align:left}small{display:block;color:#68757d;overflow-wrap:anywhere;font-size:12px}a{color:#006f65}td:first-child{white-space:nowrap}td:nth-child(2){max-width:800px}p{max-width:1000px}</style><h1>川农大教务网 · 本地资料目录</h1>'''
    index += f'<p>采集日期：2026-09-29 · 唯一附件 {len(unique)} 份 · 网页 {len(pages)} 页 · 附件 {total/1024/1024:.1f} MiB</p><p>原始材料尚未完成版本与适用范围审核。网页优先打开纯文本，HTML 为原始存档。附件来源及哈希见 catalog.jsonl。此目录不表示全站所有文件已收齐。</p><p><a href="report.md">采集报告</a> · <a href="unresolved.jsonl">未解决链接</a> · <a href="verification.json">文件校验</a></p><label>搜索资料 <input id="q" placeholder="标题、专业、文件类型或网址关键词"></label><p id="count"></p><table><thead><tr><th>类型</th><th>资料</th><th>格式</th><th>大小</th><th>出处</th></tr></thead><tbody>'
    index += '\n'.join(rows)+'</tbody></table><script>const rows=[...document.querySelectorAll("tbody tr")];document.querySelector("#q").addEventListener("input",e=>{let n=0;const q=e.target.value.trim().toLowerCase();for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(q);if(!r.hidden)n++}document.querySelector("#count").textContent=`显示 ${n} 条`});</script></html>'
    (ROOT/'index.html').write_text(index,encoding='utf8')
    status = Counter(state['done'].values())
    report = f'''# 四川农业大学教务网公开资料采集报告

采集起点：https://jiaowu.sicau.edu.cn/  
开始：{state['started']}  
最近检查点：{state['updated']}  
时间格式为 UTC；北京时间加 8 小时。

## 结果

- 已处理 URL：{len(state['done'])}
- 可访问网页存档：{len(pages)}（原始 HTML 和提取纯文本，未完成正文质量筛选）
- 另存的登录受限响应：{len(restricted)}（HTTP 200 但正文明确要求登录，不计可用资料）
- 另存的非文档查询响应：{len(non_document_pages)}（课表等，不计资料目录）
- 成功附件 URL：{len(files)}
- SHA-256 去重后的附件：{len(unique)}
- 附件大小：{total/1024/1024:.2f} MiB
- 本地校验问题：{len(errors)}
- 未登记磁盘附件：{len(untracked_files)}（运行中生成报告可能有短暂时间差，最终报告应为 0）
- 尚未解决的失败/限制 URL：{len(unresolved)}（含 sitemap 探测与附件返回 HTML）
- 待处理队列：{len(state['queue'])}
- 公开表单检索记录：{len(searches)}
- 状态统计：`{json.dumps(dict(status),ensure_ascii=False)}`

## 文件格式

'''
    report += '\n'.join(f'- `{k}`：{v}' for k,v in sorted(formats.items()))
    report += '''

## 发现路径与覆盖限制

1. 从首页实际跳转地址出发，递归处理同域名的栏目、正文、框架、附件及静态脚本打开链接。
2. 用网站实际存在的公开通知搜索表单，按所有类别及 2000—2026 年标题关键词作只读 POST 搜索；保存搜索结果 HTML、查询参数和发现链接。年份搜索匹配标题，不保证涵盖该年每条通知。
3. 搜索引擎发现的官方 URL 作为补充种子，文件内容仍从官方地址直接下载；未用搜索摘要替代原文。
4. 页面遍历范围为 `jiaowu.sicau.edu.cn`；教务网页面直接链接到其他 `*.sicau.edu.cn` 的附件也下载，包括 `jwnews.sicau.edu.cn` 托管的制度 PDF。其他站外页面仅记录，没有递归扩展全校。excluded.jsonl 保留早期范围排除事件；其附件后续可能已成功，实际结果以 catalog.jsonl 为准。
5. robots.txt 返回 404；没有登录、绕过验证码、枚举文章编号或猜测服务器目录。标准 sitemap.xml 探测结果另有记录。
6. 队列耗尽仅表示已实现发现规则下没有待处理 URL，不表示全部服务器文件。无公开入口、登录区、未知动态链接、不可用文件与站外资源均不在完整性保证内。
7. 抓取限速、最多 3 个并发，单文件上限 200 MiB。请求异常有有限重试；最终失败原样保留。
8. 排除教室课表、调停课、教师课表等实时查询入口，防止教室/周次组合无限扩展；已经访问的少量响应仅作存档。原始页面清单包含登录提示页，可用目录已排除这些页面，单独见 restricted_pages.jsonl。
9. 本站部分旧 HTTP 链接连接超时，采用已验证可访问的同域 HTTPS 协议获取同一路径；清单 url 保留发现地址，final_url 记录实际下载地址。没有改动路径或枚举未知文件。

## 资料使用说明

- 从 index.html 搜索并打开本地文件；files/ 保留原始字节，pages/ 保存 HTML/TXT，search_pages/ 保存公开查询结果。
- manifest.jsonl 为下载事件；catalog.jsonl 是按 URL 整理并合并多来源信息的附件清单。同字节不同 URL 共用一份文件。
- accessible_pages.jsonl 是排除登录提示页及实时查询页后的网页目录；培养方案补充了来源正文中的专业与年份标题，未改动原始文件。
- failed.jsonl 保留历史失败事件；unresolved.jsonl 为报告生成时仍未解决的链接；state.json 可用于断点继续。
- 所有材料标为 unreviewed：未核验当前有效性、适用学院/年级、生效日期或是否已被替代。原始公开文件可能含公示名单，不直接进入通用问答库。
- 没有修改产品语料、检索索引、gold、协作状态或 T029 任务。
- 文件校验：全部附件大小与 SHA-256 对照；ZIP/OOXML 校验 CRC 与必要结构；PDF 校验文件头。未进行全部文档的视觉逐页审阅，也未执行压缩包内容。
- 个别源文件扩展名与内容容器不一致（例如 .doc 实际为 OOXML），仍保留原名和字节，在 verification.json 中标记 extension_mismatch；后续解析器应按内容识别。
'''
    (ROOT/'report.md').write_text(report,encoding='utf8')
    print(json.dumps({'unique_files':len(unique),'attachment_urls':len(files),'pages':len(pages),'restricted_pages':len(restricted),'MiB':round(total/1024/1024,2),'unresolved':len(unresolved),'pending':len(state['queue']),'verification_errors':errors},ensure_ascii=True))


if __name__=='__main__':
    run()
