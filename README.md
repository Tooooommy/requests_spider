<div align=center>
<img src="./spider.png">
</div>

## 描述
requests_spider 是一个轻量级的异步爬虫框架，基于requests_html进行二次开发，类似flask

## 安装
pip install requests_spider

## 依赖
python: > 3.6
uvloop
requests_html

## 用法
##### 基础例子
```python3
import json
from spider import XField, Spider, Model, Response, Request


class Proxy(Model):
    ip = XField(rule='//tr[contains(@class, "odd")]/td[2]', first=False)
    port = XField(rule='//tr[contains(@class, "odd")]/td[3]', first=False)

    async def process(self, response: Response):
        with open('proxy1.txt', 'a+') as file:
            for result in self.merge():
                file.write(json.dumps(result) + '\n')


spider = Spider('proxy', workers=15)
spider.domains = ['www.xicidaili.com']
spider.init_requests = [
    Request(url='http://www.xicidaili.com/nn/{}'.format(x), model=Proxy) for x in range(1, 10)
]

spider.async_limit = 5

if __name__ == '__main__':
    spider.run()

```
爬取代理网站ip

##### 中间组件
```python3
import random
import re

from spider import Spider, Request, XRequest, Model, XField, RField, Response, Field, asyncio

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


spider = Spider('bilibili', workers=5)

spider.init_requests = [
    Request(url=videos_url.format(mid='35789774', page=1), model=VideoInfo),
]
spider.async_limit = 5


@spider.Middleware('request')
async def test(request):
    print(request.url)
    if request.url.startswith('https://space.bilibili.com/'):
        request.info.update({'headers': {'Referer': 'https://space.bilibili.com/'}})
    else:
        request.info.update({'headers': {'Referer': 'https://bilibili.com/'}})

    asyncio.sleep(round(random.random() * 5))
    return request


if __name__ == '__main__':
    spider.run()
```
爬取bilibili用户视频，用户资料，视频资料，利用中间组件进行切换headers

## API
#### Spider
继承requests_html的HTMLSession

- **Spider.async_limit**

    利用asyncio.Semaphore限制并发数量


- **Spider.queue_timeout**

    从队列获取数据时候超时设置

- **Spider.request_depth**

    请求的深度

- **Spider.init_requests**

    初始化请求

- **Spider.domains**

    爬取域名设置

- **Spider.rules**

    从响应的数据中获取下次请求的信息，并加入队列

- **Spider.Middleware**

    中间组件
    Middleware('request'), request入队之前执行，返回request, response, None
    Middleware('response'), response入队之前，返回request, response, None


##### Model
Model类似一个字典的数据模型

- **Model.keys**

    类似字典的keys

- **Model.values**

    类似字典的values

- **Model.items**

    类似字典的items

- **Model.json**

    获取所有Field的字典形式

- **Model.dumps**

    获取所有的Field的字符串

- **Model.merge**

    当所有的Field从响应数据获取的数据是列表的时候，将获取的列表合并成为json数据

- **Model.process**

    处理响应数据


##### Field

- **Field**

    不处理或待处理数据项

- **XField**

    利用xpath从响应数据中获取数据

- **CField**

    利用css获取数据

- **RField**

    利用正则获取数据

##### Request

- **Request**
    正常的请求

- **XRequest**

    利用xpath, 用于Spider.rules

- **RRequest**

    利用正则，用于Spider.rules



## 例子
examples目录下
bilibili.py 爬取哔哩哔哩用户信息、视频信息和视频
qidian.py 爬取起点小说月票排行包括评分
proxy.py 爬取代理ip网站代理
pearvideo.py 爬取梨视频网站的视频

# License
MIT