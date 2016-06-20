import os
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING

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
        self.universal_models = self.mongo_client.lists.universal_model
        self.models = self.mongo_client.lists.model
        self.carbon_sources = self.mongo_client.lists.carbon_source
        self.products = self.mongo_client.lists.product

    @staticmethod
    def _insert_all(list, elements):
        for element in elements:
            list.update(
                {'_id': element.pop('id')},
                {'$set': element},
                upsert=True
            )

    def insert_product_list(self, products):
        self._insert_all(self.products, products)

    def insert_universal_models_list(self, universal_models):
        self._insert_all(self.universal_models, universal_models)

    def insert_models_list(self, models):
        self._insert_all(self.models, models)

    def insert_carbon_sources_list(self, carbon_sources):
        self._insert_all(self.carbon_sources, carbon_sources)

    def is_available(self, model_id, universal_model_id, carbon_source_id, product_id):
        return self.models.find_one(model_id) and \
               self.universal_models.find_one(universal_model_id) and \
               self.carbon_sources.find_one(carbon_source_id) and \
               self.products.find_one({"_id": product_id, 'universal_models': {'$in': [universal_model_id]}})


class PathwayCollection(MongoDB):
    """
    Pymongo methods wrapper for simpler calls to model specific databases, defined by model, universal model,
    carbon source and product
    """
    def __init__(self, model_id, universal_model_id, carbon_source_id, product_id):
        super(PathwayCollection, self).__init__()
        self.model_id = model_id
        self.universal_model_id = universal_model_id
        self.carbon_source_id = carbon_source_id
        self.product_id = product_id
        self.pathways = self.mongo_client.pathways.pathways
        self.key = {
            "model_id": self.model_id,
            "universal_model_id": self.universal_model_id,
            "carbon_source_id": self.carbon_source_id,
            "product_id": self.product_id
        }
        self.pathways.create_index({
            k: 1 for k, v in self.key.items()
        })

    def upsert(self):
        timestamp = datetime.now()
        self.pathways.update(
            self.key,
            {'$set': {
                "pathways": [],
                "ready": False,
                "created": timestamp,
                "updated": timestamp,
                "model_id": self.model_id,
                "universal_model_id": self.universal_model_id,
                "carbon_source_id": self.carbon_source_id,
                "product": self.product_id,
            }},
            upsert=True
        )

    def append_pathway(self, reactions_list, model, primary_nodes):
        self.pathways.update(
            self.key,
            {
                "$push": {
                    "pathways": {'reactions': reactions_list, 'model': model, 'primary_nodes': primary_nodes}
                },
                '$set': {
                    "updated": datetime.now()
                }
            }
        )

    def set_ready(self):
        self.pathways.update(
            self.key,
            {'$set': {
                "ready": True,
                "updated": datetime.now(),
            }}
        )

    def remove(self):
        self.pathways.remove(self.key)

    def find(self):
        return self.pathways.find_one(self.key)
