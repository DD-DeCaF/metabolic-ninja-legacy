import os
import re
import pickle
from cameo import load_model, models
from cameo.strain_design.pathway_prediction import PathwayPredictor
from cameo.util import Timer
import logging

logging.basicConfig()
logger = logging.getLogger('metabolic-ninja')
logger.setLevel(logging.DEBUG)


PICKLED_PREDICTOR_PATH = 'cache.pickle'


def pathway_to_list(pathway):
    return [reaction_to_dict(reaction) for reaction in pathway.reactions]


def reaction_to_dict(reaction):
    return dict(
        id=reaction.id,
        name=reaction.name,
        reaction_string=reaction.build_reaction_string(use_metabolite_names=True),
    )


def get_predictor():
    if os.path.exists(PICKLED_PREDICTOR_PATH):
        logger.debug('Cached model found.')
        with Timer('Loading pickled model'):
            return load_predictor()
    logger.debug('No model found. Loading model from scratch')
    with Timer('Building model from scratch'):
        predictor = generate_predictor()
    dump_predictor(predictor)
    logger.debug('Predictor is ready')
    return predictor


def load_predictor():
    with open(PICKLED_PREDICTOR_PATH, 'rb') as f:
        return pickle.load(f)


def generate_predictor():
    return PathwayPredictor(
        model=models.bigg.iMM904,
        universal_model=models.universal.metanetx_universal_model_bigg_rhea,
        compartment_regexp=re.compile(".*_c$")
    )


def dump_predictor(predictor):
    with open(PICKLED_PREDICTOR_PATH, 'wb') as f:
        pickle.dump(predictor, f)
