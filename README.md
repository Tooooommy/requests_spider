<div align=center>
<img src="./spider.png">
</div>

## 描述
requests_spider 是一个轻量级的异步爬虫框架，基于requests_html进行二次开发

## 安装
pip install requests_spider

## 依赖
python: >= 3.6
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
    Request(url='http://www.xicidaili.com/nn/{}'.format(x), callback=Proxy) for x in range(1, 10)
]

spider.async_limit = 5

if __name__ == '__main__':
    spider.run()

```


## API
#### Spider
爬虫主要类： spider =Spider('name'), 继承requests_html

- **Spider.async_limit**

    利用asyncio.Semaphore限制并发数量


- **Spider.queue_timeout**

    从队列获取数据时候超时设置

- **Spider.init_requests**

    初始化请求

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

##### Rule
每次爬取的时候进行链接规则抓取

- **XRule**
    利用xpath, 用于Spider.rules

- **RRule**
    利用正则，用于Spider.rules



## 例子
examples目录下

user.py 抓取哔哩哔哩的用户信息， 根据某个用户的关注者和被关注者

video.py 抓取某个用户的所有投稿视频

bilibili.py 爬取哔哩哔哩用户信息、视频信息和视频

qidian.py 爬取起点小说月票排行包括评分

proxy.py 爬取代理ip网站代理

pearvideo.py 爬取梨视频网站的视频

# License
MIT