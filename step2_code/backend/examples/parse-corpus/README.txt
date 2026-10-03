本目录中的文件均为合成测试数据，用于验证文档正文解析功能。

- sample.txt：中文多段落 TXT，含数字、空行分隔
- sample.docx：段落-表格-段落交错的 DOCX，含空段落
- generate_docx.py：确定性生成 sample.docx 的脚本
- manifest.json：语料登记清单

is_synthetic=true，source_site 包含"合成测试"，source_url 使用 example.org。
不得用于论文评测或真实校园问答。

查看正文块：
  & .\.venv\Scripts\python.exe -m campus_assistant.corpus.parse --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus
