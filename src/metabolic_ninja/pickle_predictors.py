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
import pickle
import logging
import time
from functools import lru_cache
from cameo import load_model, models
from cameo.strain_design.pathway_prediction import PathwayPredictor


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


PICKLED_PREDICTOR_PATH = 'pickles/cache_{}_{}.pickle'


@lru_cache(2**6)
def get_predictor(model_id, universal_model_id):
    if os.path.exists(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id)):
        logger.debug("{}/{}: cached model found, loading from disk".format(model_id, universal_model_id))
        predictor = load_predictor(model_id, universal_model_id)
    else:
        logger.debug("{}/{}: no cached model found; generating and dumping".format(model_id, universal_model_id))
        predictor = generate_predictor(model_id, universal_model_id)
        dump_predictor(predictor, model_id, universal_model_id)
    logger.debug("{}/{}: predictor is ready")
    return predictor


def load_predictor(model_id, universal_model_id):
    t = time.time()
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'rb') as f:
        p = pickle.load(f)
    logger.debug("{}/{}: unpickled in {:.2f}s".format(model_id, universal_model_id, time.time() - t))
    return p


def generate_predictor(model_id, universal_model_id):
    t = time.time()
    universal_model = getattr(models.universal, universal_model_id)
    model = getattr(models.bigg, model_id) if model_id != universal_model_id else universal_model
    pathway_predictor = PathwayPredictor(
        model=model,
        universal_model=universal_model,
    )
    pathway_predictor.model.solver.problem.parameters.tune_problem()
    logger.debug("{}/{}: generated predictor in {:.2f}s".format(model_id, universal_model_id, time.time() - t))
    return pathway_predictor


def dump_predictor(predictor, model_id, universal_model_id):
    t = time.time()
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'wb') as f:
        logger.debug("{}/{}: dumping pickle".format(model_id, universal_model_id))
        pickle.dump(predictor, f)
    logger.debug("{}/{}: dumped predictor in {:.2f}s".format(model_id, universal_model_id, time.time() - t))


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
