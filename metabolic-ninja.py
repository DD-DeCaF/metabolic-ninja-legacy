import os
import re
import pickle
from cameo import load_model, models
from cameo.strain_design.pathway_prediction import PathwayPredictor
from cameo.util import Timer

import logging

logging.basicConfig()
logger = logging.getLogger('cameo')
logger.setLevel(logging.DEBUG)


def pathways_to_html(pathways):
    string = str()
    for i, pathway in enumerate(pathways):
        string += 'Pathway No. {}\n'.format(i + 1)
        for reaction in pathway.reactions:
            string += '{}, {}, {}\n'.format(reaction.id, reaction.name,
                                       reaction.build_reaction_string(use_metabolite_names=True))
    return string


if os.path.exists('cache.pickle'):
    logger.debug('Cached model found.')
    with open('cache.pickle', 'rb') as f:
        with Timer('Loading pickled model'):
            predictor = pickle.load(f)
            logger.debug('Cached model loaded')
else:
    logger.debug('No model found. Loading model from scratch')
    with Timer('Building model from scratch'):
        model = load_model('models/iMM904.json')
        universal_model = models.universal.metanetx_universal_model_bigg_rhea
        predictor = PathwayPredictor(model=model, universal_model=universal_model,
                                     compartment_regexp=re.compile(".*_c$"))
    with open('cache.pickle', 'wb') as f:
        pickle.dump(predictor, f)

# result = predictor.run(product='methanol', max_predictions=1)
# print(pathways_to_html(result))

# We need to import request to access the details of the POST request
# and render_template, to render our templates (form and response)
# we'll use url_for to get some URLs for the app on the templates
from flask import Flask, render_template, request, url_for

# Initialize the Flask application
app = Flask(__name__)


# Define a route for the default URL, which loads the form
@app.route('/')
def form():
    return render_template('form_submit.html')


# Define a route for the action of the form, for example '/hello/'
# We are also defining which type of requests this route is 
# accepting: POST requests in this case
@app.route('/hello/', methods=['POST'])
def hello():
    product = request.form['product']
    result = predictor.run(product=product, max_predictions=2)
    html_output = pathways_to_html(result)
    return render_template('form_action.html', product=html_output)


# Run the app :)
if __name__ == '__main__':
    logger.debug('Starting flask app.')
    app.run(
        debug=True,
        host="0.0.0.0",
        port=int("5000")
    )
