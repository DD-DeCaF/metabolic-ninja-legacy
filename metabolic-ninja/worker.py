import asyncio
import os
import sys
import traceback
from functools import partial
from aiozmq import rpc
from utils import get_predictor, metabolite_to_dict, reaction_to_dict, pathway_to_model, logger
from pathway_graph import PathwayGraph
from mongo_client import MongoDB, ModelMongoDB
from cameo import models


MAX_PREDICTIONS = 10


def append_pathway(mongo_client, product, pathway):
    logger.debug("Pathway for product {} is ready, add to mongo".format(product))
    pathway_graph = PathwayGraph(pathway, product)
    reactions_list = [reaction_to_dict(reaction) for reaction in pathway_graph.sorted_reactions]
    primary_nodes = [metabolite_to_dict(metabolite) for metabolite in pathway_graph.sorted_primary_nodes]
    mongo_client.append_pathway(product, reactions_list, pathway_to_model(pathway), primary_nodes)


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, product: str, model_id: str):
        mongo_client = ModelMongoDB(model_id)
        try:
            predictor = get_predictor(model_id)
            logger.debug("Starting pathway prediction for {}".format(product))
            predictor.run(
                product=product,
                max_predictions=MAX_PREDICTIONS,
                callback=partial(append_pathway, mongo_client, product),
            )
        except:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            logger.debug("Error occured. Remove {} from database".format(product))
            mongo_client.remove(product)
            raise
        else:
            logger.debug("Product {} is ready".format(product))
            mongo_client.set_ready(product)

    @rpc.method
    def create_list_of_models(self):
        logger.debug("Creating models list")
        MongoDB().insert_models_list(models.index_models_bigg())

    @rpc.method
    def create_list_of_products(self):
        logger.debug("Creating products list")
        MongoDB().insert_product_list(models.universal.metanetx_universal_model_bigg_rhea_kegg_brenda.metabolites)


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect=os.environ['SERVER_PORT_5555_TCP'])
    logger.debug("Serving RPC on {}".format(os.environ['SERVER_PORT_5555_TCP']))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
