import asyncio
import json
import sys
import hashlib
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from requests_spider.rule import Rule
from requests_spider.request import Request
from requests_spider.response import Response
from requests_spider.logger import logger
from requests_spider.model import Model
from requests_spider.squeue import Squeue
from inspect import isasyncgen, isawaitable
from requests_html import HTMLSession

try:
    import uvloop as uv

    asyncio.set_event_loop_policy(uv.EventLoopPolicy())
except ImportError:
    pass

try:
    assert sys.version_info.major == 3
    assert sys.version_info.minor > 5
except AssertionError:
    raise RuntimeError('Snake requires Python 3.6+!')

_Response = Response
_Request = Request
_Model = Model
_Rule = Rule
_Queue = Squeue
_Set = set


class Spider(HTMLSession):

    def __init__(self, name, loop=None, workers=None, mock_browser=True):
        super().__init__(mock_browser=mock_browser)

        self.name = name

        self._init_requests = []
        self._rules = []

        self.async_limit = 5
        self.queue_timeout = 5
        self.request_count = 0

        self._middleware_funcs = {}
        self._queue = _Queue()
        self._visited_url = _Set()

        self.semaphore = asyncio.Semaphore(self.async_limit)
        self.loop = loop or asyncio.get_event_loop()
        self.thread_pool = ThreadPoolExecutor(max_workers=workers)

    """
    basic settings
    """

    # 初始化请求
    @property
    def init_requests(self):
        return self._init_requests

    @init_requests.setter
    def init_requests(self, requests):
        if isinstance(requests, list):
            for request in requests:
                if isinstance(request, _Request):
                    self._init_requests.append(request)
        elif isinstance(requests, _Request):
            self._init_requests.append(requests)
        else:
            raise TypeError('start_requests: {} is list or Request but not {} '.format(requests, type(requests)))

    @property
    def rules(self):
        return self._rules

    @rules.setter
    def rules(self, rules):
        """
        next request rule
        """
        for rule in rules:
            if isinstance(rule, _Request):
                self._rules.append(rule)

    @property
    def is_running(self):
        """
        queue is not empty and program is running
        """
        if self._queue.empty():
            return False
        return True

    """
    request from Request and async request
    """

    def request(self, *args, **kwargs):
        func = partial(super(Spider, self).request, *args, **kwargs)
        return self.loop.run_in_executor(self.thread_pool, func)

    async def from_request(self, req):
        try:
            self.request_count += 1
            resp = await self.request(url=req.url, method=req.method, **req.info)
            return _Response.from_response(req, resp, self)
        except (TimeoutError, ConnectionError) as e:
            logger.info('Request: {} and Error: {}'.format(req, e))

    """
    operate queue 
    """

    async def put_item(self, item: _Request):
        if isinstance(item, _Request):
            if item.not_filter:
                self._queue.dumps_nowait(item)
            elif not self.filter_request(item):
                self._queue.dumps_nowait(item)
        else:
            logger.info('put item: {}'.format(item))

    async def get_item(self):
        return await self._queue.loads()

    """
    filter request
    """

    @staticmethod
    def encode_request(req: _Request):
        """
        encode request
        """

        e_url = json.dumps({req.method: req.url, 'form_filter': req.form_filter}).encode('utf8')
        return hashlib.md5(e_url).hexdigest()

    def add_request(self, req: _Request):
        """
        add request
        """

        e_url = self.encode_request(req)
        self._visited_url.add(e_url)

    def filter_request(self, req: _Request):
        """
        filter request
        """

        e_url = self.encode_request(req)
        if e_url in self._visited_url:
            return True
        return False

    """
    Component
    """

    def _add_middleware(self, func, option='request'):
        """
        add middleware func
        """
        if option == 'request':
            self._middleware_funcs.setdefault(option, []).append(func)
        elif option == 'response':
            self._middleware_funcs.setdefault(option, []).append(func)
        return func

    def Middleware(self, option):
        """
        option type: request/response/record
        @spider.Middleware
        """
        if callable(option):
            return self._add_middleware(func=option)
        else:
            return partial(self._add_middleware, option=option)

    def _run_middleware(self, item, name):
        """
        run middleware
        """
        for middleware in self._middleware_funcs.get(name):
            if isinstance(item, _Request) or isinstance(item, _Response):
                item = middleware(item)
            else:
                return None
        return item

    async def async_put_item(self, result):
        """
        async put item
        async generator/generator/list/item
        """
        if isasyncgen(result):
            async for item in result:
                await self.put_item(item)
        elif isawaitable(result):
            await self.put_item(await result)
        elif isinstance(result, list):
            for item in result:
                await self.put_item(item)
        else:
            await self.put_item(result)

    """
    main
    """

    async def init(self):
        """
        Request initialization:  getting initialization requests from Middleware
        """
        for request in self.init_requests:
            await self.async_put_item(request)

    async def dispather(self):
        """
        dispather: get request from queue and put into downloader
        """
        with await self.semaphore:
            while self.is_running:
                try:
                    item = await asyncio.wait_for(self.get_item(), self.queue_timeout)
                    if isinstance(item, _Request):
                        resp = await self.downloader(item)
                        if isinstance(resp, _Response):
                            await self.parser(resp)
                except asyncio.TimeoutError:
                    pass

    async def downloader(self, item: _Request):
        """
        downloader： requests -> request_middleware_func -> downloader -> response_middleware_func -> return
        """

        logger.info('run downloader')
        logger.info('request: {}'.format(item))

        self.add_request(item)
        if self._middleware_funcs.get('request'):
            item = await self._run_middleware(item, 'request')
        if item:
            if isinstance(item, _Request):
                item = await self.from_request(item)
            if self._middleware_funcs.get('response'):
                item = await self._run_middleware(item, 'response')

        logger.info('response: {}'.format(item))
        logger.info('end downloader')

        return item

    async def parser(self, response: _Response):
        """
        parser： parse response and get request or process model data
        """
        logger.info('run parser')
        logger.info('response: {}'.format(response))
        if len(self._rules) > 0:
            for rule in self._rules:
                result = rule.search(response)
                if result:
                    await self.async_put_item(result)

        callback = getattr(response.current_request, 'callback', None)
        if callback:
            callback = callback()
            if isinstance(callback, _Model):
                callback.load(response)
                callback = callback.process(response)
            await self.async_put_item(callback)

        logger.info('end parser')

    def run(self):
        """
        process: main program
        """
        logger.info('START SPIDER')
        start_time = datetime.now()
        try:
            logger.info('run init_spider')
            self.loop.run_until_complete(self.init())
            logger.info('end init_spider')

            logger.info('run main_spider')
            tasks = asyncio.wait(
                [self.dispather() for _ in range(self.async_limit)])
            self.loop.run_until_complete(tasks)
            logger.info('end main_spider')

        except KeyboardInterrupt:
            logger.info('keyboard cancel all tasks')
            for task in asyncio.Task.all_tasks():
                task.cancel()
            self.loop.run_forever()
        finally:
            self.close()
            self.loop.close()
            logger.info('Request Count: {}'.format(self.request_count))
            logger.info('Time Usage： {}'.format(datetime.now() - start_time))
            logger.info('CLOSE SPIDER')
