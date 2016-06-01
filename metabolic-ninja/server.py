import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiohttp import web
from aiozmq import rpc
from motor import motor_asyncio

logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

client = None


TIMEOUT = timedelta(minutes=20)


def prediction_has_failed(product_document):
    return product_document and (not product_document['ready']) and \
           (datetime.now() - product_document['updated'] >= TIMEOUT)


def prediction_is_ready(product_document):
    return product_document and product_document['ready']


@asyncio.coroutine
def run_predictor(request):
    product = request.GET['product']
    product_exists = yield from mongo_client.db.product.find_one(product)
    if not product_exists:
        return web.HTTPNotFound(text="No such product")
    product_document = yield from mongo_client.db.ecoli.find_one(product)
    if prediction_is_ready(product_document):
        return web.HTTPOk(text="Ready")
    if prediction_has_failed(product_document):
        yield from mongo_client.db.ecoli.remove(product)
        client.call.predict_pathways(product)
        return web.HTTPAccepted(text="Prediction failed, restarting")
    if not product_document:
        client.call.predict_pathways(product)
    return web.HTTPAccepted(text="Accepted")


@asyncio.coroutine
def pathways(request):
    product = request.GET['product']
    product_document = yield from mongo_client.db.ecoli.find_one(product)
    result = []
    if product_document:
        result = product_document['pathways']
    return web.json_response(result)


@asyncio.coroutine
def product_list(request):
    result = []
    products_cursor = mongo_client.db.product.find()
    while (yield from products_cursor.fetch_next):
        result.append(products_cursor.next_object()['_id'])
    return web.json_response(result)


app = web.Application()
app.router.add_route('GET', '/', run_predictor)
app.router.add_route('GET', '/pathways', pathways)
app.router.add_route('GET', '/product_list', product_list)


@asyncio.coroutine
def server(loop):
    global client
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    yield from client.call.create_list_of_products()
    logger.debug('Product list is ready')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    logger.debug('Web server is up')


if __name__ == '__main__':
    mongo_client = motor_asyncio.AsyncIOMotorClient(os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
