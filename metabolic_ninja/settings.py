import os

MONGO_ADDR = os.environ['MONGO_ADDR']
MONGO_PORT = int(os.environ['MONGO_PORT'])
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
