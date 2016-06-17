from datetime import datetime
from pymongo import MongoClient

import logging
import os

logging.basicConfig()
logger = logging.getLogger('mongo_client')
logger.setLevel(logging.DEBUG)

MONGO_CRED = (os.environ['MONGO_PORT_27017_TCP_ADDR'], 27017)


class MongoDB(object):
    """
    Pymongo methods wrapper for simpler calls to common database "db"
    """

    def __init__(self):
        self.mongo_client = MongoClient(*MONGO_CRED)
        self.models = self.mongo_client.db.models
        self.products = self.mongo_client.db.products

    def insert_models_list(self, models_dataframe):
        for _, row in models_dataframe.iterrows():
            self.mongo_client.db.models.update(
                {'_id': row.bigg_id},
                {'$set': {
                    "name": row.organism
                }},
                upsert=True
            )

    def all_models(self):
        return self.mongo_client.db.models.find()

    def model_is_available(self, model_id):
        return self.models.find_one(model_id)

    def insert_product_list(self, metabolites):
        for metabolite in metabolites:
            self.products.update(
                {'_id': metabolite.name},
                {'$set': {
                    "name": metabolite.name
                }},
                upsert=True
            )

    def all_products(self):
        return self.products.find()

    def product_is_available(self, product):
        return self.products.find_one(product)


class ModelMongoDB(MongoDB):
    """
    Pymongo methods wrapper for simpler calls to model specific databases, defined by model ID
    """
    def __init__(self, model_id):
        super(ModelMongoDB, self).__init__()
        self.model_id = model_id
        self.pathways = self.mongo_client[self.model_id].pathways

    def upsert(self, product):
        timestamp = datetime.now()
        self.pathways.update(
            {'_id': product},
            {'$set': {
                "pathways": [],
                "ready": False,
                "created": timestamp,
                "updated": timestamp,
            }},
            upsert=True
        )

    def append_pathway(self, product, reactions_list, model, primary_nodes):
        self.pathways.update(
            {
                "_id": product
            },
            {
                "$push": {
                    "pathways": {'reactions': reactions_list, 'model': model, 'primary_nodes': primary_nodes}
                },
                '$set': {
                    "updated": datetime.now()
                }
            }
        )

    def set_ready(self, product):
        self.pathways.update(
            {'_id': product},
            {'$set': {
                "ready": True,
                "updated": datetime.now(),
            }}
        )

    def remove(self, product):
        self.pathways.remove({'_id': product})

    def find(self, product):
        return self.pathways.find_one(product)
