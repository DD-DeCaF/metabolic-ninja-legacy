import asyncio
import json
import time
from functools import partial

import requests
from aiozmq import rpc
from utils import logger

MAX_PREDICTIONS = 3

predictor = None


def predict_mock(product, max_predictions, callback):
    """Mock for Cameo predictor with callback function"""
    for step in range(10):
        callback("Pathway {}".format(step))
        time.sleep(1)
    return 'OK'


def push_progress(request_id, message):
    requests.post('http://server:8080/progress', data=json.dumps({
        "request_id": request_id,
        "message": message,
    }))


class WorkerHandler(rpc.AttrHandler):
    @rpc.method
    def predict_pathways(self, product: str, request_id: int) -> str:
        # result = pathways_to_html(predictor.run(product=product, max_predictions=MAX_PREDICTIONS))
        logger.debug("Request ID is {}".format(request_id))
        result = predict_mock(
            product=product,
            max_predictions=MAX_PREDICTIONS,
            callback=partial(push_progress, request_id),
        )
        return "Worker {}, product {}, pathways {}".format(request_id, product, result)


@asyncio.coroutine
def worker():
    yield from rpc.serve_rpc(WorkerHandler(), connect='tcp://server:5555')


if __name__ == '__main__':
    # predictor = get_predictor()  # get the model when the worker starts
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker())
    loop.run_forever()
