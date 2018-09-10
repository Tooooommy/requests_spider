from urllib.parse import urlparse, urljoin, urlunparse

"""
http请求方法常量
"""
METHOD_HEAD = 'HEAD'
METHOD_GET = 'GET'
METHOD_DELETE = 'DELETE'
METHOD_OPTIONS = 'OPTIONS'
METHOD_PATCH = 'PATCH'
METHOD_POST = 'POST'
METHOD_PUT = 'PUT'
METHOD_ALL = {
    METHOD_HEAD,
    METHOD_GET,
    METHOD_DELETE,
    METHOD_OPTIONS,
    METHOD_PATCH,
    METHOD_POST,
    METHOD_PUT
}


def parse_url(link: str):
    return dict(zip(
        ['scheme', 'netloc', 'path', 'params', 'query', 'fragment'],
        [v for v in urlparse(link)]))


def unparse_url(**kwargs):
    return urlunparse((v for v in kwargs.values()))


def mk_link(link: str, url: str):
    parsed = parse_url(link)

    if not parsed['netloc']:
        return urljoin(url, link)

    if not parsed['scheme']:
        parsed['scheme'] = urlparse(url).scheme
        return unparse_url(**parsed)
    return link
