import os
from pymongo import MongoClient

import logging

logging.basicConfig()
logger = logging.getLogger('mongo')
logger.setLevel(logging.DEBUG)


class MongoDB(object):
    """
    Pymongo methods wrapper for simpler calls
    """
    def __init__(self, *args, **kwargs):
        self.mongo_client = MongoClient(*args, **kwargs)
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

    def remove(self, product):
        self.collection.remove({'_id': product})

