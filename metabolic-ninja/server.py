from aiohttp import web
from aiozmq import rpc
from mongo_client import MongoDB
import json
import asyncio
import logging

logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

client = None


@asyncio.coroutine
def run_predictor(request):
    product = request.GET['product']
    exists = mongo_client.exists(product)
    if exists and mongo_client.is_ready(product):
        return web.HTTPOk(text="Ready")
    if not exists:
        client.call.predict_pathways(product)
    return web.HTTPAccepted(text="Request is accepted")


@asyncio.coroutine
def pathways(request):
    product = request.GET['product']
    result = []
    if mongo_client.exists(product):
        result = mongo_client.get(product)['pathways']
    return web.HTTPOk(text=json.dumps(result))


app = web.Application()
app.router.add_route('GET', '/', run_predictor)
app.router.add_route('GET', '/pathways', pathways)


@asyncio.coroutine
def server(loop):
    global client
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)


if __name__ == '__main__':
    mongo_client = MongoDB()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
