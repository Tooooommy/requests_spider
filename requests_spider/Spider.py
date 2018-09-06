import asyncio
import json
import sys
import hashlib
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from urllib.parse import urlparse
from requests_spider.Asker import Request, Response
from requests_spider.Logger import logger
from requests_spider.Model import Model
from inspect import isasyncgen, isawaitable
from requests_html import HTMLSession

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
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
_Queue = asyncio.Queue
_Set = set


class Spider(HTMLSession):

    def __init__(self, name, loop=None, workers=None, mock_browser=True):
        super().__init__(mock_browser=mock_browser)

        self.name = name

        self._init_requests = []
        self._domains = []
        self._rules = []

        self.async_limit = 5
        self.queue_timeout = 5

        self._middleware_funcs = {}  # 下载器之后
        self._queue = _Queue()

        self._done_urls = _Set()  # 访问过url

        self.semaphore = asyncio.Semaphore(self.async_limit)
        self.loop = loop or asyncio.get_event_loop()
        self.thread_pool = ThreadPoolExecutor(max_workers=workers)

    """
    基本设置
    """

    # 初始化请求
    @property
    def init_requests(self):
        return self._init_requests

    @init_requests.setter
    def init_requests(self, requests):
        if isinstance(requests, list):
            self._init_requests.append(requests)
        else:
            raise TypeError('start_requests: {} is list but not {} '.format(requests, type(requests)))

    # 初始化域名
    @property
    def domains(self):
        return self._domains

    @domains.setter
    def domains(self, domains):
        if isinstance(domains, list):
            for domain in domains:
                domain = self._make_domain(domain)
                self._domains.append(domain)
        elif isinstance(domains, str):
            domain = self._make_domain(domains)
            self._domains.append(domain)
        else:
            raise TypeError('domains: {} is list or str but not {}'.format(domains, type(domains)))

    @staticmethod
    def _make_domain(domain):
        """
        修正domain
        """
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    # 获取下次请求的规则
    @property
    def rules(self):
        return self._rules

    @rules.setter
    def rules(self, rules):
        for rule in rules:
            if isinstance(rule, _Request):
                self._rules.append(rule)

    # 判断是否运行
    @property
    def is_running(self):
        """
        判断队列是否为空，程序是否运行
        """
        if self._queue.empty():
            return False
        return True

    """
    session请求方法
    """

    def request(self, *args, **kwargs):
        func = partial(super(Spider, self).request, *args, **kwargs)
        return self.loop.run_in_executor(self.thread_pool, func)

    async def from_request(self, req):
        try:
            resp = await self.request(url=req.url, method=req.method, **req.info)
            return _Response.from_response(req, resp, self)
        except (TimeoutError, ConnectionError) as e:
            logger.info(e)

    """
    队列操作
    """

    async def put_item(self, item):
        """
        入队判断
        """
        if isinstance(item, _Request):
            if item.not_filter:
                self._queue.put_nowait(item)
            elif not self.filter(item):
                self._queue.put_nowait(item)
        elif isinstance(item, _Response):
            self._queue.put_nowait(item)
        else:
            # logger.info('put item: {}'.format(item))
            pass

    async def get_item(self):
        """
        出队
        """
        return await self._queue.get()

    """
    过滤请求
    """

    @staticmethod
    def encode_filter(req):
        """
        编码url
        """
        e_url = json.dumps({req.method: req.url, 'meta_filter': req.meta_filter}).encode('utf8')
        return hashlib.md5(e_url).hexdigest()

    def add_filter(self, req):
        """
        添加url
        """
        e_url = self.encode_filter(req)
        self._done_urls.add(e_url)

    def filter_url(self, req):
        """
        过滤url
        """
        e_url = self.encode_filter(req)
        if e_url in self._done_urls:
            return True

        return False

    def filter_domains(self, req):
        """
        过滤域名
        """
        netloc = urlparse(req.url).netloc
        if len(self._domains) > 0 and not any([netloc.endswith(domain) for domain in self._domains]):
            return True

        return False

    def filter(self, req):
        """

        """
        if self.filter_url(req):
            return True
        elif self.filter_domains(req):
            return True
        return False

    """
    中间组件
    """

    def _add_middleware(self, func, option='request'):
        """
        添加中间函数
        """
        if option == 'request':
            self._middleware_funcs.setdefault(option, []).append(func)
        elif option == 'response':
            self._middleware_funcs.setdefault(option, []).append(func)
        return func

    def Middleware(self, option):
        """
        option type: request/response/record
        request
        response
        record
        """
        if callable(option):
            return self._add_middleware(func=option)
        else:
            return partial(self._add_middleware, option=option)

    async def _run_middleware(self, item, name):
        """
        run middleware
        """
        for middleware in self._middleware_funcs.get(name):
            item = await middleware(item)
        return item

    async def middleware(self, item):
        """
        middleware: processing the acquired item for Middleware
        item type: request/response
        """
        logger.info('启动中间件')
        if isinstance(item, _Request):
            if self._middleware_funcs.get('request'):
                item = await self._run_middleware(item, 'request')

        if isinstance(item, _Response):
            if self._middleware_funcs.get('response'):
                item = await self._run_middleware(item, 'response')

        await self.put_item(item)
        logger.info('结束中间件')

    async def async_put_middleware(self, result):
        """
        异步添加结果到队列中
        判断是否问异步生成器/可挂起/一般
        """
        if isasyncgen(result):
            async for item in result:
                await self.middleware(item)
        elif isawaitable(result):
            await self.middleware(await result)
        elif isinstance(result, list):
            for item in result:
                await self.middleware(item)
        else:
            await self.middleware(result)

    """
    主操作
    """

    # 初始化
    async def init(self):
        """
        Request initialization:  getting initialization requests from Middleware
        """
        for request in self._init_requests:
            logger.info('初始化请求： {}'.format(request))
            await self.async_put_middleware(request)

    # 分发器
    async def dispatcher(self):
        """
        分发器：从队列中获取item，进行进行判别分发到下载器、记录器、解析器
        """
        logger.info('启动分发器')
        with await self.semaphore:
            while self.is_running:
                try:
                    item = await asyncio.wait_for(self.get_item(), self.queue_timeout)
                    if isinstance(item, _Request):
                        await self.downloader(item)
                    elif isinstance(item, _Response):
                        await self.parser(item)
                except asyncio.TimeoutError:
                    pass
        logger.info('结束分发器')

    # 下载器
    async def downloader(self, req):
        """
        下载器：从分发器中获取请求信息，然后进行请求， 获得response响应信息并入对
        """
        logger.info('启动下载器')
        logger.info('request: {}'.format(req))
        resp = await self.from_request(req)
        logger.info('response: {}'.format(resp))
        self.add_filter(req)
        await self.async_put_middleware(resp)
        logger.info('结束下载器')

    # 解析器
    async def parser(self, resp):
        """
        解析器： 从分发器中获取response, 处理rule,record
        """
        logger.info('启动解析器')
        logger.info('response: {}'.format(resp, resp.url))
        if len(self._rules) > 0:
            for rule in self._rules:
                result = rule.search(resp)
                await self.async_put_middleware(result)

        # print('condition: {}'.format(isinstance(record, _Record) and hasattr(record, 'process')))
        model = getattr(resp.current_request, 'model', None)
        print(resp.current_request)
        if model:
            record = model if isinstance(model, _Model) else model()
            record.load(resp)
            result = record.process(resp)
            await self.async_put_middleware(result)
        logger.info('结束解析器')

    def run(self):
        """
        处理器：开启事务,初始化程序,运行分发器
        """
        logger.info('开启爬虫程序')
        start_time = datetime.now()
        try:
            logger.info('初始化爬虫程序')
            self.loop.run_until_complete(self.init())
            logger.info('完成爬虫程序初始化')
            dispatcher = self.dispatcher()
            logger.info('开启爬虫主程序')
            self.loop.run_until_complete(dispatcher)
            logger.info('结束爬虫主程序')

        except KeyboardInterrupt:
            logger.info('手动取消爬虫程序任务')
            for task in asyncio.Task.all_tasks():
                task.cancel()
            self.loop.run_forever()
        finally:
            self.close()
            self.loop.close()
            logger.info('关闭爬虫请求会话')
            logger.info('结束事件循环')
            logger.info('结束爬虫程序')
            logger.info('爬虫程序耗费时间： {}'.format(datetime.now() - start_time))
