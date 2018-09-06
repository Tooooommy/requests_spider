import asyncio
import re
from lxml.etree import ParserError
from requests_spider.Const import METHOD_GET, METHOD_ALL
from requests_html import HTMLResponse
from urllib.parse import urlparse, urlunparse, urljoin

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


def dict_url(link: str):
    return dict(zip(
        ['scheme', 'netloc', 'path', 'params', 'query', 'fragment'],
        [v for v in urlparse(link)]))


def mk_link(link: str, url: str):
    # parsed = urlparse(link)
    parsed = dict_url(link)

    if not parsed['netloc']:
        return urljoin(url, link)

    if not parsed['scheme']:
        parsed['scheme'] = urlparse(url).scheme
        parsed = (v for v in parsed.values())
        return urlunparse(parsed)
    return link


class Response(HTMLResponse):
    def __init__(self, session, request):
        super(Response, self).__init__(session)
        self.current_request = request

    @classmethod
    def from_response(cls, request, response, session):
        """
        给获取的response响应数据绑定meta/record
        """
        resp = cls(session, request)
        resp.__dict__.update(response.__dict__)
        return resp

    def __str__(self):
        return '<Response: {}>'.format(self.status_code)

    __repr__ = __str__


class Request(object):
    def __init__(self, url, *, method=METHOD_GET, model=None, meta=None,
                 not_filter=False, meta_filter=None, **kwargs):
        """
        包装一下下次请求的一些信息
        :param url:类似百度等网址，格式：https://www.baidu.com
        :param method:请求方法，格式 GET/POST...
        :param meta:元数据块，request和response之间的数据交流， 格式：{'hello': 'world'}
        :param model: 元数据
        :param not_filter:是否过滤该请求，格式：False/True
        """
        self._url = url
        method = str(method).upper()
        if method not in METHOD_ALL:
            raise ValueError('{} not in {}'.format(method, METHOD_ALL))
        self.method = method
        self.info = kwargs or {}
        self.model = model
        self.not_filter = not_filter
        self.meta_filter = meta_filter
        self.meta = dict(meta) if meta else {}

    def __str__(self):
        return "<Request: {}>".format(self.url)

    __repr__ = __str__

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, link):
        parsed = dict_url(link)
        if not parsed['scheme']:
            parsed['scheme'] = 'https'
        self._url = urlunparse((v for v in parsed.values()))

    def copy(self, url):
        return Request(url, method=self.method, model=self.model, meta=self.meta,
                       meta_filter=self.meta_filter, not_filter=self.not_filter, **self.info)

    def make_next(self, links, resp):
        return [self.copy(mk_link(link, resp.url)) for link in links]

    def search(self, response):
        pass


class XRequest(Request):

    def search(self, response):
        try:
            links = response.html.xpath(self.url)
        except (ParserError, UnicodeDecodeError):
            links = []
        return self.make_next(links, response)


class RRequest(Request):

    def search(self, response):
        links = re.findall(self.url, response.text)
        return self.make_next(links, response)


if __name__ == '__main__':
    d = dict_url('video_1424027.com')
    print(d)
    link = mk_link('video_1424027', 'http://www.pearvideo.com/popular')
    print(link)
