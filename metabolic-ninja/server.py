from aiohttp import web
from aiozmq import rpc
from motor import motor_asyncio
import os
import asyncio
import logging

logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

client = None


@asyncio.coroutine
def run_predictor(request):
    product = request.GET['product']
    product_document = yield from mongo_client.db.ecoli.find_one({'_id': product})
    if product_document and product_document["ready"]:
        return web.HTTPOk(text="Ready")
    if not product_document:
        client.call.predict_pathways(product)
    return web.HTTPAccepted(text="Accepted")


@asyncio.coroutine
def pathways(request):
    product = request.GET['product']
    product_document = yield from mongo_client.db.ecoli.find_one({'_id': product})
    result = []
    if product_document:
        result = product_document['pathways']
    return web.json_response(result)


app = web.Application()
app.router.add_route('GET', '/', run_predictor)
app.router.add_route('GET', '/pathways', pathways)


@asyncio.coroutine
def server(loop):
    global client
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)


if __name__ == '__main__':
    mongo_client = motor_asyncio.AsyncIOMotorClient(os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
