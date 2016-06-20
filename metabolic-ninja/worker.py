import asyncio
import os
import sys
import traceback
from functools import partial
from collections import defaultdict
from aiozmq import rpc
from utils import get_predictor, metabolite_to_dict, reaction_to_dict, pathway_to_model, logger
from pathway_graph import PathwayGraph
from mongo_client import MongoDB, PathwayCollection
from cameo import models


MAX_PREDICTIONS = 10


def append_pathway(mongo_client, pathway):
    logger.debug("{}: pathway is ready, add to mongo".format(mongo_client.key))
    pathway_graph = PathwayGraph(pathway, mongo_client.product_id)
    reactions_list = [reaction_to_dict(reaction) for reaction in pathway_graph.sorted_reactions]
    primary_nodes = [metabolite_to_dict(metabolite) for metabolite in pathway_graph.sorted_primary_nodes]
    mongo_client.append_pathway(reactions_list, pathway_to_model(pathway), primary_nodes)


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, key: dict):
        mongo_client = PathwayCollection(**key)
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

    @rpc.method
    def create_list_of_models(self):
        logger.debug("Creating models list")
        MongoDB().insert_models_list(
            [{
                 'id': row.bigg_id,
                 'name': row.organism,
             } for index, row in models.index_models_bigg().iterrows()]
        )

    @rpc.method
    def create_list_of_universal_models(self):
        logger.debug("Creating universal models list")
        MongoDB().insert_universal_models_list([{'id': key, 'name': key} for key in vars(models.universal).keys()])

    @rpc.method
    def create_list_of_carbon_sources(self):
        logger.debug("Creating models list")
        carbon_sources = ['EX_glc_lp_e_rp_']
        MongoDB().insert_carbon_sources_list(
            [{
                 'id': source,
                 'name': source,
             } for source in carbon_sources]
        )

    @rpc.method
    def create_list_of_products(self):
        logger.debug("Creating products list")
        all_products = defaultdict(lambda: [])
        for universal_model in vars(models.universal).keys():
            for product in getattr(models.universal, universal_model).metabolites:
                all_products[product].append(universal_model)
        MongoDB().insert_product_list(
            [{
                 'id': k.id,
                 'name': k.name,
                 'universal_models': v
             } for k, v in all_products.items()]
        )


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect=os.environ['SERVER_PORT_5555_TCP'])
    logger.debug("Serving RPC on {}".format(os.environ['SERVER_PORT_5555_TCP']))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
