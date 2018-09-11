import pymongo
from requests_spider import Spider, Model, Request, XRule, Response, CField, XField, Field, RField, asyncio
from fontTools import BytesIO
from fontTools.ttLib import TTFont
from examples.settings import MONGO_DB, MONGO_URI

rank_url = 'https://www.qidian.com/rank/yuepiao?style={}&page={}'
score_url = 'https://book.qidian.com/ajax/comment/index?_csrfToken={}&bookId={}&pageSize=15'
font_url = 'https://qidian.gtimg.com/qd_anti_spider/{}.woff'

num_dict = {"six": "6", "three": "3", "period": ".", "eight": "8", "zero": "0",
            "five": "5", "nine": "9", "four": "4", "seven": '7', "one": "1", "two": "2"}

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]


async def get_nums(font_type, font_str):
    # print(font_str.encode('unicode-escape'))
    response = await spider.get(url=font_url.format(font_type))
    font = response.content
    ttfont = TTFont(BytesIO(font))
    mappings = {hex(k)[2:]: num_dict.get(v) for k, v in ttfont.getBestCmap().items()}
    # print(mappings)
    items = font_str.encode('unicode-escape').split(b'\\U000')[1:]
    return "".join([mappings.get(item.decode('utf8')) for item in items])


class BookScore(Model):
    id = Field()
    score = Field()
    count = Field()

    async def process(self, response: Response):
        data = response.json()['data']
        self['score'] = str(data['rate'])
        self['count'] = str(data['userCount'])
        self['id'] = response.current_request.meta.get('bookid')
        # print(response.current_request.meta)
        data = self.json()
        print(data)
        db['qidian'].update_one({'id': self['id']}, {"$set": dict(self.json())}, True)


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
        self['img'] = 'https:' + self['img'][:-1]
        data = self.json()
        print(data)
        db['qidian'].update_one({'id': self['id']}, {"$set": dict(self.json())}, True)
        yield Request(score_url.format(spider.cookies.get('_csrfToken'), self['id']),
                      callback=BookScore, meta={'bookid': self['id']})


spider = Spider(name='one', workers=4)
spider.domains = ['book.qidian.com', 'www.qidian.com']
spider.init_requests = [
    Request(rank_url.format(1, page)) for page in range(1, 2)
]

spider.rules = [
    XRule(rule='//div[@class="book-img-box"]/a/@href', callback=BookInfo)
]


@spider.Middleware('request')
async def sleep(request):
    # await asyncio.sleep(5)
    return request


@spider.Middleware('response')
async def set_error_code(response):
    print(response.status_code)
    print(response.url)
    if response.status_code != 200:
        return None
    return response


if __name__ == '__main__':
    spider.run()
