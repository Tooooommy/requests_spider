from requests_spider.const import METHOD_GET, METHOD_ALL
from requests_spider.const import parse_url, unparse_url

REQUEST_ARGS = frozenset({'params ', 'data', 'headers', 'cookies',
                          'files', 'auth', 'timeout', 'allow_redirects', 'proxies',
                          'hooks', 'stream', 'verify', 'cert', 'json'})


class Request(object):
    def __init__(self, url, *,
                 method=METHOD_GET,
                 callback=None,
                 meta=None,
                 not_filter=False,
                 form_filter=None,
                 **info):
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
        self._method = method

        self.__dict__.update(info)
        self.callback = callback
        self.not_filter = not_filter
        self.form_filter = form_filter
        self.meta = dict(meta) if meta else {}

    def __str__(self):
        return "<Request: {}>".format(self.url)

    __repr__ = __str__

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, link):
        parsed = parse_url(link)
        if not parsed['scheme']:
            parsed['scheme'] = 'https'
        self._url = unparse_url(**parsed)

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, method):
        method = str(method).upper()
        if method not in METHOD_ALL:
            raise ValueError('{} not in {}'.format(method, METHOD_ALL))
        self._method = method

    @property
    def info(self):
        _info = {}
        for key in REQUEST_ARGS:
            if key in self.__dict__.keys():
                _info.update(self.__dict__.get(key))
        return _info




