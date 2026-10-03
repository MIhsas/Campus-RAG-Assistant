import unittest
from student_pagination import next_form


class PaginationTests(unittest.TestCase):
    def test_only_readonly_next_event_and_hidden_state(self):
        html='''<form action="./list.html?x=1"><input type="hidden" name="__VIEWSTATE" value="state"><input name="password" value="ignored"><a id="lbnNextPage" href="javascript:__doPostBack('lbnNextPage','')">下一页</a><span id="lblCurrentPage">1</span><span id="lblPageCount">2</span></form>'''
        action,fields,current,total=next_form(html,'https://xggl.sicau.edu.cn/Web/list.html')
        self.assertEqual(action,'https://xggl.sicau.edu.cn/Web/list.html?x=1')
        self.assertEqual(fields,{'__VIEWSTATE':'state','__EVENTTARGET':'lbnNextPage','__EVENTARGUMENT':''})
        self.assertEqual((current,total),(1,2))

    def test_disabled_last_page_never_posts(self):
        self.assertIsNone(next_form('<form><a id="lbnNextPage" class="aspNetDisabled">下一页</a></form>','https://xggl.sicau.edu.cn/Web/list.html'))

    def test_reject_cross_host_action(self):
        with self.assertRaises(ValueError):
            next_form('''<form action="https://example.org/"><a id="lbnNextPage" href="javascript:__doPostBack('lbnNextPage','')">下一页</a><span id="lblCurrentPage">1</span><span id="lblPageCount">2</span></form>''','https://xggl.sicau.edu.cn/Web/list.html')
