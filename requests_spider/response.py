from requests_html import HTMLResponse
from requests_spider.request import Request


class Response(HTMLResponse):
    def __init__(self, session, request: Request):
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
