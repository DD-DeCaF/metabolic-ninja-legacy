from datetime import datetime
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
        self.ecoli_collection = self.mongo_client.db.ecoli
        self.product_collection = self.mongo_client.db.product

    def upsert(self, product):
        timestamp = datetime.now()
        self.ecoli_collection.update(
            {'_id': product},
            {'$set': {
                "pathways": [],
                "ready": False,
                "created": timestamp,
                "updated": timestamp,
            }},
            upsert=True
        )

    def append_pathway(self, product, pathway):
        self.ecoli_collection.update(
            {"_id": product},
            {"$push": {"pathways": pathway}, '$set': {"updated": datetime.now()}}
        )

    def set_ready(self, product):
        self.ecoli_collection.update(
            {'_id': product},
            {'$set': {
                "ready": True,
                "updated": datetime.now(),
            }}
        )

    def remove(self, product):
        self.ecoli_collection.remove({'_id': product})

    def insert_product_list(self, metabolites):
        for metabolite in metabolites:
            self.product_collection.update(
                {'_id': metabolite.name},
                {'$set': {
                    "name": metabolite.name
                }},
                upsert=True
            )
