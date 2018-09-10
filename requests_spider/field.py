import re

from lxml.etree import ParserError


class Field(object):
    """default field"""

    def __init__(self, default=None, rule=None, first=True, attr=None):
        self.rule = rule
        self.first = first
        self.attr = attr
        self.default = default
        # self.value = '' if first else []

    def load_item(self, response):
        """field load"""
        return self.default
        # raise NotImplementedError

    def parse_item(self, element):
        if isinstance(element, str):
            value = element
        elif self.attr:
            value = element.attrs[self.attr]
        else:
            value = element.text

        return value

    def __str__(self):
        return '<Field: {}>'.format(self.__class__.__name__)

    __repr__ = __str__


class CField(Field):
    """Css Field"""

    def load_item(self, response):
        element = None
        if self.rule:
            element = response.html.find(self.rule, first=self.first)
            if element:
                element = self.parse_item(element) if self.first else [self.parse_item(e) for e in element]
        # logger.info('rule: {} and element: {}'.format(self.rule, element))
        return element or self.default


class XField(Field):
    """Xpath Field"""

    def load_item(self, response):
        element = None
        try:
            if self.rule:
                element = response.html.xpath(self.rule, first=self.first)
                if element:
                    element = self.parse_item(element) if self.first else [self.parse_item(e) for e in element]
        except (ParserError, UnicodeDecodeError):
            element = self.default
        # logger.info('rule: {} and element: {}'.format(self.rule, element))
        return element or self.default


class RField(Field):
    """Regex Field"""

    def load_item(self, response):
        element = None
        try:
            if self.rule:
                element = re.findall(self.rule, response.text)
                if element:
                    element = element[0] if element and self.first else element
        except (ParserError, UnicodeDecodeError):
            element = self.default
        # logger.info('rule: {} and element: {}'.format(self.rule, element))
        return element or self.default
