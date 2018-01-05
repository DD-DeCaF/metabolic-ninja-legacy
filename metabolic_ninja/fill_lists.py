import logging
from cameo import models
from metabolic_ninja.mongo_client import MongoDB
from collections import defaultdict


logging.basicConfig()
logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)


def create_list_of_models():
    logger.debug("Creating models list")
    MongoDB().insert_models_list(
        [{
             'id': row.bigg_id,
             'name': row.organism,
         } for index, row in models.index_models_bigg().iterrows()]
    )


def create_list_of_universal_models():
    logger.debug("Creating universal models list")
    MongoDB().insert_universal_models_list([{'id': key, 'name': key} for key in vars(models.universal).keys()])


def create_list_of_carbon_sources():
    logger.debug("Creating carbon sources list")
    carbon_sources = ['EX_glc_lp_e_rp_']
    MongoDB().insert_carbon_sources_list(
        [{
             'id': source,
             'name': source,
         } for source in carbon_sources]
    )


def create_list_of_products():
    logger.debug("Creating products list")
    all_products = defaultdict(lambda: [])
    logger.debug("all products")
    for universal_model in vars(models.universal).keys():
        logger.debug(universal_model)
        for product in getattr(models.universal, universal_model).metabolites:
            all_products[product.name].append(universal_model)
    MongoDB().insert_product_list(
        [{
             'id': k,
             'name': k,
             'universal_models': v
         } for k, v in all_products.items()]
    )


create_lists = [
    create_list_of_products,
    create_list_of_models,
    create_list_of_universal_models,
    create_list_of_carbon_sources
]
for f in create_lists:
    f()
