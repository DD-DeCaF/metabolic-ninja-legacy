import asyncio
import os
from functools import partial
from aiozmq import rpc
from utils import get_predictor, pathway_to_list, logger
from mongo_client import MongoDB

MAX_PREDICTIONS = 10


def append_pathway(product, pathway):
    logger.debug("Pathway for product {} is ready, add to mongo".format(product))
    mongo_client.append_pathway(product, pathway_to_list(pathway))


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, product: str):
        mongo_client.upsert(product)
        try:
            logger.debug("Starting pathway prediction for {}".format(product))
            predictor.run(
                product=product,
                max_predictions=MAX_PREDICTIONS,
                callback=partial(append_pathway, product),
            )
        except:
            logger.debug("Error occured. Remove {} from database".format(product))
            mongo_client.remove(product)
            raise
        else:
            logger.debug("Product {} is ready".format(product))
            mongo_client.set_ready(product)

    @rpc.method
    def create_list_of_products(self):
        logger.debug("Creating products list")
        mongo_client.insert_product_list(predictor.universal_model.metabolites)


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect=os.environ['SERVER_PORT_5555_TCP'])


if __name__ == '__main__':
    predictor = get_predictor()
    mongo_client = MongoDB(os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
