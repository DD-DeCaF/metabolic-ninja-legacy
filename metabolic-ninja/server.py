from aiohttp import web
from aiozmq import rpc
import asyncio
import logging
from itertools import count

logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

client = None


class IDGenerator(object):
    counter = count(1)

    @classmethod
    def next(cls):
        return next(cls.counter)


@asyncio.coroutine
def hello(request):
    product = request.GET['product']
    pathways = yield from client.call.predict_pathways(product, IDGenerator.next())
    return web.Response(text=pathways)


@asyncio.coroutine
def progress(request):
    data = yield from request.json()
    logger.info(data)
    return web.HTTPOk()


app = web.Application()
app.router.add_route('GET', '/', hello)
app.router.add_route('POST', '/progress', progress)


@asyncio.coroutine
def server(loop):
    global client
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass