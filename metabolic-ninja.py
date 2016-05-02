import os
import re
import pickle
from cameo import models
from cameo.strain_design.pathway_prediction import PathwayPredictor

import logging
logging.basicConfig()
logger = logging.getLogger('cameo')
logger.setLevel(logging.DEBUG)

if os.path.exists('cache.pickle'):
    logger.debug('Cached model found.')
    with open('cache.pickle', 'rb') as f:
        predictor = pickle.load(f)
else:
    logger.debug('No model found. Loading model from scratch')
    model = models.bigg.iMM904
    predictor = PathwayPredictor(model=model, compartment_regexp=re.compile(".*_c$"))
    with open('cache.pickle', 'wb') as f:
        pickle.dump(predictor, f)

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
    result = predictor.run(product=product, max_predictions=1)
    html_output = result.data_frame.to_json()
    return render_template('form_action.html', product=html_output)


# Run the app :)
if __name__ == '__main__':
    app.run(
        debug=True,
        host="0.0.0.0",
        port=int("5000")
    )
    logger.debug('Flask app initialized.')
