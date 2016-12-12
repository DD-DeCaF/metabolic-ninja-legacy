import os
import re
import pickle
import logging
import json
from functools import lru_cache
from copy import deepcopy
import cobra
from cameo import load_model, models
from cameo.strain_design.pathway_prediction import PathwayPredictor
from cameo.util import Timer


logging.basicConfig()
logger = logging.getLogger('metabolic-ninja')
logger.setLevel(logging.DEBUG)


PICKLED_PREDICTOR_PATH = 'cache_{}_{}.pickle'


def pathway_to_model(pathway):
    model = cobra.Model('test')
    model.add_reactions(deepcopy(list(pathway.reactions)))
    return json.loads(cobra.io.to_json(model))


def pathway_to_list(pathway):
    return [reaction_to_dict(reaction) for reaction in pathway.reactions]


def reaction_to_dict(reaction):
    return dict(
        id=reaction.id,
        name=reaction.name,
        reaction_string=reaction.build_reaction_string(use_metabolite_names=True),
    )


def metabolite_to_dict(metabolite):
    return dict(
        id=metabolite.nice_id,
        name=metabolite.name,
        formula=metabolite.formula,
    )


@lru_cache(2**5)
def get_predictor(model_id, universal_model_id):
    if os.path.exists(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id)):
        logger.debug('Cached model found.')
        with Timer('Loading pickled model'):
            return load_predictor(model_id, universal_model_id)
    logger.debug('No model found. Loading model from scratch')
    with Timer('Building model from scratch'):
        predictor = generate_predictor(model_id, universal_model_id)
    dump_predictor(predictor, model_id, universal_model_id)
    logger.debug('Predictor is ready')
    return predictor


def load_predictor(model_id, universal_model_id):
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'rb') as f:
        return pickle.load(f)


def generate_predictor(model_id, universal_model_id):
    universal_model = getattr(models.universal, universal_model_id)
    model = getattr(models.bigg, model_id) if model_id != universal_model_id else universal_model
    pathway_predictor = PathwayPredictor(
        model=model,
        universal_model=universal_model,
        compartment_regexp=re.compile(".*_c$")
    )
    pathway_predictor.model.solver.problem.parameters.tune_problem()
    return pathway_predictor


def dump_predictor(predictor, model_id, universal_model_id):
    with open(PICKLED_PREDICTOR_PATH.format(model_id, universal_model_id), 'wb') as f:
        pickle.dump(predictor, f)
