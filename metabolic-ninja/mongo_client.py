from datetime import datetime
from pymongo import MongoClient

import logging

logging.basicConfig()
logger = logging.getLogger('mongo_client')
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

    def append_pathway(self, product, reactions_list, model):
        self.ecoli_collection.update(
            {
                "_id": product
            },
            {
                "$push": {
                    "pathways": {'reactions': reactions_list, 'model': model}
                },
                '$set': {
                    "updated": datetime.now()
                }
            }
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

    def is_available(self, product):
        return self.product_collection.find_one(product)

    def find(self, product):
        return self.ecoli_collection.find_one(product)

    def all_products(self):
        return self.product_collection.find()
