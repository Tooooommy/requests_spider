import re
from requests_spider import Spider, Model, Request, XRequest,Response, CField, XField, Field, RField, asyncio
from fontTools import BytesIO
from fontTools.ttLib import TTFont

rank_url = 'https://www.qidian.com/rank/yuepiao?style={}&page={}'
score_url = 'https://book.qidian.com/ajax/comment/index?_csrfToken={}&bookId={}&pageSize=15'
font_url = 'https://qidian.gtimg.com/qd_anti_spider/{}.woff'

num_dict = {"six": "6", "three": "3", "period": ".", "eight": "8", "zero": "0",
            "five": "5", "nine": "9", "four": "4", "seven": '7', "one": "1", "two": "2"}


async def get_nums(font_type, font_str):
    print(font_str.encode('unicode-escape'))
    response = await snake.get(url=font_url.format(font_type))
    font = response.content
    ttfont = TTFont(BytesIO(font))
    mappings = {hex(k)[2:]: num_dict.get(v) for k, v in ttfont.getBestCmap().items()}
    print(mappings)
    items = font_str.encode('unicode-escape').split(b'\\U000')[1:]
    return "".join([mappings.get(item.decode('utf8')) for item in items])


class BookScore(Model):
    id = Field()
    score = Field()
    count = Field()

    async def process(self, response: Response):
        data = response.json()['data']
        self['score'] = data['rate']
        self['count'] = data['userCount']
        self['id'] = response.current_request.meta.get('bookid')
        print(response.current_request.meta)
        with open('qidian2.txt', 'a+') as f:
            f.write(self.dumps() + '\n')


class BookInfo(Model):
    id = CField(rule='#bookImg', attr='data-bid')
    img = CField(rule='#bookImg > img', attr='src')
    name = CField(rule='.book-info > h1 > em')
    author = XField(rule='//a[contains(@class, "writer")]//text()')
    tags = XField(rule='//p[contains(@class, "tag")]/span', first=False)
    intro = XField(rule='//p[contains(@class, "intro")]')
    total_words = XField(rule='//div[contains(@class, "book-info")]/p[3]/em[1]/span')
    total_click = XField(rule='//div[contains(@class, "book-info")]/p[3]/em[2]/span')
    week_click = XField(rule='//div[contains(@class, "book-info")]/p[3]/cite[2]/span[2]//text()')
    total_recommend = XField(rule='//div[contains(@class, "book-info")]/p[3]/em[3]/span')
    week_recommend = XField(rule='//div[contains(@class, "book-info")]/p[3]/cite[3]/span[2]//text()')

    async def process(self, response):
        font_type = response.html.xpath('//div[contains(@class, "book-info")]/p[3]/em[1]/span/@class', first=True)
        self['total_words'] = await get_nums(font_type, self['total_words'])
        self['total_click'] = await get_nums(font_type, self['total_click'])
        self['week_click'] = await get_nums(font_type, self['week_click'])
        self['total_recommend'] = await get_nums(font_type, self['total_recommend'])
        self['week_recommend'] = await get_nums(font_type, self['week_recommend'])

        with open('qidian1.txt', 'a+') as file:
            self['img'] = 'https:' + self['img'][:-1]
            file.write(self.dumps() + '\n')
            file.flush()
        yield Request(score_url.format(snake.cookies.get('_csrfToken'), self['id']),
                      model=BookScore, meta={'bookid': self['id']})


snake = Spider(name='one')
snake.domains = ['www.qidian.com']
snake.init_requests = [
    Request(rank_url.format(1, page)) for page in range(1, 2)
]

snake.rules = [
    XRequest('//div[@class="book-img-box"]/a/@href', model=BookInfo)
]


@snake.Middleware('request')
async def sleep(request):
    # await asyncio.sleep(5)
    return request


snake.async_limit = 15

if __name__ == '__main__':
    snake.run()
