import pymongo
from requests_spider import Spider, Request, Model, Response, asyncio, RField, re, json, XField
from examples.settings import MONGO_DB, MONGO_URI

#
video_url = 'https://space.bilibili.com/ajax/member/getSubmitVideos?mid={}&pagesize=30&tid=0&page={}&keyword' \
            '=&order=pubdate '

av_url = 'https://www.bilibili.com/video/av{aid}'

rf = 'https://space.bilibili.com/'
ua = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]
mids = [35789774]


async def videoinfo(response: Response):
    if response.status_code == 200 and response.json()['status']:
        params = re.findall('mid=(.*?)&pagesize=30&tid=0&page=(.*?)&keyword', response.url)[0]
        yield Request(url=video_url.format(params[0], int(params[1]) + 1), callback=videoinfo)
        data = response.json()['data']['vlist']
        for d in data:
            db['video'].update_one({'aid': d['aid']}, {'$set': d}, True)
            yield Request(url=av_url.format(aid=d['aid']), callback=AVPage)


class AVPage(Model):
    data = RField(rule='<script>window.__playinfo__=(.*?)</script>')
    tags = XField(rule='//ul[contains(@class, "tag-area clearfix")]//li[contains(@class, "tag")]', first=False)

    async def process(self, response: Response):
        if response.status_code == 200:
            durl = json.loads(self['data'])['durl']
            aid = re.findall('https://www.bilibili.com/video/av(.*)', response.url)[0]
            db['video'].update_one({'aid': int(aid)}, {'$set': self.json()})
            print(db['video'].find_one({'aid': int(aid)}))
            for d in durl:
                name = str(aid) + '_' + str(d['order']) + '.mp4'
                yield Request(d['url'], meta={'name': name}, callback=download)


async def download(response: Response):
    if response.status_code == 200:
        chunk_size = 1024
        name = response.current_request.meta.get('name')
        with open(name, 'wb') as f:
            for content in response.iter_content(chunk_size=chunk_size):
                f.write(content)
                f.flush()


spider = Spider('bilibili_video', workers=4)
spider.async_limit = 4
spider.init_requests = [Request(url=video_url.format(mid, 1), callback=videoinfo) for mid in mids]


@spider.Middleware('request')
async def set_headers(request: Request):
    request.info.update({'headers': {'Referer': rf, 'UserAgent': ua}})
    await asyncio.sleep(2)
    return request


if __name__ == '__main__':
    spider.run()
