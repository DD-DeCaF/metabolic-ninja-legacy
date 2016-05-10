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


IMM904_MODEL_PATH = 'models/iMM904.json'
PICKLED_PREDICTOR_PATH = 'cache.pickle'


def pathways_to_html(pathways):
    string = str()
    for i, pathway in enumerate(pathways):
        string += 'Pathway No. {}'.format(i + 1)
        for reaction in pathway.reactions:
            string += '{}, {}, {}'.format(reaction.id, reaction.name,
                                       reaction.build_reaction_string(use_metabolite_names=True))
    return string


def get_predictor():
    if os.path.exists(PICKLED_PREDICTOR_PATH):
        logger.debug('Cached model found.')
        with Timer('Loading pickled model'):
            return load_predictor()
    logger.debug('No model found. Loading model from scratch')
    with Timer('Building model from scratch'):
        predictor = generate_predictor()
    dump_predictor(predictor)
    return predictor


def load_predictor():
    with open(PICKLED_PREDICTOR_PATH, 'rb') as f:
        return pickle.load(f)


def generate_predictor():
    universal_model = models.universal.metanetx_universal_model_bigg_rhea
    return PathwayPredictor(
        model=load_model(IMM904_MODEL_PATH),
        universal_model=universal_model,
        compartment_regexp=re.compile(".*_c$")
    )


def dump_predictor(predictor):
    with open(PICKLED_PREDICTOR_PATH, 'wb') as f:
        pickle.dump(predictor, f)
