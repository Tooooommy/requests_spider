from requests_spider import Spider, Request


async def test(response):
    for x in range(100000):
        yield Request(url='http://www.httpbin.org/get', callback=speed)
    print(response.status_code)


async def speed(response):
    print(response.status_code)


spider = Spider('test')
spider.init_requests = [Request(url='http://www.httpbin.org/status/200', callback=test)]

if __name__ == '__main__':
    spider.run()
