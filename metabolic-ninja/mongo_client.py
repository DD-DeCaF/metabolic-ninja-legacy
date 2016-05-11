import os
from pymongo import MongoClient

import logging

logging.basicConfig()
logger = logging.getLogger('mongo')
logger.setLevel(logging.DEBUG)


class MongoDB(object):
    def __init__(self):
        self.mongo_client = MongoClient(os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)
        self.collection = self.mongo_client.db.ecoli

    def upsert(self, product):
        self.collection.update(
            {'_id': product},
            {'$set': {
                "pathways": [],
                "ready": False
            }},
            upsert=True
        )

    def append_pathway(self, product, pathway):
        self.collection.update(
            {"_id": product},
            {"$push": {"pathways": pathway}}
        )

    def set_ready(self, product):
        self.collection.update(
            {'_id': product},
            {'$set': {
                "ready": True
            }}
        )

    def get(self, product):
        return self.collection.find_one({'_id': product})

    def exists(self, product):
        return self.collection.find({'_id': product}).count() > 0

    def is_ready(self, product):
        return self.get(product)["ready"]

    def remove(self, product):
        self.collection.remove({'_id': product})

