# 川农大教务网本次采集工具

正式通用爬虫的设计见 `../../docs/superpowers/plans/2026-09-29-public-document-crawler.md`。这里是独立资料采集脚本，不接入 RAG 后端，不是正式通用爬虫的完成声明。

运行环境：Windows、Python 3.12、系统 curl.exe、BeautifulSoup4。使用现有环境；本次没有安装新依赖。

在 `F:\Collage Paper` 运行：

```powershell
python tools/sicau_capture/discover_search.py
python tools/sicau_capture/capture.py --output data/collections/sicau-jiaowu-2026-09-29 --seeds data/collections/sicau-jiaowu-2026-09-29/all_seeds.txt
python tools/sicau_capture/report.py
python -m unittest discover -s tools/sicau_capture -v
```

- `discover_search.py`：对实际存在的公开搜索表单执行只读查询；查询结果与参数均存档。
- `capture.py`：从队列继续；只有当前 URL 下载完整才保存成功结果。断点恢复按 URL 重新下载尚未完成文件，不是 HTTP Range 字节续传。不能同时运行两个实例写同一个输出目录。
- `web_seeds.txt`：检索中看到的官方原始 URL；本次 `all_seeds.txt` 为其与搜索表单结果的去重合集。
- `report.py`：核验下载文件，生成报告、JSONL 目录和本地可搜索 `index.html`。
- `state.json`：包括待处理和进行中的请求。首次运行上限 10,000 个 URL；达到上限会保留队列并明确报告，重复执行可继续。

范围：教务网同域公开页面与附件，以及教务网页面直接链接的其他校内域名附件（例如 `jwnews.sicau.edu.cn` 制度 PDF）。跨站页面链接仅记录；不登录；不遍历教师/学生私人数据；教室课表、调停课和教师实时查询不属于本次文档采集。公开招生页面与公开附件下载接口允许访问，即使路径包含 `jiaoshi`。

可靠性边界：静态 DOM 和明确的 `window.open` 链接可提取；复杂 JavaScript 拼接和动态表单尚无通用支持；未实现增量 ETag、SQLite 或浏览器适配。网页日期只是候选值，不表示政策生效时间。存储的 HTML 是原始存档，浏览材料时优先用纯文本入口。

本次数据未经适用范围和现行有效性筛选；进入 RAG 前仍需人工审阅。最终覆盖与失败数以数据目录的 `report.md` 为准。

## 学工与学院扩展批次

`multi_capture.py` 使用 `sites.json` 白名单、SQLite 队列、SHA-256 文件去重和来源边表；与上面的第一版教务采集器分开运行。Windows 上优先使用环境现有的 PycURL/libcurl Schannel，缺失时退回 curl.exe；没有安装新依赖。单主机请求间隔至少 0.8 秒，全局至少 0.2 秒，页面和附件不绕过访问控制。证书链、主机名验证保持开启，仅对吊销服务离线使用 libcurl 的 REVOKE_BEST_EFFORT。

`cnzx_adapter.py` 适配继续教育学院官网公开 GET 接口，接口和分页参数依据存档的官网 JavaScript。`multi_report.py` 生成可搜索附件索引、逐站 TXT 索引、当前状态和校验报告。历史 JSONL 日志用于审计，恢复状态以 `crawl.sqlite` 为准，当前导出状态以 `url_status.jsonl` 为准。

2026-09-29 按用户要求停止；2026-09-30 用户已明确要求继续。当前运行状态见 `../../data/collections/sicau-student-colleges-2026-09-29/run_status.json`，交接见该目录的 `RESUME.md`。只在用户要求继续后移除 STOP 并恢复。

`student_pagination.py` 已接入学工 ASP.NET 公开列表下一页提交，保存原始页面并导出种子；不执行登录、搜索或其他提交事件。分页结果中的新链接由主采集器每 30 秒导入。`run_collection.py` 同时管理这两个采集过程，每分钟更新报告，退出后自动校验已保存附件。统一入口：

```powershell
python tools/sicau_capture/run_collection.py --output data/collections/sicau-student-colleges-2026-09-29
```

请勿与单独的 multi_capture / student_pagination 实例同时运行。`runs/` 保存进程日志，STOP 让请求收尾后退出。真实继续教育学院文章接口已验证字段与正文；直接公开的 web.cnzx.info 文档链接允许下载，该域名的普通网页仍不扩大遍历。

## 2026-10-02 验证码 OCR 有限样本试验

用户明确要求测试图片识读及持续自动采集可行性。`captcha_trial.py` 只读取主队列中的 captcha_required 来源，结果单独写入批次 `discovery/captcha-ocr-trial/`，不修改主采集数量或 RAG 索引。通过独立 `.venv-ocr` 环境的本地 ddddocr 识读公开四位数字图片，保留同一主机的内存 Cookie 会话，提交实际读数；每个 URL 无自动重试，连续失败 3 次退出，全局请求间隔至少 1 秒，单文件上限 100 MiB。HTTP 200 的 HTML 不算附件，ZIP 容器需通过 CRC 校验。

```powershell
tools/sicau_capture/.venv-ocr/Scripts/python.exe tools/sicau_capture/captcha_trial.py --root data/collections/sicau-student-colleges-2026-09-29 --limit 30
```

每次 limit 必须为 1–100，默认在三个已观察到该验证码表单的学院间交替测试；可用 --hosts 指定已纳入采集范围的学院域名。再次运行会跳过 results.json 中已尝试的 URL，继续新样本。结果检查点采用临时文件后替换；中途未写入记录的 URL 下次重取。单实例运行。批次 STOP 或试验目录 STOP 均可停止后续请求。本脚本不会自动定时运行、无限重复尝试、修改系统代理或关闭 TLS 校验。更多样本成功不等于所有站点长期都可用。

## 持续处理剩余附件

### 当前范围（2026-10-03 用户缩小任务）

后续只处理学工网新旧入口 xggl / xgxt、党委学工部（处）xsc、信息工程学院 xxgc，均为 sicau.edu.cn 子域名。批次 `collection_scope.json` 是持久化允许列表，`captcha_collect.py` 启动时自动读取；命令行不能扩展到配置外站点。其他已下载材料保留，其未下载链接不再作为本轮任务。不要再运行旧的全站 multi_capture / run_collection 入口。

每个验证码 URL 累计最多尝试 2 次，优先处理未尝试链接，随后补试失败项；历史成功不再请求。状态统计仅针对限定范围，主目录唯一文件数仍包括历史所有站点。`remaining_attemptable` 为本轮仍可尝试数，归零后自动退出；`scoped_unresolved.json` 列出最终未取得的验证码附件及既有 404/403 等失败来源，不能将“本轮结束”理解为全部链接下载成功。范围筛选、重启保持范围及重试上限测试已加入采集测试集。

2026-10-02 用户授权持续处理剩余链接。`captcha_collect.py` 按每批 40 个链接运行上述流程，批次结束后继续；连续三次失败退避 60 秒后继续其他链接。每个 URL 本轮尝试一次，失败记录保留在 results.json，主队列仍保留 captcha_required；不会将失败计为下载完成。已下载的试验文件也会校验并合并到主目录，按 SHA-256 去重，保留每个成功 URL 的来源。每个结果保存断点和 `captcha_status.json`，每批刷新 index.html。启动锁阻止重复运行本脚本；不能与其他采集写入进程同时运行。

```powershell
tools/sicau_capture/.venv-ocr/Scripts/python.exe -u tools/sicau_capture/captcha_collect.py --root data/collections/sicau-student-colleges-2026-09-29
```

当前验证码后台任务状态以 `captcha_status.json`、实际进程和 `runs/captcha-continuous-*.log` 为准，旧 `run_status.json` 仅描述已结束的页面采集任务。关闭电脑会中断进程；重新执行上面命令从已保存结果继续。创建批次 STOP 文件可平稳停止。全部已发现链接尝试完成后自动退出并校验文件；这不代表所有受限附件均已获得，也不包括未来新发布内容。
