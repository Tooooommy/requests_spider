import pickle
from asyncio import Queue


class Squeue(Queue):
    def __init__(self, maxsize=0, *, loop=None):
        super().__init__(maxsize=maxsize, loop=loop)

    async def dumps(self, item):
        item = pickle.dumps(item)
        await self.put(item)

    async def loads(self):
        item = await self.get()
        return pickle.loads(item)

    def dumps_nowait(self, item):
        item = pickle.dumps(item)
        self.put_nowait(item)

    def loads_nowait(self):
        item = self.get_nowait()
        return pickle.loads(item)


if __name__ == '__main__':
    from requests_spider import Request, Response
    from requests_spider import Model
    from requests_spider import Field


    class m(Model):
        a = Field()
        _b = 111

        async def process(self, response: Response):
            print(response)


    r = Request(url='https://www.baidu.com', model=m)

    q = Squeue()
    r.__dict__.update({'_love': 11})
    q.dumps_nowait(r)
    re = q.loads_nowait()
    print(re.__dict__)
