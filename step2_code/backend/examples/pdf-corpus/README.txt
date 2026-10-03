合成 PDF 演示夹具（T021）
生成方式：scripts/make-pdf-fixtures.py，fpdf2 + 本机 Windows SimHei 字体本地生成，无网络获取。
sample-text.pdf：两页中文文本（含数字 10/2024、否定词 不/不得、页内章节标记），用于逐页提取与引用核对。
sample-no-text.pdf：仅线条/矩形，无任何文本，用于验证“未提取到文本”不可用状态。
合成资料，不代表真实学校规定；不改旧 parse/comparison 语料与 gold。
