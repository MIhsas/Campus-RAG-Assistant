"""Read-only API routes observed in cnzx.info's published Vue JavaScript."""
import html
from urllib.parse import urlsplit, urljoin, parse_qs, urlencode
from bs4 import BeautifulSoup

BASE='https://www.cnzx.info'
API=BASE+'/Net/interface/'
ENDPOINTS={'GetXinWenLieBiao.ashx','GetXinWenLeiBie.ashx','GetXinWenXiangQing.ashx'}


def is_api(url):
    p=urlsplit(url)
    return p.hostname=='www.cnzx.info' and (p.path=='/moren.json' or (p.path.startswith('/Net/interface/') and p.path.split('/')[-1] in ENDPOINTS))


def parse_api(data,url):
    links=[]
    def add(endpoint,params,label):
        links.append((API+endpoint+'?'+urlencode(params),label))
    def category(cid,label):
        if str(cid).isdigit() and int(cid)>0:
            add('GetXinWenLeiBie.ashx',{'LeiBieID':cid},label)
            add('GetXinWenLieBiao.ashx',{'LeiBieID':cid,'TiaoShu':8,'YeMa':1},label)
    def walk(node):
        if isinstance(node,list):
            for child in node:walk(child)
        elif isinstance(node,dict):
            label=node.get('MingCheng') or node.get('ZiLeiXingMingCheng') or '公开栏目'
            for key,value in node.items():
                if key in ('XinWenLeiXingID','ZiLeiXingXinWenLeiXingID'):category(value,label)
                elif key=='ChaXunLeiXingID' and value:
                    add('GetXinWenLieBiao.ashx',{'ChaXunLeiXing':value,'TiaoShu':8,'YeMa':1},label)
                elif key in ('LianJie','ZiLeiXingLianJie') and isinstance(value,str) and value:
                    links.append((urljoin(BASE,value),label))
                elif isinstance(value,(list,dict)):walk(value)
    path=urlsplit(url).path
    if path=='/moren.json':
        walk(data)
        return 'api_config','继续教育学院公开栏目配置','',list(dict.fromkeys(links))
    if not isinstance(data,dict):
        return 'api_error','接口响应格式异常','',[]
    if data.get('ZhuangTai',1)<0:
        return 'api_empty',data.get('TiShi','无数据'),'',[]
    if 'GetXinWenLeiBie' in path:
        for item in data.get('ShuJu',[]):
            category(item.get('ZiLeiBieMingID'),item.get('ZiLeiBieMingCheng','栏目'))
            if item.get('LianJieDiZhi'):links.append((urljoin(BASE,item['LianJieDiZhi']),item.get('ZiLeiBieMingCheng','栏目')))
        return 'api_categories',data.get('LeiBieMingCheng','公开栏目'),'',list(dict.fromkeys(links))
    if 'GetXinWenLieBiao' in path:
        for item in data.get('ShuJu',[]):
            if item.get('XinWenID'):
                add('GetXinWenXiangQing.ashx',{'XinWenID':item['XinWenID']},item.get('BiaoTi','文章'))
            if item.get('LianJieDiZhi'):links.append((urljoin(BASE,item['LianJieDiZhi']),item.get('BiaoTi','文章')))
        q={k:v[0] for k,v in parse_qs(urlsplit(url).query).items()}
        page=int(q.get('YeMa',1));size=int(q.get('TiaoShu',8))
        if page*size<int(data.get('ZongTiaoShu',0)) and data.get('ShuJu'):
            q['YeMa']=page+1
            add('GetXinWenLieBiao.ashx',q,'下一页')
        return 'api_list','继续教育学院公开文章列表','',list(dict.fromkeys(links))
    title=data.get('BiaoTi','继续教育学院文章')
    body=data.get('NeiRong','') or ''
    soup=BeautifulSoup(body,'html.parser')
    # Relative attachment paths are rendered against the public article route.
    for a in soup.select('a[href],iframe[src],embed[src]'):
        value=a.get('href') or a.get('src')
        if value and not value.lower().startswith(('javascript:','mailto:')):
            links.append((urljoin(BASE+'/article/',value),a.get_text(' ',strip=True)))
    if data.get('LianJieDiZhi'):links.append((urljoin(BASE,data['LianJieDiZhi']),title))
    body='<h1>'+html.escape(title)+'</h1><p>'+html.escape(str(data.get('FaBuShiJian','')))+'</p>'+body
    return 'api_article',title,body,list(dict.fromkeys(links))
