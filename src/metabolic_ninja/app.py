# Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import copy
from datetime import datetime, timedelta
import time
import asyncio
import requests
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
from metabolic_ninja.middleware import raven_middleware
from metabolic_ninja.healthz import healthz
from . import raven_client


logger = logging.getLogger(__name__)

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
        id=metabolite.id,
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
    loop = asyncio.get_event_loop()
    loop.create_task(predict_pathways(mongo_client.key))


def bigg_ids(object_ids):
    query = json.dumps({'ids': object_ids, 'dbFrom': 'mnx', 'dbTo': 'bigg', 'type': 'Metabolite'})
    r = requests.post(os.environ['ID_MAPPER_API'], data=query)
    return r.json()['ids']


def append_pathway(mongo_client, pathway):
    logger.debug("Pathway is ready, adding to mongo: {}".format(mongo_client.key))
    pathway = map_metabolites_ids_to_bigg(pathway)
    pathway_graph = PathwayGraph(pathway, mongo_client.product_id)
    reactions_list = [reaction_to_dict(reaction) for reaction in pathway_graph.sorted_reactions]
    primary_nodes = [metabolite_to_dict(metabolite) for metabolite in pathway_graph.sorted_primary_nodes]
    mongo_client.append_pathway(reactions_list, pathway_to_model(pathway), primary_nodes)


def map_metabolites_ids_to_bigg(pathway_original):
    pathway = copy.deepcopy(pathway_original)
    all_met_ids = bigg_ids(
        [met.id for reaction in pathway.reactions for met in
         reaction.metabolites])
    for reaction in pathway.reactions:
        for metabolite in reaction.metabolites:
            metabolite.id = all_met_ids[metabolite.id][0] + '_c' \
                if metabolite.id in all_met_ids else metabolite.id
    return pathway


async def run_predictor(request):
    key = {attr: request.GET[attr] for attr in ('product_id', 'model_id', 'universal_model_id', 'carbon_source_id')}
    product_exists = MongoDB(mongo_client=MONGO_CLIENT).is_available(**key)
    if not product_exists:
        return web.HTTPNotFound(text="No such key")
    mongo_client = PathwayCollection(key, mongo_client=MONGO_CLIENT)
    product_document = mongo_client.find()
    logger.info("New prediction request: {}".format(key))

    if prediction_is_ready(product_document):
        logger.debug("Cached prediction already exists: {}".format(key))
        return web.HTTPOk(text="Ready")

    if prediction_has_failed(product_document):
        logger.debug("Prediction has failed; restarting: {}".format(key))
        mongo_client.remove()
        start_prediction(mongo_client)
        return web.HTTPAccepted(text="Prediction failed, restarting")

    if not product_document:
        logger.debug("Starting new prediction: {}".format(key))
        start_prediction(mongo_client)
        return web.HTTPAccepted(text="Accepted")
    else:
        logger.debug("Prediction already in progress (or not yet timed out): {}".format(key))
        return web.HTTPAccepted(text="Already in progress (or not yet timed out)")


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


async def predict_pathways(key: dict):
    t = time.time()
    logger.info("Starting prediction job: {}".format(key))
    mongo_client = PathwayCollection(key, mongo_client=MONGO_CLIENT)
    mongo_client.pathways.create_index([(k, ASCENDING) for k in key])
    try:
        logger.debug("Getting predictor: {}".format(key))
        predictor = get_predictor(mongo_client.model_id, mongo_client.universal_model_id)
        logger.debug("Starting pathway prediction: {}".format(key))
        predictor.run(
            product=mongo_client.product_id,
            max_predictions=MAX_PREDICTIONS,
            callback=partial(append_pathway, mongo_client),
        )
    except Exception:
        raven_client.captureException()
        logger.error("Error during pathway prediction; removing key from mongodb: {}".format(key))
        mongo_client.remove()
        raise
    else:
        logger.debug("Prediction complete in {:.2f}s: {}".format(time.time() - t, key))
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


app = web.Application(middlewares=[raven_middleware])
app.router.add_route('GET', '/pathways/healthz', healthz)
app.router.add_route('GET', '/pathways/predict', run_predictor)
app.router.add_route('GET', '/pathways/ws', ws_handler)
app.router.add_route('GET', '/pathways/pathways', pathways)
app.router.add_route('GET', '/pathways/lists/product', product_list)
app.router.add_route('GET', '/pathways/lists/model', model_list)
app.router.add_route('GET', '/pathways/lists/universal_model', universal_model_list)
app.router.add_route('GET', '/pathways/lists/carbon_source', carbon_source_list)


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
    await loop.create_server(app.make_handler(), '0.0.0.0', 8000)
    logger.debug('Web server is up')


if __name__ == '__main__':
    # Put the most used predictor to memory
    get_predictor('iJO1366', 'metanetx_universal_model_bigg')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
