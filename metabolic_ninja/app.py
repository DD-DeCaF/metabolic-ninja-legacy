import logging
from datetime import datetime, timedelta
import asyncio
import sys
import traceback
import json
from copy import deepcopy
from functools import partial
import aiohttp_cors
import cobra
from aiohttp import web, WSMsgType
from pymongo import MongoClient, ASCENDING
from metabolic_ninja.pathway_graph import PathwayGraph
from metabolic_ninja.mongo_client import MongoDB, PathwayCollection, MONGO_CRED
from metabolic_ninja.pickle_predictors import get_predictor


logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

MAX_PREDICTIONS = 10

TIMEOUT = timedelta(minutes=30)


MONGO_CLIENT = MongoClient(*MONGO_CRED, maxPoolSize=None)


def pathway_to_model(pathway):
    model = cobra.Model('test')
    model.add_reactions(deepcopy(list(pathway.reactions)))
    return json.loads(cobra.io.to_json(model))


def pathway_to_list(pathway):
    return [reaction_to_dict(reaction) for reaction in pathway.reactions]


def reaction_to_dict(reaction):
    return dict(
        id=reaction.id,
        name=reaction.name,
        reaction_string=reaction.build_reaction_string(use_metabolite_names=True),
    )


def metabolite_to_dict(metabolite):
    return dict(
        id=metabolite.nice_id,
        name=metabolite.name,
        formula=metabolite.formula,
    )


def prediction_has_failed(product_document):
    return product_document and (not product_document['ready']) and \
           (datetime.now() - product_document['updated'] >= TIMEOUT)


def prediction_is_ready(product_document):
    return product_document and product_document['ready']


def start_prediction(mongo_client):
    mongo_client.upsert()
    predict_pathways(mongo_client.key)


def append_pathway(mongo_client, pathway):
    logger.debug("{}: pathway is ready, add to mongo".format(mongo_client.key))
    pathway_graph = PathwayGraph(pathway, mongo_client.product_id)
    reactions_list = [reaction_to_dict(reaction) for reaction in pathway_graph.sorted_reactions]
    primary_nodes = [metabolite_to_dict(metabolite) for metabolite in pathway_graph.sorted_primary_nodes]
    mongo_client.append_pathway(reactions_list, pathway_to_model(pathway), primary_nodes)


async def run_predictor(request):
    key = {attr: request.GET[attr] for attr in ('product_id', 'model_id', 'universal_model_id', 'carbon_source_id')}
    product_exists = MongoDB(mongo_client=MONGO_CLIENT).is_available(**key)
    if not product_exists:
        return web.HTTPNotFound(text="No such key")
    mongo_client = PathwayCollection(key, mongo_client=MONGO_CLIENT)
    product_document = mongo_client.find()
    logger.info(get_predictor.cache_info())
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


async def pathways(request):
    key = {attr: request.GET[attr] for attr in ('product_id', 'model_id', 'universal_model_id', 'carbon_source_id')}
    mongo_client = PathwayCollection(key, mongo_client=MONGO_CLIENT)
    product_document = mongo_client.find()
    result = []
    if product_document:
        result = product_document['pathways']
    return web.json_response(result)


def json_response(collection):
    return web.json_response([{'id': m['_id'], 'name': m['name']} for m in collection])


async def universal_model_list(request):
    return json_response(MongoDB(mongo_client=MONGO_CLIENT).universal_models.find())


async def carbon_source_list(request):
    return json_response(MongoDB(mongo_client=MONGO_CLIENT).carbon_sources.find())


async def model_list(request):
    return json_response(MongoDB(mongo_client=MONGO_CLIENT).models.find())


async def product_list(request):
    universal_model = request.GET['universal_model_id']
    return json_response(MongoDB(mongo_client=MONGO_CLIENT).products.find({'universal_models': {'$in': [universal_model]}}))


def predict_pathways(key: dict):
    logger.info(get_predictor.cache_info())
    mongo_client = PathwayCollection(key, mongo_client=MONGO_CLIENT)
    mongo_client.pathways.create_index([(k, ASCENDING) for k in key])
    try:
        predictor = get_predictor(mongo_client.model_id, mongo_client.universal_model_id)
        logger.debug("Starting pathway prediction: {}".format(mongo_client.key))
        predictor.run(
            product=mongo_client.product_id,
            max_predictions=MAX_PREDICTIONS,
            callback=partial(append_pathway, mongo_client),
        )
    except:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        logger.debug("Error occured. Remove {}".format(mongo_client.key))
        mongo_client.remove()
        raise
    else:
        logger.debug("Ready: {}".format(mongo_client.key))
        mongo_client.set_ready()


async def ws_handler(request):
    logger.info(get_predictor.cache_info())
    mongodb = MongoDB(mongo_client=MONGO_CLIENT)
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    try:
        # send updated list of pathways on demand
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    key = msg.json()
                    product_exists = mongodb.is_available(**key)
                    if not product_exists:
                        ws.send_json(dict(error=404, message='No such key'))
                    pathway_coll = PathwayCollection(key, mongo_client=MONGO_CLIENT)
                    document = pathway_coll.find()
                    pathways_in_db = []
                    is_ready = False
                    if document:
                        pathways_in_db = document['pathways']
                        is_ready = document['ready']
                    ws.send_json(
                        dict(pathways=pathways_in_db, is_ready=is_ready))
            elif msg.type == WSMsgType.ERROR:
                logger.error('Websocket closed with exception {}'.format(ws.exception()))
    except asyncio.CancelledError:
        logger.info('Websocket is cancelled')
    await ws.close()
    return ws


app = web.Application()
API_PREFIX = '/pathways'
LISTS_PREFIX = API_PREFIX + '/lists'
app.router.add_route('GET', API_PREFIX + '/predict', run_predictor)
app.router.add_route('GET', API_PREFIX + '/ws', ws_handler)
app.router.add_route('GET', API_PREFIX + '/pathways', pathways)
app.router.add_route('GET', LISTS_PREFIX + '/product', product_list)
app.router.add_route('GET', LISTS_PREFIX + '/model', model_list)
app.router.add_route('GET', LISTS_PREFIX + '/universal_model', universal_model_list)
app.router.add_route('GET', LISTS_PREFIX + '/carbon_source', carbon_source_list)

# Put the most used predictor to memory
get_predictor('iJO1366', 'metanetx_universal_model_bigg')

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

async def start(loop):
    await loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    logger.debug('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
