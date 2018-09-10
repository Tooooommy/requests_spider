import re
from lxml.etree import ParserError
from requests_spider.request import Request
from requests_spider.const import mk_link
from requests_spider.response import Response


class Rule(Request):
    def __init__(self, rule, **kwargs):
        super().__init__(url=None, **kwargs)
        self.rule = rule

    def replace(self, url):
        return Request(url, method=self.method, callback=self.callback, meta=self.meta,
                       form_filter=self.form_filter, not_filter=self.not_filter, **self.info)

    def make_next(self, links, response):
        return [self.replace(mk_link(link, response.url)) for link in links]

    def search(self, response: Response):
        pass


class XRule(Rule):

    def search(self, response: Response):
        try:
            links = response.html.xpath(self.rule)
        except (ParserError, UnicodeDecodeError):
            links = []
        return self.make_next(links, response)


class RRule(Rule):

    def search(self, response: Response):
        links = re.findall(self.url, response.text)
        return self.make_next(links, response)


class CRule(Rule):
    def __init__(self, rule, attr='href', **kwargs):
        super().__init__(rule, **kwargs)
        self.attr = attr

    def search(self, response: Response):
        try:
            links = response.html.find(self.url)
            links = [link.attrs.get(self.attr) for link in links]
        except (ParserError, UnicodeDecodeError):
            links = []
        return self.make_next(links, response)
