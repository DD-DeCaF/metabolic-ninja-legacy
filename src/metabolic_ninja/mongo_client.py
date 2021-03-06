# Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING

from . import settings

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MONGO_CRED = (settings.MONGO_ADDR, settings.MONGO_PORT)


class MongoDB(object):
    """
    Pymongo methods wrapper for simpler calls to common database "db"
    """

    def __init__(self, mongo_client=None):
        self.mongo_client = mongo_client or MongoClient(*MONGO_CRED)
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
        return (
            self.universal_models.find_one(universal_model_id) and
            (model_id == universal_model_id or self.models.find_one(model_id)) and
            self.carbon_sources.find_one(carbon_source_id) and
            self.products.find_one({"_id": product_id, 'universal_models': {'$in': [universal_model_id]}})
        )


class PathwayCollection(MongoDB):
    """
    Pymongo methods wrapper for simpler calls to model specific databases, defined by model, universal model,
    carbon source and product
    """
    def __init__(self, key, **kwargs):
        super(PathwayCollection, self).__init__(**kwargs)
        self.key = key
        self.pathways = self.mongo_client.pathways.pathways
        for k, v in self.key.items():
            setattr(self, k, v)
        # self.pathways.create_index([(k, ASCENDING) for k in self.key])

    def upsert(self):
        timestamp = datetime.now()
        data = {
            "pathways": [],
            "ready": False,
            "created": timestamp,
            "updated": timestamp,
        }
        data.update(self.key)
        self.pathways.update(
            self.key,
            {'$set': data},
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
