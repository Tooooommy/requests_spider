import json
from requests_spider import XField, Spider, Model, Response, Request


class Proxy(Model):
    ip = XField(rule='//tr[contains(@class, "odd")]/td[2]', first=False)
    port = XField(rule='//tr[contains(@class, "odd")]/td[3]', first=False)

    async def process(self, response: Response):
        with open('proxy1.txt', 'a+') as file:
            for result in self.merge():
                file.write(json.dumps(result) + '\n')


snake = Spider('proxy', workers=15)
snake.domains = ['www.xicidaili.com']
snake.init_requests = [
    Request(url='http://www.xicidaili.com/nn/{}'.format(x), callback=Proxy) for x in range(1, 10)
]

snake.async_limit = 5

if __name__ == '__main__':
    snake.run()
