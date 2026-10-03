import unittest
from cnzx_adapter import is_api, parse_api


class CnzxTests(unittest.TestCase):
    def test_public_list_pagination_and_observed_ids(self):
        url='https://www.cnzx.info/Net/interface/GetXinWenLieBiao.ashx?LeiBieID=31&TiaoShu=8&YeMa=1'
        status,title,body,links=parse_api({'ZongTiaoShu':9,'ShuJu':[{'XinWenID':123,'BiaoTi':'通知'}]},url)
        self.assertEqual(status,'api_list')
        self.assertTrue(any('XinWenID=123' in u for u,t in links))
        self.assertTrue(any('YeMa=2' in u for u,t in links))
        self.assertFalse(any('YeMa=3' in u for u,t in links))

    def test_only_named_public_api_endpoints(self):
        self.assertTrue(is_api('https://www.cnzx.info/moren.json'))
        self.assertFalse(is_api('https://www.cnzx.info/Net/interface/Delete.ashx'))

    def test_detail_keeps_attachment_and_title(self):
        status,title,body,links=parse_api({'BiaoTi':'办法','NeiRong':'<a href="/files/a.pdf">文件</a>'},'https://www.cnzx.info/Net/interface/GetXinWenXiangQing.ashx?XinWenID=123')
        self.assertEqual((status,title),('api_article','办法'))
        self.assertIn(('https://www.cnzx.info/files/a.pdf','文件'),links)
