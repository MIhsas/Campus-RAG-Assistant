import unittest
import sqlite3
from multi_capture import discover, candidate, page_state


class MultiTests(unittest.TestCase):
    def test_attachment_endpoint(self):
        self.assertEqual(candidate('https://xsc.sicau.edu.cn/system/_content/download.jsp?wbfileid=1', {'xsc.sicau.edu.cn'}), 'file')

    def test_external_scope(self):
        self.assertEqual(candidate('https://jjxy.sicau.edu.cn/a.pdf', {'xsc.sicau.edu.cn'}), 'file')
        self.assertEqual(candidate('https://evil.example/a.pdf', {'xsc.sicau.edu.cn'}), 'excluded')

    def test_official_continuing_education_attachment_host(self):
        self.assertEqual(candidate('http://web.cnzx.info/NewsSystem/UploadFiles/a.zip',{'www.cnzx.info'}),'file')
        self.assertEqual(candidate('http://web.cnzx.info/other.html',{'www.cnzx.info'}),'excluded')

    def test_photo_is_not_document_attachment(self):
        found = discover('<img src="/__local/a.jpg"><a href="/__local/b.pdf">规定</a>', 'https://xsc.sicau.edu.cn/a.htm')
        self.assertEqual(found, [('https://xsc.sicau.edu.cn/__local/b.pdf','规定')])

    def test_js_redirect_discovery(self):
        found = discover("<script>window.location.href='https://xgxt.sicau.edu.cn/web';</script>", 'https://xggl.sicau.edu.cn/')
        self.assertIn(('https://xgxt.sicau.edu.cn/web','script_redirect'),found)

    def test_login_is_not_content(self):
        self.assertEqual(page_state('<title>用户登录</title><form><input type="password"></form>'), 'login_required')
        self.assertEqual(page_state('<h1>学生奖励办法</h1><p>国家奖学金条件</p>'), 'page')

    def test_download_directory_is_page(self):
        self.assertEqual(candidate('https://xsc.sicau.edu.cn/download.htm', {'xsc.sicau.edu.cn'}), 'page')

    def test_captcha_attachment_is_blocked(self):
        self.assertEqual(page_state('<title>附件下载</title><p>请输入验证码下载附件</p>'), 'captcha_required')

    def test_queue_does_not_starve_other_hosts(self):
        from multi_capture import next_candidates
        db=sqlite3.connect(':memory:')
        db.row_factory=sqlite3.Row
        db.execute('create table urls(id integer,host text,status text,priority integer)')
        db.executemany('insert into urls values(?,?,?,?)',[(i,'a','queued',0) for i in range(4100)]+[(5000,'b','queued',20)])
        self.assertEqual({r['host'] for r in next_candidates(db)}, {'a','b'})


if __name__=='__main__':
    unittest.main()
