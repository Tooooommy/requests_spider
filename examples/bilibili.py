import random
import re
from aiohttp import RequestInfo, ClientResponse, ClientSession, ClientRequest
from requests_spider import Spider, Request, XRequest, Model, XField, RField, Response, Field, asyncio

# 获取某个用户的所有的视频信息 ===> 获取aid / page
videos_url = "https://space.bilibili.com/ajax/member/getSubmitVideos?mid={mid}" \
             "&pagesize=30&tid=0&page={page}&keyword=&order=pubdate"

# 某个视频推荐的视频  ===> 获取aid
recommend_url = "https://comment.bilibili.com/playtag,{cid}-{aid}?html5=1"

# 用户信息 post csrf/mid
user_url = "https://space.bilibili.com/ajax/member/GetInfo"

# av页面，====> 获取下载视频的url、cid-aid, mid
av_url = "https://www.bilibili.com/video/av{aid}"


class AV(Model):
    urls = RField(rule='"url":"(.*?)","backup_url"', first=False)
    cid = RField(rule='cid=(.*?)&aid=')
    aid = RField(rule='&aid=(.*?)&pre_ad=')
    mid = RField(rule='"owner":{"mid":(.*?),')

    async def process(self, response: Response):
        print(self['urls'])
        print(self['cid'])
        print(self['aid'])
        print(self['mid'])
        print(self.json())
        if self['mid'] and self['aid'] and self['urls'] and self['cid']:
            # 推荐视频
            yield Request(url=recommend_url.format(cid=self['cid'], aid=self['aid']), model=Recommend)

            # 用户信息
            yield Request(url=user_url, method='POST', data={'csrf': '', 'mid': self['mid']},
                          model=UserInfo, not_filter=True)

            # 下载视频
            for order, url in enumerate(self['urls']):
                yield Request(url=url.replace('http', 'https'),
                              meta={'name': self['aid'] + '_' + str(order)}, model=Video)


class UserInfo(Model):
    mid = Field()
    name = Field()
    sex = Field()
    rank = Field()
    face = Field()
    regtime = Field()
    birthday = Field()
    sign = Field()
    level_info = Field()

    async def process(self, response: Response):
        status = response.json().get('status')
        if status:
            data = response.json().get('data')
            for k in self.keys():
                if k in data:
                    self[k] = data[k]
            with open('user_' + str(self['mid']) + '.txt', 'w') as f:
                f.write(self.dumps() + '\n')


class Recommend(Model):

    async def process(self, response: Response):
        for data in response.json():
            yield Request(av_url.format(aid=data[1]), model=AV)


class VideoInfo(Model):

    async def process(self, response: Response):
        status = response.json().get('status')
        if status:
            data = response.json().get('data')
            pattern = 'mid=(\d+?)&pagesize=30&tid=0&page=(\d+?)&keyword=&order=pubdate'
            patn = re.findall(pattern, response.url)[0]
            print(patn)
            yield Request(url=videos_url.format(mid=patn[0], page=int(patn[1]) + 1), model=VideoInfo),
            for v in data['vlist']:
                yield Request(url=av_url.format(aid=v.get('aid')), model=AV)


class Video(Model):

    async def process(self, response: Response):
        file_name = response.current_request.meta.get('name')
        if file_name and response.status_code == 200:
            with open(file_name + '.mp4', 'wb') as f:
                for content in response.iter_content(chunk_size=512):
                    f.write(content)
                    f.flush()


snake = Spider('bilibili', workers=5)

snake.init_requests = [
    Request(url=videos_url.format(mid='35789774', page=1), model=VideoInfo),
]
snake.async_limit = 5


@snake.Middleware('request')
async def test(request):
    print(request.url)
    if request.url.startswith('https://space.bilibili.com/'):
        request.info.update({'headers': {'Referer': 'https://space.bilibili.com/'}})
    else:
        request.info.update({'headers': {'Referer': 'https://bilibili.com/'}})

    asyncio.sleep(round(random.random() * 5))
    return request


if __name__ == '__main__':
    snake.run()
