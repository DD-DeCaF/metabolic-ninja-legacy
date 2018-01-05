import os
import pickle
import logging
import time
from functools import lru_cache
from cameo import load_model, models
from cameo.strain_design.pathway_prediction import PathwayPredictor


logging.basicConfig()
logger = logging.getLogger('metabolic-ninja')
logger.setLevel(logging.DEBUG)


PICKLED_PREDICTOR_PATH = 'pickles/cache_{}_{}.pickle'


@lru_cache(2**6)
def get_predictor(model_id, universal_model_id):
    if os.path.exists(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id)):
        logger.debug('Cached model found.')
        return load_predictor(model_id, universal_model_id)
    logger.debug('No model found. Loading model from scratch')
    predictor = generate_predictor(model_id, universal_model_id)
    dump_predictor(predictor, model_id, universal_model_id)
    logger.debug('Predictor is ready')
    return predictor


def load_predictor(model_id, universal_model_id):
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'rb') as f:
        t = time.time()
        p = pickle.load(f)
        logger.info('Unpickled in {} sec'.format(time.time() - t))
        return p


def generate_predictor(model_id, universal_model_id):
    universal_model = getattr(models.universal, universal_model_id)
    model = getattr(models.bigg, model_id) if model_id != universal_model_id else universal_model
    pathway_predictor = PathwayPredictor(
        model=model,
        universal_model=universal_model,
    )
    pathway_predictor.model.solver.problem.parameters.tune_problem()
    return pathway_predictor


def dump_predictor(predictor, model_id, universal_model_id):
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'wb') as f:
        pickle.dump(predictor, f)


MODELS_IDS = ['iJO1366', 'iMM904']
UNIVERSAL_MODELS_IDS = [
    'metanetx_universal_model_rhea',
    'metanetx_universal_model_bigg',
    'metanetx_universal_model_bigg_rhea',
    'metanetx_universal_model_bigg_rhea_kegg',
    'metanetx_universal_model_bigg_rhea_kegg_brenda'
]


if __name__ == '__main__':
    for m in MODELS_IDS:
        for u in UNIVERSAL_MODELS_IDS:
            dump_predictor(get_predictor(m, u), m, u)
