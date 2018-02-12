"""
Celery configuration module.

See `the celery docs
<http://docs.celeryproject.org/en/latest/userguide/configuration.html>`_.
"""

import os

REDIS_ENDPOINT = os.environ.get('REDIS_ENDPOINT')
broker_url = "redis://%s/0" % REDIS_ENDPOINT
result_backend = "redis://%s/0" % REDIS_ENDPOINT
broker_transport_options = {
    'region': os.environ.get('AWS_REGION', 'us-east-1'),
    'queue_name_prefix': 'accounts-',
}
worker_prefetch_multiplier = 1
task_acks_late = True
