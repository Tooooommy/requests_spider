import json

from requests_html import HTMLResponse
from requests_spider import Spider, RField, XField, Model, Request, XRule, Response, RRule


class VideoInfo(Model):
    rank = XField(rule='//div[contains(@class, "popularem-sort")]//text()', first=False)
    img = RField(rule='<div class="popularem-img" style="background-image: url\((.*?)\);">', first=False)
    # img = XField(rule='//div[contains(@class, "popularem-img")]/@style', first=False)
    title = XField(rule='//h2[contains(@class, "popularem-title")]//text()', first=False)
    content = XField(rule='//p[contains(@class, "popularem-abs")]//text()', first=False)
    author = XField(rule='//a[contains(@class, "column")]//text()', first=False)
    love = XField(rule='//span[contains(@class, "fav")]//text()', first=False)

    async def process(self, response: HTMLResponse):
        with open('pearvideo.txt', 'a+') as f:
            # if isinstance(self.values(), list) and isinstance(self.values()[0], list):
            #     for values in list(zip(*self.values())):
            #         result = dict(zip(self.keys(), values))
            for result in self.merge():
                f.write(json.dumps(result, ensure_ascii=False) + '\n')


class Video(Model):
    async def process(self, response: Response):
        filename = response.url.split('/')[-1]
        print(filename)
        with open(filename, 'wb') as f:
            f.write(response.content)
            f.flush()


snake = Spider('pearvideo')
snake.init_requests = [
    Request(url='http://www.pearvideo.com/popular_loading.jsp?reqType=1&start={}&sort={}'.
            format(x, x * 10), callback=VideoInfo) for x in range(0, 10)
]

snake.rules = [
    XRule(rule='//a[contains(@class, "popularembd")]/@href'),
    RRule(rule='(http://.*?\.mp4)', model=Video)
]


@snake.Middleware('request')
async def set_timeout(request):
    # print(request.url)
    # await asyncio.sleep(1)
    return request


snake.run()
