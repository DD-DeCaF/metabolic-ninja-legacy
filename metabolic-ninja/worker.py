import asyncio
import os
import sys
import traceback
from functools import partial
from aiozmq import rpc
from utils import get_predictor, pathway_to_list, pathway_to_model, logger
from mongo_client import MongoDB


MAX_PREDICTIONS = 10


def append_pathway(product, pathway):
    logger.debug("Pathway for product {} is ready, add to mongo".format(product))
    mongo_client.append_pathway(product, pathway_to_list(pathway), pathway_to_model(pathway))


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, product: str):
        try:
            predictor = get_predictor()
            logger.debug("Starting pathway prediction for {}".format(product))
            predictor.run(
                product=product,
                max_predictions=MAX_PREDICTIONS,
                callback=partial(append_pathway, product),
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
    def create_list_of_products(self):
        logger.debug("Creating products list")
        mongo_client.insert_product_list(get_predictor().universal_model.metabolites)


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect=os.environ['SERVER_PORT_5555_TCP'])
    logger.debug("Serving RPC on {}".format(os.environ['SERVER_PORT_5555_TCP']))

if __name__ == '__main__':
    mongo_client = MongoDB(os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
