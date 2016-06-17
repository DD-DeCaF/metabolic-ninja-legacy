import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from aiozmq import rpc
from mongo_client import MongoDB, ModelMongoDB

logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

client = None


TIMEOUT = timedelta(minutes=60)


def prediction_has_failed(product_document):
    return product_document and (not product_document['ready']) and \
           (datetime.now() - product_document['updated'] >= TIMEOUT)


def prediction_is_ready(product_document):
    return product_document and product_document['ready']


def start_prediction(mongo_client, product):
    mongo_client.upsert(product)
    client.call.predict_pathways(product, mongo_client.model_id)


@asyncio.coroutine
def run_predictor(request):
    product = request.GET['product']
    model_id = request.GET['model_id']

    product_exists = MongoDB().product_is_available(product)
    if not product_exists:
        logger.debug("No such product: {}".format(product))
        return web.HTTPNotFound(text="No such product")
    model_exists = MongoDB().model_is_available(model_id)
    if not model_exists:
        logger.debug("No such model: {}".format(model_id))
        return web.HTTPNotFound(text="No such model")

    mongo_client = ModelMongoDB(model_id)
    product_document = mongo_client.find(product)
    if prediction_is_ready(product_document):
        logger.debug("Product {} is ready".format(product))
        return web.HTTPOk(text="Ready")
    if prediction_has_failed(product_document):
        mongo_client.remove(product)
        start_prediction(mongo_client, product)
        logger.debug("Prediction for product {} is failed, restarting".format(product))
        return web.HTTPAccepted(text="Prediction failed, restarting")
    if not product_document:
        start_prediction(mongo_client, product)
        logger.debug("Call prediction for {}".format(product))
    return web.HTTPAccepted(text="Accepted")


@asyncio.coroutine
def pathways(request):
    product = request.GET['product']
    mongo_client = ModelMongoDB(request.GET['model_id'])
    product_document = mongo_client.find(product)
    result = []
    if product_document:
        result = product_document['pathways']
    return web.json_response(result)


@asyncio.coroutine
def model_list(request):
    return web.json_response([{'id': m['_id'], 'name': m['name']} for m in MongoDB().all_models()])


@asyncio.coroutine
def product_list(request):
    return web.json_response([p['_id'] for p in MongoDB().all_products()])


app = web.Application()
API_PREFIX = '/api'
app.router.add_route('GET', API_PREFIX, run_predictor)
app.router.add_route('GET', API_PREFIX + '/pathways', pathways)
app.router.add_route('GET', API_PREFIX + '/product_list', product_list)
app.router.add_route('GET', API_PREFIX + '/model_list', model_list)


@asyncio.coroutine
def start(loop):
    global client
    logger.debug('Connect to RPC server')
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    logger.debug('Calling for list of models')
    yield from client.call.create_list_of_models()
    logger.debug('Model list is ready')
    yield from client.call.create_list_of_products()
    logger.debug('Product list is ready')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    logger.debug('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
