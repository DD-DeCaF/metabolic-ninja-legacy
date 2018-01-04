import logging

from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from . import settings


# Configure Raven to capture warning logs
raven_client = Client(settings.SENTRY_DSN)
handler = SentryHandler(raven_client)
handler.setLevel(logging.WARNING)
setup_logging(handler)
