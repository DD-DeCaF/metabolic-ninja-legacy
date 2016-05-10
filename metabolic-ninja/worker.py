import asyncio
import time
from functools import partial
from random import randint
from aiozmq import rpc
from utils import get_predictor, logger
from mongo_client import MongoDB

MAX_PREDICTIONS = 3


def predict_mock(product, max_predictions, callback):
    """Mock for Cameo predictor with callback function"""
    result = []
    for step in range(MAX_PREDICTIONS):
        pathway = "Pathway {}: ".format(step) + ", ".join("reaction {}".format(i) for i in range(randint(1, 5)))
        callback(pathway)
        result.append(pathway)
        time.sleep(1)
    return result


def append_pathway(product, pathway):
    logger.debug("writing to mongo: add pathway {}".format(pathway))
    mongo_client.append_pathway(product, pathway)
    logger.debug("written to mongo: pathway {}".format(pathway))


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, product: str):
        mongo_client.upsert(product)
        # get_predictor().run(
        #     product=product,
        #     max_predictions=MAX_PREDICTIONS,
        #     callback=partial(append_pathway, product),
        # )
        predict_mock(
            product=product,
            max_predictions=MAX_PREDICTIONS,
            callback=partial(append_pathway, product),
        )
        mongo_client.set_ready(product)


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect='tcp://server:5555')


if __name__ == '__main__':
    mongo_client = MongoDB()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
