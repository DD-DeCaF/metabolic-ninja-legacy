import asyncio
import aiohttp_cors
import logging
from datetime import datetime, timedelta
from aiohttp import web
from aiozmq import rpc
from mongo_client import MongoDB, PathwayCollection

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


def start_prediction(mongo_client):
    mongo_client.upsert()
    client.call.predict_pathways(mongo_client.key)


@asyncio.coroutine
def run_predictor(request):
    key = {attr: request.GET[attr] for attr in ('product_id', 'model_id', 'universal_model_id', 'carbon_source_id')}
    product_exists = MongoDB().is_available(**key)
    if not product_exists:
        return web.HTTPNotFound(text="No such key")

    mongo_client = PathwayCollection(key)
    product_document = mongo_client.find()
    if prediction_is_ready(product_document):
        logger.debug("Ready: {}".format(key))
        return web.HTTPOk(text="Ready")
    if prediction_has_failed(product_document):
        mongo_client.remove()
        start_prediction(mongo_client)
        logger.debug("Prediction for {} is failed, restarting".format(key))
        return web.HTTPAccepted(text="Prediction failed, restarting")
    if not product_document:
        start_prediction(mongo_client)
        logger.debug("Call prediction for {}".format(key))
    return web.HTTPAccepted(text="Accepted")


@asyncio.coroutine
def pathways(request):
    key = {attr: request.GET[attr] for attr in ('product_id', 'model_id', 'universal_model_id', 'carbon_source_id')}
    mongo_client = PathwayCollection(key)
    product_document = mongo_client.find()
    result = []
    if product_document:
        result = product_document['pathways']
    return web.json_response(result)


def json_response(collection):
    return web.json_response([{'id': m['_id'], 'name': m['name']} for m in collection])


@asyncio.coroutine
def universal_model_list(request):
    return json_response(MongoDB().universal_models.find())


@asyncio.coroutine
def carbon_source_list(request):
    return json_response(MongoDB().carbon_sources.find())


@asyncio.coroutine
def model_list(request):
    return json_response(MongoDB().models.find())


@asyncio.coroutine
def product_list(request):
    universal_model = request.GET['universal_model_id']

    def has_prediction(product_id):
        key = dict(
            universal_model_id=universal_model,
            model_id='iJO1366',
            product_id=product_id,
            carbon_source_id='EX_glc_lp_e_rp_',
        )
        mongo_client = PathwayCollection(key)
        return prediction_is_ready(mongo_client.find())

    return json_response(
        [m for m in
         MongoDB().products.find({'universal_models': {'$in': [universal_model]}})
         if has_prediction(m['_id'])]
    )


app = web.Application()
API_PREFIX = '/pathways'
LISTS_PREFIX = API_PREFIX + '/lists'
app.router.add_route('GET', API_PREFIX + '/predict', run_predictor)
app.router.add_route('GET', API_PREFIX + '/pathways', pathways)
app.router.add_route('GET', LISTS_PREFIX + '/product', product_list)
app.router.add_route('GET', LISTS_PREFIX + '/model', model_list)
app.router.add_route('GET', LISTS_PREFIX + '/universal_model', universal_model_list)
app.router.add_route('GET', LISTS_PREFIX + '/carbon_source', carbon_source_list)

# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
})

# Configure CORS on all routes.
for route in list(app.router.routes()):
    cors.add(route)


@asyncio.coroutine
def start(loop):
    global client
    logger.debug('Connect to RPC server')
    client = yield from rpc.connect_rpc(bind='tcp://0.0.0.0:5555')
    # logger.debug('Calling for list of models')
    # yield from client.call.create_list_of_models()
    # logger.debug('Calling for list of universal models')
    # yield from client.call.create_list_of_universal_models()
    # logger.debug('Calling for list of products')
    # yield from client.call.create_list_of_products()
    logger.debug('Calling for list of carbon sources')
    yield from client.call.create_list_of_carbon_sources()
    logger.debug('Starting web server')
    yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    logger.debug('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
