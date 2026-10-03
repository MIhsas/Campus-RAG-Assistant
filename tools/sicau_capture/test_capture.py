import unittest
from capture import normalize, extract_links, classify, decode_html, attachment_name


class CaptureTests(unittest.TestCase):
    def test_relative_and_fragment(self):
        self.assertEqual(normalize('https://jiaowu.sicau.edu.cn/web/web/web/index.asp', '../web/a.asp?id=2#x'), 'https://jiaowu.sicau.edu.cn/web/web/web/a.asp?id=2')

    def test_legacy_chinese_and_embedded(self):
        raw = '<meta charset="gb2312"><a href="../附件.doc">表格</a><iframe src="more.asp"></iframe><object data="rule.pdf"></object>'.encode('gb18030')
        txt = decode_html(raw)
        links = extract_links(txt, 'https://jiaowu.sicau.edu.cn/a/index.asp')
        self.assertTrue(any('/附件.doc' in x[0] for x in links))
        self.assertTrue(any(x[0].endswith('/a/rule.pdf') for x in links))

    def test_html_not_pdf(self):
        self.assertEqual(classify(b'<!doctype html><html>not found</html>', 'application/pdf', 'a.pdf'), 'html')

    def test_pdf_and_office(self):
        self.assertEqual(classify(b'%PDF-1.7\n', 'application/octet-stream', 'a.pdf'), 'file')
        self.assertEqual(classify(bytes.fromhex('D0CF11E0A1B11AE1')+b'a', '', 'a.doc'), 'file')

    def test_javascript_link(self):
        links = extract_links('<a href="javascript:window.open(\'files/a.pdf\')">下载</a>', 'https://jiaowu.sicau.edu.cn/x/')
        self.assertIn(('https://jiaowu.sicau.edu.cn/x/files/a.pdf', '下载'), links)

    def test_legacy_download_filename(self):
        header = 'attachment; filename=' + '附件1 证明书办理申请表.doc'.encode('gb18030').decode('latin1')
        self.assertEqual(attachment_name('https://jiaowu.sicau.edu.cn/fujian_down.asp?pid=1', header), '附件1 证明书办理申请表.doc')

    def test_filename_cannot_escape(self):
        self.assertNotIn('/', attachment_name('https://a.test/a.pdf', 'attachment; filename="../../evil.pdf"'))


if __name__ == '__main__':
    unittest.main()
