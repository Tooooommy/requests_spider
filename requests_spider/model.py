import json

from requests_spider.field import Field
from requests_spider.response import Response


class ModelMeta(type):
    def __new__(mcs, name, bases, attrs):
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)

        fields = {k: v for k, v in attrs.items() if isinstance(v, Field)}
        for k in fields.keys():
            attrs.pop(k)

        attrs['_fields'] = fields
        return type.__new__(mcs, name, bases, attrs)


class Model(metaclass=ModelMeta):
    def __init__(self):
        self._values = {k: v.default for k, v in self._fields.items()}

    def __getitem__(self, item):
        try:
            return self._values[item]
        except KeyError:
            raise AttributeError('{} object has no attribute {}'.format(self.__class__.__name__, item))

    def __setitem__(self, key, value):
        self._values[key] = value

    def __delitem__(self, key):
        del self._values[key]

    def __getattr__(self, item):
        if item in self._values:
            raise AttributeError("Use record[{}] to get field value".format(item))
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            raise AttributeError("Use record[{}] = {} to set field value".format(key, value))
        super(Model, self).__setattr__(key, value)

    def keys(self):
        return list(self._values.keys())

    def values(self):
        return list(self._values.values())

    def items(self):
        return self._values.items()

    def json(self):
        return dict(self._values)

    def dumps(self):
        return json.dumps(self.json(), ensure_ascii=False)

    def merge(self):
        result = []
        if len(self.values()) > 0 and isinstance(self.values()[0], list):
            len_ = len(self.values()[0])
            for values in self.values():
                if len(values) != len_ or not isinstance(values, list):
                    raise ValueError('Values [{}] error len or not list !'.format(values))

            for values in list(zip(*self.values())):
                result.append(dict(zip(self.keys(), values)))
        return result

    def __str__(self):
        return '<Model: {}>'.format(self.__class__.__name__)

    def load(self, response):
        for key, value in self._fields.items():
            self._values[key] = value.load_item(response)

    async def process(self, response: Response):
        raise NotImplementedError

