import re
import pymongo
from examples.settings import MONGO_DB, MONGO_URI
from requests_spider import Spider, Request, Model, Response, Field

user_url = 'https://space.bilibili.com/ajax/member/GetInfo'

follower_url = 'https://api.bilibili.com/x/relation/followers?vmid={mid}&pn={page}&ps=20&' \
               'order=desc&jsonp=jsonp'

followed_url = 'https://api.bilibili.com/x/relation/followings?vmid={mid}&pn={page}&ps=20&' \
               'order=desc&jsonp=jsonp'

rf = 'https://space.bilibili.com/'
ua = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'

init_mids = ['35789774', '122879', '3488061', '25595576', '656068', '2515236']

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]


class UserInfo(Model):
    mid = Field()
    name = Field()
    sex = Field()
    rank = Field()
    face = Field()
    regtime = Field()
    birthday = Field()
    sign = Field()
    level = Field()

    async def process(self, response: Response):
        if response.status_code == 200:
            result = response.json()
            if result['status']:
                for key in self.keys():
                    if key in result['data']:
                        self[key] = result['data'][key]
                self['level'] = result['data']['level_info']['current_level']
                db['user'].update_one({'mid': self['mid']}, {"$set": self.json()}, True)
                yield Request(url=followed_url.format(mid=result['data']['mid'], page=1), callback=follow)
                yield Request(url=follower_url.format(mid=result['data']['mid'], page=1), callback=follow)


async def follow(response):
    if response.status_code == 200:
        result = response.json()
        if result['code'] == 0:
            params = re.findall('x/relation/(.*?)\?vmid=(.*?)&pn=(.*?)&ps', response.url)[0]
            if params[0] == 'followings':
                yield Request(url=followed_url.format(mid=params[1], page=int(params[2]) + 1), callback=follow)
            elif params[0] == 'followers':
                yield Request(url=follower_url.format(mid=params[1], page=int(params[2]) + 1), callback=follow)
            for data in result['data']['list']:
                form_data = {'csrf': '', 'mid': data['mid']}
                yield Request(url=user_url, method='post', data=form_data, form_filter=form_data, callback=UserInfo)


def set_init_requests():
    for init_mid in init_mids:
        init_data = {'csrf': None, 'mid': init_mid}
        yield Request(url=follower_url.format(mid=init_mid, page=1), callback=follow)
        yield Request(url=followed_url.format(mid=init_mid, page=1), callback=follow)
        yield Request(url=user_url, method='post', data=init_data, form_filter=init_data, callback=UserInfo)


spider = Spider('bilibili_user', workers=4)
spider.async_limit = 4
spider.queue_timeout = 8
spider.init_requests = [x for x in set_init_requests()]


@spider.Middleware('request')
async def set_headers(request: Request):
    request.info.update({'headers': {'Referer': rf, 'UserAgent': ua}})
    # await asyncio.sleep(4)
    return request


if __name__ == '__main__':
    spider.run()
    client.close()
